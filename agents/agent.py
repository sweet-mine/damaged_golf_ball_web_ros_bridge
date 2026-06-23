import os
import subprocess
import re
from typing import Dict, Any, List
import dotenv
from langchain_openai import ChatOpenAI
from langchain_classic.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.tools import tool

# Load environment variables
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
dotenv.load_dotenv(os.path.join(base_dir, ".env"))

# -------------------------------------------------------------------------
# 원칙 1: 모든 함수는 try-except로 감싸여 Exception 대신 dict를 반환합니다.
# 원칙 2: 모든 파라미터에는 기본값(default value)이 부여되어 있습니다.
# 원칙 3: raw_output뿐만 아니라, LLM이 이해하기 쉽도록 핵심 필드를 파싱하여 제공합니다.
# -------------------------------------------------------------------------

import json

def _parse_arg(val: Any) -> str:
    """ReAct 에이전트의 다양한 파싱 결과(JSON, 따옴표 등)를 안전하게 문자열로 변환합니다."""
    if val is None:
        return ""
    val_str = str(val).strip()
    if val_str.startswith("{") and val_str.endswith("}"):
        try:
            data = json.loads(val_str)
            if data:
                # 첫 번째 키의 값을 취하거나 적절한 값을 추출
                first_val = next(iter(data.values()))
                return str(first_val).strip()
            return ""
        except:
            pass
    # 따옴표 제거
    if (val_str.startswith("'") and val_str.endswith("'")) or (val_str.startswith('"') and val_str.endswith('"')):
        val_str = val_str[1:-1]
    return val_str.strip()

@tool
def get_node_list(namespace: str = "") -> Dict[str, Any]:
    """현재 시스템에 실행 중인 ROS2 노드 목록을 반환합니다."""
    ns = _parse_arg(namespace)
    try:
        result = subprocess.run(["ros2", "node", "list"], capture_output=True, text=True, check=True)
        nodes = [line.strip() for line in result.stdout.split('\n') if line.strip()]
        return {
            "success": True,
            "node_count": len(nodes),
            "nodes": nodes,
            "raw_output": result.stdout
        }
    except Exception as e:
        return {"success": False, "nodes": [], "error_message": str(e), "suggestion": "환경변수가 설정되어 있는지 확인하세요."}

@tool
def get_topic_list(include_hidden: str = "False") -> Dict[str, Any]:
    """현재 활성화된 ROS2 토픽 목록을 반환합니다."""
    hidden_bool = _parse_arg(include_hidden).lower() in ["true", "1", "yes"]
    try:
        cmd = ["ros2", "topic", "list"]
        if hidden_bool:
            cmd.append("-a")
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        topics = [line.strip() for line in result.stdout.split('\n') if line.strip()]
        return {
            "success": True,
            "topic_count": len(topics),
            "topics": topics,
            "raw_output": result.stdout
        }
    except Exception as e:
        return {"success": False, "topics": [], "error_message": str(e)}

@tool
def get_topic_info(topic_name: str = "/rosout") -> Dict[str, Any]:
    """특정 ROS2 토픽의 타입, 퍼블리셔 및 서브스크라이버 개수 정보를 반환합니다."""
    topic = _parse_arg(topic_name)
    if not topic:
        topic = "/rosout"
    try:
        result = subprocess.run(["ros2", "topic", "info", topic], capture_output=True, text=True, check=True)
        lines = result.stdout.split('\n')
        
        # 핵심 필드 추출 로직
        msg_type = lines[0].split(': ')[1] if len(lines) > 0 and 'Type:' in lines[0] else "Unknown"
        pub_count = int(lines[1].split(': ')[1]) if len(lines) > 1 and 'Publisher count:' in lines[1] else 0
        sub_count = int(lines[2].split(': ')[1]) if len(lines) > 2 and 'Subscription count:' in lines[2] else 0
        
        return {
            "success": True,
            "topic_name": topic,
            "message_type": msg_type,
            "publisher_count": pub_count,
            "subscriber_count": sub_count,
            "raw_output": result.stdout
        }
    except Exception as e:
        return {"success": False, "topic_name": topic, "error_message": str(e)}

