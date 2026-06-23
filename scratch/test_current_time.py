import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agents.agent import GolfbotAgent

def test():
    print("Initializing Agent...")
    agent = GolfbotAgent(verbose=True)
    
    print("\n--- Test 1: Generic Message (Should NOT invoke tool) ---")
    res1 = agent.chat("안녕? 넌 누구야?", [])
    print("Response 1:", res1)
    
    print("\n--- Test 2: Current Time Query (Should invoke get_current_time) ---")
    res2 = agent.chat("오늘이 며칠이고 지금 몇 시야?", [])
    print("Response 2:", res2)

if __name__ == "__main__":
    test()
