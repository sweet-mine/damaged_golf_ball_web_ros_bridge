import subprocess
import re
from typing import Dict, Any
from langchain_ollama import ChatOllama
from langchain_classic.agents import AgentExecutor, create_react_agent, AgentOutputParser
from langchain_core.prompts import PromptTemplate, ChatPromptTemplate
from langchain_core.tools import tool
from langchain_core.agents import AgentAction, AgentFinish
from langchain_core.exceptions import OutputParserException

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

# 도구 리스트 묶기
diagnostic_tools = [
    get_node_list, 
    get_topic_list, 
    get_topic_info, 
    get_topic_hz, 
    get_node_info, 
    get_system_diagnosis,
    navigate_to_room
]

class GolfbotAgent:
    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        # 1. 모델 인스턴스 생성
        self.llm = ChatOllama(
            model="gemma4:e2b", 
            temperature=0, 
        )
        self.tools = diagnostic_tools

        # 2. 의도 분류기 (Intent Gate) 설정
        intent_template = (
            "You are an intent classifier for a ROS2 robot assistant.\n"
            "Analyze the user message and classify it into one of the following categories:\n"
            "- CHAT: General greetings, small talk, casual conversations, OR questions referencing previous outputs/dialogue history that do NOT require executing new ROS tools.\n"
            "- DIAGNOSTIC: Direct queries requesting NEW information about the ROS2 system, nodes, topics, system diagnostics, OR commanding the robot to navigate to a specific room.\n\n"
            "Respond with ONLY the category name: 'CHAT' or 'DIAGNOSTIC' without any other text.\n\n"
            "User Message: {input}\n"
            "Category:"
        )
        self.intent_prompt = PromptTemplate.from_template(intent_template)
        self.intent_chain = self.intent_prompt | self.llm

        # 3. 일반 대화용 (CHAT) 프롬프트 설정
        chat_template = [
            ("system", "당신은 ROS2 로봇 시스템을 지원하는 친절하고 전문적인 AI 어시스턴트입니다. 사용자와 일상적인 대화(안부 인사 등)를 나누거나, 일반적인 질문에 성실하게 답변하세요. 대화 기록을 참고하여 자연스럽게 답하세요."),
            ("human", "이전 대화 기록:\n{chat_history}\n\n현재 사용자 질문: {input}")
        ]
        self.chat_prompt = ChatPromptTemplate.from_messages(chat_template)
        self.chat_chain = self.chat_prompt | self.llm

    def _get_history_str(self, history: list = None) -> str:
        if not history:
            return "이전 대화가 없습니다."
        return "\n".join([f"- 사용자: {m.get('content', '')}" if m.get('role') == 'user' else f"- AI 답변: {m.get('content', '')}" for m in history])

    def _execute_react(self, user_input: str) -> str:
        """이전 대화 기록 및 불필요한 레이어로 인한 오작동/반복 문제를 완벽히 우회하는 고성능 커스텀 ReAct 실행 루프"""
        tools_str = ""
        for t in self.tools:
            tools_str += f"- {t.name}: {t.description}\n"
            
        system_prompt = (
            "당신은 ROS2 시스템 진단 AI입니다.\n"
            "사용자 질문을 분석하여 어떤 도구를 호출해야 하는지 판단하세요.\n\n"
            "도구 목록:\n"
            f"{tools_str}\n"
            "도구가 필요하다면 반드시 아래 형식으로 작성하세요:\n"
            "Action: 도구이름 (반드시 위 도구 목록 중 하나)\n"
            "Action Input: 매개변수\n\n"
            "도구가 필요없다면 곧바로 최종 답변을 작성하세요:\n"
            "Final Answer: 최종 답변\n\n"
            "시작!\n\n"
            f"Question: {user_input}"
        )
        
        if self.verbose:
            print("\n[에이전트] 도구 호출 필요성 판단 (Step 1)...")
            
        resp = self.llm.invoke(system_prompt)
        generation = resp.content.strip()
        
        if self.verbose:
            print(f"[LLM 판단 결과]:\n{generation}")
            
        # 바로 최종 답변을 낸 경우 조기 종료
        if "Final Answer:" in generation:
            return generation.split("Final Answer:")[-1].strip()
        if "최종 답변:" in generation:
            return generation.split("최종 답변:")[-1].strip()
            
        # 수동 Action 파싱
        action = None
        action_input = ""
        
        if "Action:" in generation:
            action_part = generation.split("Action:")[-1].strip()
            if "Action Input:" in action_part:
                parts = action_part.split("Action Input:")
                action = parts[0].strip()
                action_input = parts[1].strip()
            else:
                action = action_part.strip()
                
            if "\n" in action:
                action = action.split("\n")[0].strip()
            if "\n" in action_input:
                action_input = action_input.split("\n")[0].strip()
                
            action = action.strip('"').strip("'").strip()
            action_input = action_input.strip('"').strip("'").strip()
            
        if not action:
            # Action 형식을 못 맞췄지만 텍스트가 있으면 그대로 반환
            return generation
            
        if self.verbose:
            print(f"[도구 실행] 실행 도구: {action}, 매개변수: {action_input}")
            
        # 도구 검색 및 수행
        tool_found = None
        for t in self.tools:
            if t.name == action:
                tool_found = t
                break
                
        if tool_found:
            try:
                if not action_input or action_input.lower() in ["none", "null", "empty"]:
                    obs = tool_found.invoke({})
                else:
                    obs = tool_found.invoke(action_input)
            except Exception as e:
                obs = {"success": False, "error": str(e)}
        else:
            obs = {"success": False, "error": f"Tool '{action}' not found."}
            
        if self.verbose:
            print(f"[도구 실행 결과]: {obs}")
            
        # 2단계: 도구 실행 결과를 바탕으로 최종 답변 생성
        obs_str = str(obs)
        if len(obs_str) > 2000:
            obs_str = obs_str[:2000] + "\n... [결과가 너무 길어 생략됨]"
            
        step2_prompt = (
            "당신은 ROS2 시스템 진단 AI입니다.\n"
            f"사용자 질문: {user_input}\n\n"
            f"도구 실행 결과:\n{obs_str}\n\n"
            "---\n"
            "위 도구 실행 결과를 바탕으로, 사용자 질문에 대한 최종적이고 상세한 한국어 답변을 작성하세요.\n"
            "결과에서 정확한 정보를 찾을 수 없더라도 절대 코드를 짜거나 JSON 포맷으로 대답하지 마세요.\n"
            "자연스러운 한국어 문장으로 답변해야 합니다.\n"
            "반드시 아래 형식으로만 작성하세요:\n"
            "Final Answer: [여기에 최종 한국어 답변 작성]"
        )
        
        if self.verbose:
            print("\n[에이전트] 최종 답변 생성 (Step 2)...")
            
        resp2 = self.llm.invoke(step2_prompt)
        generation2 = resp2.content.strip()
        
        if self.verbose:
            print(f"[LLM 최종 답변]:\n{generation2}")
            
        if "Final Answer:" in generation2:
            return generation2.split("Final Answer:")[-1].strip()
        if "최종 답변:" in generation2:
            return generation2.split("최종 답변:")[-1].strip()
            
        return generation2

    def chat(self, user_input: str, history: list = None) -> str:
        # 1. 의도 분류 (Intent Classification)
        intent_res = self.intent_chain.invoke({"input": user_input})
        intent = intent_res.content.strip().upper()
        if self.verbose:
            print(f"\n[의도 게이트] 감지된 의도: {intent}")

        chat_history_str = self._get_history_str(history)

        # 2. 의도에 따른 분기 처리
        if "DIAGNOSTIC" in intent:
            if self.verbose:
                print("[에이전트] ROS diagnostics/ReAct 패턴 실행 중...")
            output = self._execute_react(user_input)
        else:
            if self.verbose:
                print("[일반 대화] 일상 및 기타 질의 처리 중...")
            response = self.chat_chain.invoke({
                "input": user_input,
                "chat_history": chat_history_str
            })
            output = response.content

        return output

# 5. 실행 테스트 및 CLI 루프
if __name__ == "__main__":
    agent = GolfbotAgent(verbose=True)
    print("====================================================")
    print(" Golfbot Conversational Agent (ReAct + Intent Gate) ")
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