@tool
def get_topic_hz(topic_name: str = "/rosout", timeout_sec: str = "2") -> Dict[str, Any]:
    """특정 토픽의 발행 주기(주파수, Hz)를 측정합니다. 무한 대기를 방지하기 위해 timeout이 적용됩니다."""
    topic = _parse_arg(topic_name)
    if not topic:
        topic = "/rosout"
    
    try:
        timeout_val = int(_parse_arg(timeout_sec))
    except:
        timeout_val = 2
        
    try:
        # hz 명령어는 지속 실행되므로 timeout을 걸어 샘플링 후 종료합니다.
        result = subprocess.run(
            ["ros2", "topic", "hz", topic], 
            capture_output=True, text=True, timeout=timeout_val
        )
        output = result.stdout
    except subprocess.TimeoutExpired as e:
        output = e.stdout.decode('utf-8') if e.stdout else ""
    except Exception as e:
        return {"success": False, "error_message": str(e)}

    # 간단한 파싱 (출력 결과에서 average rate 추출)
    avg_rate = "Unknown"
    for line in output.split('\n'):
        if "average rate:" in line:
            avg_rate = line.split(':')[1].strip()
            break
            
    return {
        "success": True,
        "topic_name": topic,
        "average_hz": avg_rate,
        "raw_output": output
    }

@tool
def get_node_info(node_name: str = "") -> Dict[str, Any]:
    """특정 ROS2 노드의 상세 정보(Publishers, Subscribers, Services 등)를 반환합니다."""
    node = _parse_arg(node_name)
    if not node:
        return {"success": False, "error_message": "노드 이름이 제공되지 않았습니다. get_node_list를 먼저 실행하세요."}
        
    try:
        result = subprocess.run(["ros2", "node", "info", node], capture_output=True, text=True, check=True)
        return {
            "success": True,
            "node_name": node,
            "info_length": len(result.stdout),
            "raw_output": result.stdout
        }
    except Exception as e:
        return {"success": False, "error_message": str(e)}

@tool
def get_system_diagnosis(include_network: str = "False") -> Dict[str, Any]:
    """현재 ROS 시스템 정보를 파악하고 진단합니다. 리포트를 제공합니다."""
    net_bool = _parse_arg(include_network).lower() in ["true", "1", "yes"]
    try:
        cmd = ["ros2", "doctor", "--report"]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        warning_count = result.stdout.lower().count("warning")
        error_count = result.stdout.lower().count("error")
        
        # ROS2 배포판 이름 추출
        distro = "Unknown"
        for line in result.stdout.split('\n'):
            if "distribution name" in line:
                distro = line.split(':')[-1].strip()
                break
                
        # 불필요하게 긴 네트워크 정보 필터링
        report = result.stdout
        if not net_bool and "PLATFORM INFORMATION" in report:
            report = report[report.index("PLATFORM INFORMATION"):]
            
        return {
            "success": True,
            "warning_count": warning_count,
            "error_count": error_count,
            "is_healthy": warning_count == 0 and error_count == 0,
            "ros_version": f"ROS 2 {distro}",
            "diagnostic_report": report.strip()
        }
    except Exception as e:
        return {"success": False, "error_message": str(e)}

@tool
def navigate_to_room(room_number: str) -> Dict[str, Any]:
    """로봇을 지정된 방(1, 2, 3, 4)으로 이동시킵니다. 입력은 반드시 '1', '2', '3', '4' 중 하나여야 합니다."""
    room_map = {
        "1": {"x": 1.83, "y": 1.45},
        "2": {"x": 1.83, "y": -1.61},
        "3": {"x": -0.40, "y": 1.45},
        "4": {"x": -0.40, "y": -1.61},
    }
    
    room_id = str(room_number).strip()
    if room_id not in room_map:
        return {"success": False, "error_message": f"잘못된 방 번호입니다. '1', '2', '3', '4' 중에서 선택하세요. 입력값: {room_id}"}
        
    target = room_map[room_id]
    
    try:
        import requests
        from requests.exceptions import Timeout
        try:
            response = requests.post("http://127.0.0.1:8000/nav", json=target, timeout=2)
            if response.status_code == 200:
                return {"success": True, "message": f"{room_id}번 방으로 이동 명령을 전달했습니다.", "target": target}
            else:
                return {"success": False, "error_message": f"이동 명령 전송 실패: {response.text}"}
        except Timeout:
            # Nav2 action server 승인 지연으로 인한 타임아웃 발생 시, 정상 비동기 전송으로 간주
            return {"success": True, "message": f"{room_id}번 방으로 이동 명령을 성공적으로 전달했습니다. (로봇이 백그라운드에서 주행을 시작합니다.)", "target": target}
    except Exception as e:
        return {"success": False, "error_message": f"API 호출 중 오류 발생: {str(e)}"}

