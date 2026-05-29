from langchain_ollama import ChatOllama
import sys

def test():
    llm = ChatOllama(model="gemma4:e2b", temperature=0)
    llm_with_stop = llm.bind(stop=["\nObservation:", "\n\tObservation:"])
    
    prompt_no_space = (
        "당신은 ROS2 시스템을 진단하는 로봇 소프트웨어 전문 AI 어시스턴트입니다. 주어진 도구를 활용해 사용자의 질문에 정확하게 답변하세요.\n\n"
        "도구 목록:\n"
        "get_node_list(namespace: str = '') -> Dict[str, Any] - 현재 시스템에 실행 중인 ROS2 노드 목록을 반환합니다.\n"
        "get_topic_list(include_hidden: str = 'False') -> Dict[str, Any] - 현재 활성화된 ROS2 토픽 목록을 반환합니다.\n\n"
        "반드시 아래 형식을 엄격하게 준수하여 답변을 작성하세요:\n\n"
        "Question: 답변해야 하는 질문\n"
        "Thought: 질문에 어떻게 대답해야 할지 생각 (예: 도구 호출 필요성 판단)\n"
        "Action: 사용할 도구 이름 (반드시 [get_node_list, get_topic_list] 중 하나만 선택)\n"
        "Action Input: 도구에 제공할 매개변수 입력\n"
        "Observation: 도구 실행 결과\n"
        "Thought: 이제 최종 답변을 알고 있음\n"
        "Final Answer: 사용자의 질문에 대한 최종적이고 상세한 한국어 답변\n\n"
        "시작!\n\n"
        "Question: 현재 활성화된 토픽 목록 알려줘\n"
        "Thought: 사용자는 현재 활성화된 ROS2 토픽 목록을 요청하고 있습니다. 이를 위해서는 `get_topic_list` 도구를 사용해야 합니다.\n"
        "Action: get_topic_list\n"
        "Action Input: include_hidden='False'\n"
        "Observation: {'success': True, 'topic_count': 2, 'topics': ['/parameter_events', '/rosout'], 'raw_output': '/parameter_events\\n/rosout\\n'}\n"
        "Thought:"
    )
    
    prompt_with_space = prompt_no_space + " "

    print("=== Calling ChatOllama WITHOUT trailing space ===")
    resp = llm_with_stop.invoke(prompt_no_space)
    print("Response (No space):")
    print(repr(resp.content))

    print("\n=== Calling ChatOllama WITH trailing space ===")
    resp2 = llm_with_stop.invoke(prompt_with_space)
    print("Response (With space):")
    print(repr(resp2.content))

if __name__ == "__main__":
    test()
