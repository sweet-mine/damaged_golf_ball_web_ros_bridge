from langchain_ollama import ChatOllama
import sys

def test():
    prompt = (
        "당신은 ROS2 시스템을 진단하는 로봇 소프트웨어 전문 AI 어시스턴트입니다. 주어진 도구를 활용해 사용자의 질문에 정확하게 답변하세요.\n\n"
        "도구 목록:\n"
        "get_node_list(namespace: str = '') -> Dict[str, Any] - 현재 시스템에 실행 중인 ROS2 노드 목록을 반환합니다.\n"
        "get_topic_list(include_hidden: str = 'False') -> Dict[str, Any] - 현재 활성화된 ROS2 토픽 목록을 반환합니다.\n"
        "get_topic_info(topic_name: str = '/rosout') -> Dict[str, Any] - 특정 ROS2 토픽의 타입, 퍼블리셔 및 서브스크라이버 개수 정보를 반환합니다.\n"
        "get_topic_hz(topic_name: str = '/rosout', timeout_sec: str = '2') -> Dict[str, Any] - 특정 토픽의 발행 주기(주파수, Hz)를 측정합니다. 무한 대기를 방지하기 위해 timeout이 적용됩니다.\n"
        "get_node_info(node_name: str = '') -> Dict[str, Any] - 특정 ROS2 노드의 상세 정보(Publishers, Subscribers, Services 등)를 반환합니다.\n"
        "get_system_diagnosis(include_network: str = 'False') -> Dict[str, Any] - 현재 ROS 시스템 정보를 파악하고 진단합니다. 리포트를 제공합니다.\n\n"
        "반드시 아래 형식을 엄격하게 준수하여 답변을 작성하세요:\n\n"
        "Question: 답변해야 하는 질문\n"
        "Thought: 질문에 어떻게 대답해야 할지 생각 (예: 도구 호출 필요성 판단)\n"
        "Action: 사용할 도구 이름 (반드시 [get_node_list, get_topic_list, get_topic_info, get_topic_hz, get_node_info, get_system_diagnosis] 중 하나만 선택. 만약 질문에 답하기 위해 도구를 사용할 필요가 없다면 Action과 Action Input 단계를 생략하고 바로 Final Answer를 작성하세요.)\n"
        "Action Input: 도구에 제공할 매개변수 입력\n"
        "Observation: 도구 실행 결과\n"
        "... (Thought/Action/Action Input/Observation 과정을 필요한 만큼 반복)\n"
        "Thought: 이제 최종 답변을 알고 있음\n"
        "Final Answer: 사용자의 질문에 대한 최종적이고 상세한 한국어 답변\n\n"
        "시작!\n\n"
        "Question: 현재 활성화된 토픽 목록 알려줘\n"
        "Thought: 사용자는 현재 활성화된 ROS2 토픽 목록을 요청하고 있습니다. 이를 위해서는 `get_topic_list` 도구를 사용해야 합니다.\n"
        "Action: get_topic_list\n"
        "Action Input: include_hidden='False'\n"
        "Observation: {'success': True, 'topic_count': 2, 'topics': ['/parameter_events', '/rosout'], 'raw_output': '/parameter_events\\n/rosout\\n'}\n"
        "Thought: "
    )

    print("=== Calling Gemma 2B WITH ALL 6 TOOLS ===")
    gemma = ChatOllama(model="gemma4:e2b", temperature=0).bind(stop=["\nObservation:", "\n\tObservation:"])
    print("Response:", repr(gemma.invoke(prompt).content))

    print("\n=== Calling Llama 3.2 3B WITH ALL 6 TOOLS ===")
    llama = ChatOllama(model="llama3.2:3b", temperature=0).bind(stop=["\nObservation:", "\n\tObservation:"])
    print("Response:", repr(llama.invoke(prompt).content))

if __name__ == "__main__":
    test()
