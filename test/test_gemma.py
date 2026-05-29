from langchain_ollama import ChatOllama
import sys

def test():
    # Use standard ChatOllama
    llm = ChatOllama(model="gemma4:e2b", temperature=0)
    
    # Prompt for Turn 1 (No history)
    prompt1 = (
        "당신은 ROS2 시스템을 진단하는 로봇 소프트웨어 전문 AI 어시스턴트입니다. 주어진 도구를 활용해 사용자의 질문에 정확하게 답변하세요.\n\n"
        "도구 목록:\n"
        "get_node_list: 현재 시스템에 실행 중인 ROS2 노드 목록을 반환합니다.\n"
        "get_topic_list: 현재 활성화된 ROS2 토픽 목록을 반환합니다.\n\n"
        "반드시 아래 형식을 엄격하게 준수하여 답변을 작성하세요:\n\n"
        "Question: 답변해야 하는 질문\n"
        "Thought: 질문에 어떻게 대답해야 할지 생각 (예: 도구 호출 필요성 판단)\n"
        "Action: 사용할 도구 이름 (반드시 [get_node_list, get_topic_list] 중 하나만 선택)\n"
        "Action Input: 도구에 제공할 매개변수 입력\n"
        "Observation: 도구 실행 결과\n"
        "Thought: 이제 최종 답변을 알고 있음\n"
        "Final Answer: 사용자의 질문에 대한 최종적이고 상세한 한국어 답변\n\n"
        "이전 대화 기록:\n"
        "이전 대화가 없습니다.\n\n"
        "시작!\n\n"
        "Question: 현재 실행 중인 노드 목록을 보여줘\n"
        "Thought:"
    )

    print("--- Test 1: Turn 1 with stop sequences ['\\nObservation:', '\\n\\tObservation:'] ---")
    try:
        llm_with_stop = llm.bind(stop=["\nObservation:", "\n\tObservation:"])
        resp = llm_with_stop.invoke(prompt1)
        print("Response content:")
        print(repr(resp.content))
    except Exception as e:
        print(f"Error: {e}")

    # Prompt for Turn 2 (with history and scratchpad)
    prompt2 = (
        "당신은 ROS2 시스템을 진단하는 로봇 소프트웨어 전문 AI 어시스턴트입니다. 주어진 도구를 활용해 사용자의 질문에 정확하게 답변하세요.\n\n"
        "도구 목록:\n"
        "get_node_list: 현재 시스템에 실행 중인 ROS2 노드 목록을 반환합니다.\n"
        "get_topic_list: 현재 활성화된 ROS2 토픽 목록을 반환합니다.\n\n"
        "반드시 아래 형식을 엄격하게 준수하여 답변을 작성하세요:\n\n"
        "Question: 답변해야 하는 질문\n"
        "Thought: 질문에 어떻게 대답해야 할지 생각 (예: 도구 호출 필요성 판단)\n"
        "Action: 사용할 도구 이름 (반드시 [get_node_list, get_topic_list] 중 하나만 선택)\n"
        "Action Input: 도구에 제공할 매개변수 입력\n"
        "Observation: 도구 실행 결과\n"
        "Thought: 이제 최종 답변을 알고 있음\n"
        "Final Answer: 사용자의 질문에 대한 최종적이고 상세한 한국어 답변\n\n"
        "이전 대화 기록:\n"
        "User: 현재 실행 중인 노드 목록을 보여줘\n"
        "Assistant: 현재 실행 중인 ROS2 노드 목록은 다음과 같습니다: /rosout, tf2_ros, tf2_buffer, robot_state_publisher, joint_state_publisher, static_frame, robot_description, camera_driver, imu_driver\n\n"
        "시작!\n\n"
        "Question: 현재 활성화된 토픽 목록 알려줘\n"
        "Thought: 사용자는 ROS2 토픽 목록을 요청했습니다. `get_topic_list` 도구를 사용하여 현재 활성화된 ROS2 토픽 목록을 가져와야 합니다.\n"
        "Action: get_topic_list\n"
        "Action Input: \n"
        "Observation: {'success': True, 'topic_count': 6, 'topics': ['/camera/image', '/imu/data', '/tf', '/tf_static', '/scan', '/points'], 'raw_output': '/camera/image\\n/imu/data\\n/tf\\n/tf_static\\n/scan\\n/points\\n'}\n"
        "Thought:"
    )

    print("\n--- Test 2: Turn 2 (Second step) with stop sequences ---")
    try:
        resp = llm_with_stop.invoke(prompt2)
        print("Response content:")
        print(repr(resp.content))
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test()
