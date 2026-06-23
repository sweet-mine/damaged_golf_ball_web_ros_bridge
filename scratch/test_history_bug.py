import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agents.agent import GolfbotAgent

def test():
    agent = GolfbotAgent(verbose=True)
    
    # Simulate history from web client
    history = [
        {"role": "assistant", "content": "안녕하세요! Golfbot 로봇 제어 어시스턴트입니다. 무엇을 도와드릴까요?"}
    ]
    message = "현재 실행 중인 노드 목록을 보여줘"
    
    print("Running chat with history...")
    res = agent.chat(message, history)
    print("Result:", res)

if __name__ == "__main__":
    test()