@tool
def get_broken_ball_history() -> Dict[str, Any]:
    """현재 데이터베이스에 기록된 모든 파손 공(파손 이력) 감지 정보를 조회하여 반환합니다."""
    try:
        from database import SessionLocal, BrokenBall
        import json
        db = SessionLocal()
        try:
            items = db.query(BrokenBall).order_by(BrokenBall.id.desc()).all()
            results = []
            for item in items:
                try:
                    loc = json.loads(item.location)
                except:
                    loc = item.location
                results.append({
                    "id": item.id,
                    "timestamp": item.timestamp,
                    "location": loc
                })
            return {
                "success": True,
                "count": len(results),
                "history": results
            }
        finally:
            db.close()
    except Exception as e:
        return {"success": False, "error_message": str(e)}

@tool
def get_current_time() -> Dict[str, str]:
    """현재 시스템의 정확한 날짜와 시간을 조회하여 반환합니다. 오늘 날짜나 현재 시각에 대한 질문이 들어왔을 때만 호출해야 합니다."""
    from datetime import datetime
    return {"current_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

# 도구 리스트 묶기
diagnostic_tools = [
    get_node_list, 
    get_topic_list, 
    get_topic_info, 
    get_topic_hz, 
    get_node_info, 
    get_system_diagnosis,
    navigate_to_room,
    get_broken_ball_history,
    get_current_time
]

class GolfbotAgent:
    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        # 1. 모델 인스턴스 생성 (GPT-4o-Mini + GMS 프록시 엔드포인트 연동)
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0,
            api_key=os.getenv("GMS_API_KEY"),
            base_url="https://gms.ssafy.io/gmsapi/api.openai.com/v1"
        )
        self.tools = diagnostic_tools

        # 2. 통합 시스템 프롬프트 설정 (일상 대화 및 도구 제어 유도)
        system_prompt = (
            "당신은 ROS2 로봇 시스템(Golfbot)을 제어하고 진단하는 전문 AI 어시스턴트입니다.\n"
            "사용자의 질문에 친절하고 상세한 한국어로 답변하세요.\n"
            "시스템 노드, 토픽 정보, 주파수 측정, 파손 공 감지 이력(파손 이력) 등이 필요하거나 로봇 이동 명령을 내릴 때는 제공된 도구를 활용하여 확인한 뒤 답해야 합니다.\n"
            "도구 실행 결과에 긴 텍스트나 상세 리포트가 있으면 핵심 정보 위주로 가독성 좋게 정리하여 답변하세요.\n"
            "도구를 쓸 필요가 없는 일상 대화나 이전 질문에 대한 설명 등은 도구를 쓰지 말고 자연스러운 한국어로 대화해 주세요."
        )

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])

        # 3. OpenAI Tools 에이전트 및 실행기 생성
        self.agent = create_openai_tools_agent(self.llm, self.tools, prompt)
        self.agent_executor = AgentExecutor(
            agent=self.agent,
            tools=self.tools,
            verbose=self.verbose
        )

    def chat(self, user_input: str, history: List[Dict[str, Any]] = None) -> str:
        # Convert list of history dicts to LangChain Message objects
        chat_history = []
        if history:
            for m in history:
                role = m.get("role")
                content = m.get("content", "")
                if not content:
                    continue
                # Remove mic prefix to avoid polluting chat history with mic emojis
                if content.startswith("🎙️ "):
                    content = content[3:]
                
                if role == "user":
                    chat_history.append(HumanMessage(content=content))
                elif role == "assistant":
                    chat_history.append(AIMessage(content=content))

        # Execute
        try:
            res = self.agent_executor.invoke({
                "input": user_input,
                "chat_history": chat_history
            })
            return res.get("output", "").strip()
        except Exception as e:
            if self.verbose:
                import traceback
                traceback.print_exc()
            return f"에러가 발생했습니다: {str(e)}"

# 5. 실행 테스트 및 CLI 루프
if __name__ == "__main__":
    agent = GolfbotAgent(verbose=True)
    print("====================================================")
    print(" Golfbot Conversational Agent (Native Function Calling) ")
    print("====================================================")
    print("종료하려면 'exit' 또는 'quit'을 입력하세요.\n")
    
    while True:
        try:
            user_input = input("User: ")
            if user_input.strip().lower() in ["exit", "quit"]:
                print("대화를 종료합니다.")
                break
            if not user_input.strip():
                continue
                
            response = agent.chat(user_input)
            print(f"Agent: {response}\n")
        except KeyboardInterrupt:
            print("\n대화를 종료합니다.")
            break
        except Exception as e:
            print(f"오류가 발생했습니다: {e}\n")