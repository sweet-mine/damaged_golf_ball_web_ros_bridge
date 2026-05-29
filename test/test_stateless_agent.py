import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from agents.agent import GolfbotAgent

def test():
    # Instantiate the agent
    agent = GolfbotAgent(verbose=True)
    
    print("=== TEST 1: First Question (Get node list, stateless) ===")
    history_turn1 = []
    ans1 = agent.chat("현재 실행 중인 노드 목록을 보여줘", history_turn1)
    print(f"Answer 1: {ans1}")
    
    print("\n=== TEST 2: Second Question (Get topic list, stateless with Turn 1 history) ===")
    history_turn2 = [
        {"role": "user", "content": "현재 실행 중인 노드 목록을 보여줘"},
        {"role": "assistant", "content": ans1}
    ]
    ans2 = agent.chat("현재 활성화된 토픽 목록 알려줘", history_turn2)
    print(f"Answer 2: {ans2}")

if __name__ == "__main__":
    test()
