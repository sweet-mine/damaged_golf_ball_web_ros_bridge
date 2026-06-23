import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agents.agent import GolfbotAgent

def test():
    print("Initializing Agent...")
    agent = GolfbotAgent(verbose=True)
    
    print("\n--- Test 1: Casual Chat ---")
    res1 = agent.chat("안녕? 반가워. 너의 역할을 소개해줘.", [])
    print("Response 1:", res1)
    
    print("\n--- Test 2: Diagnostic Tool Call ---")
    res2 = agent.chat("현재 시스템에 켜져 있는 ROS2 노드 목록을 알려줘.", [])
    print("Response 2:", res2)

if __name__ == "__main__":
    test()
