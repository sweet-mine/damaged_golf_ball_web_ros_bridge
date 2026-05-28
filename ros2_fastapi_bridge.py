import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from sensor_msgs.msg import BatteryState
from sensor_msgs.msg import CompressedImage # 추가: Image 메시지 타입
from sensor_msgs.msg import Image
from cv_bridge import CvBridge # 추가: ROS Image -> OpenCV 변환
import cv2
import time

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse # 추가: HTTP 비디오 스트림용
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from pydantic import BaseModel
import uvicorn
import threading
import asyncio
import json
from database import init_db
from ws_manager import manager, app_state
from routers import broken_ball

try:
    from nav2_simple_commander.robot_navigator import BasicNavigator
    from geometry_msgs.msg import PoseStamped
except ImportError:
    BasicNavigator = None
    PoseStamped = None

# --- 웹소켓 매니저 (ws_manager.py로 분리됨) ---
loop = None
ros_node = None
navigator = None

# --- 비디오 스트리밍용 전역 변수 ---
bridge = CvBridge()
latest_jpeg = None
new_frame_event = None # 비동기 이벤트 객체

# --- ROS 2 노드 ---
class WebBridgeNode(Node):
    def __init__(self, context=None):
        super().__init__('web_bridge_node', context=context)
        self.cmd_vel_sub = self.create_subscription(Twist, '/cmd_vel', self.cmd_vel_callback, 10)
        self.metrics_sub = self.create_subscription(BatteryState, '/battery_state', self.battery_callback, 10)
        
        # 카메라 토픽 구독 추가
        self.camera_sub = self.create_subscription(Image, 'camera/image_raw', self.camera_callback, 10)
        
        # 로봇 통신 모니터링 변수 및 타이머 등록
        self.last_msg_time = 0.0
        self.is_connected = False
        self.conn_timer = self.create_timer(1.0, self.conn_timer_callback)
        
        self.get_logger().info("FastAPI Web Bridge Node Started (with Camera).")

    def conn_timer_callback(self):
        current_time = time.time()
        connected = (current_time - self.last_msg_time) < 3.0
        if connected != self.is_connected:
            self.is_connected = connected
            data = {'type': 'robot_connection', 'data': {'connected': self.is_connected}}
            if loop:
                asyncio.run_coroutine_threadsafe(manager.broadcast(data), loop)

    def cmd_vel_callback(self, msg):
        self.last_msg_time = time.time()
        data = {'type': 'cmd_vel_data', 'data': {'linear_x': round(msg.linear.x, 3), 'angular_z': round(msg.angular.z, 3)}}
        if loop: asyncio.run_coroutine_threadsafe(manager.broadcast(data), loop)

    def battery_callback(self, msg):
        self.last_msg_time = time.time()
        data = {'type': 'battery_data', 'data': {'voltage': round(msg.voltage, 3), 'percentage': round(msg.percentage, 3)}}
        if loop: asyncio.run_coroutine_threadsafe(manager.broadcast(data), loop)

    # def camera_callback(self, msg):
    #     global latest_jpeg, new_frame_event
    #     try:
    #         latest_jpeg = bytes(msg.data)
            
    #         # 새 프레임이 도착했음을 알림
    #         if loop and new_frame_event:
    #             loop.call_soon_threadsafe(new_frame_event.set)
                
    #     except Exception as e:
    #         self.get_logger().error(f"Camera Callback Error: {e}")

    def camera_callback(self, msg):
        global latest_jpeg, new_frame_event
        self.last_msg_time = time.time()
        try:
            # 1. ROS Image 메시지를 OpenCV 이미지(BGR8)로 변환
            cv_image = bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
            
            # 2. 이미지를 JPEG로 압축 (품질 조절 가능)
            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 80]
            ret, buffer = cv2.imencode('.jpg', cv_image, encode_param)
            
            if ret:
                latest_jpeg = buffer.tobytes()
                # 3. 새 프레임이 도착했음을 FastAPI 비동기 루프에 알림
                if loop and new_frame_event:
                    loop.call_soon_threadsafe(new_frame_event.set)
        except Exception as e:
            self.get_logger().error(f"Camera Callback Error: {e}")

# --- 데이터베이스 설정 (database.py로 분리됨) ---

# --- FastAPI 설정 ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    global loop, ros_node, new_frame_event, navigator
    loop = asyncio.get_running_loop()
    app_state["loop"] = loop
    new_frame_event = asyncio.Event() # 이벤트 객체 초기화
    
    rclpy.init() # 네비게이터용 기본 전역 Context 초기화
    
    # 웹 브릿지 노드 전용 Context 및 싱글스레드 Executor 생성 (Thread-safe 분리)
    ros_context = rclpy.Context()
    ros_context.init()
    
    ros_node = WebBridgeNode(context=ros_context)
    executor = rclpy.executors.SingleThreadedExecutor(context=ros_context)
    executor.add_node(ros_node)
    
    spin_thread = threading.Thread(target=executor.spin, daemon=True)
    spin_thread.start()
    
    if BasicNavigator is not None:
        navigator = BasicNavigator()
    else:
        navigator = None
        ros_node.get_logger().warn("BasicNavigator could not be imported.")
    
    yield
    
    ros_node.destroy_node()
    executor.shutdown()
    ros_context.shutdown()
    rclpy.shutdown()

app = FastAPI(lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(broken_ball.router)

# --- 데이터용 WebSocket 엔드포인트 ---
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    # 신규 연결 시 로봇 통신 현재 상태 전송
    if ros_node:
        initial_status = {
            'type': 'robot_connection',
            'data': {
                'connected': getattr(ros_node, 'is_connected', False)
            }
        }
        await websocket.send_json(initial_status)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# --- 비디오 스트리밍 제너레이터 함수 ---
async def generate_frames():
    global latest_jpeg, new_frame_event
    while True:
        # ROS에서 새 프레임(jpeg)을 만들 때까지 대기 (CPU 낭비 방지)
        await new_frame_event.wait()
        new_frame_event.clear()
        
        if latest_jpeg is not None:
            # MJPEG 포맷으로 데이터 산출(yield)
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + latest_jpeg + b'\r\n')

# --- 비디오 HTTP 스트리밍 엔드포인트 ---
@app.get("/video_feed")
async def video_feed():
    # multipart/x-mixed-replace를 통해 브라우저가 이미지를 지속적으로 덮어쓰도록 함
    return StreamingResponse(generate_frames(), media_type="multipart/x-mixed-replace; boundary=frame")

# --- 네비게이션 제어 엔드포인트 ---
class NavCommand(BaseModel):
    x: float
    y: float

@app.post("/nav")
async def nav_endpoint(cmd: NavCommand):
    global navigator, loop
    if not navigator:
        return {"status": "error", "message": "Navigator not initialized or not available"}
    
    goal_pose = PoseStamped()
    goal_pose.header.frame_id = 'map'
    goal_pose.header.stamp = navigator.get_clock().now().to_msg()
    goal_pose.pose.position.x = cmd.x
    goal_pose.pose.position.y = cmd.y
    goal_pose.pose.orientation.w = 1.0 # default facing forward
    
    # goToPose sends the goal and waits for acceptance. Running in an executor to avoid blocking the event loop.
    await loop.run_in_executor(None, navigator.goToPose, goal_pose)
    
    return {"status": "success", "message": f"Navigating to ({cmd.x}, {cmd.y})"}

# --- 파손 골프공 검출 엔드포인트 (routers/broken_ball.py로 분리됨) ---

if __name__ == '__main__':
    uvicorn.run("ros2_fastapi_bridge:app", host="0.0.0.0", port=8000, reload=False)