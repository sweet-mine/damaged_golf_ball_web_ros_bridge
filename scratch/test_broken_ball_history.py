import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agents.agent import GolfbotAgent

def test():
    print("Initializing Agent...")
    agent = GolfbotAgent(verbose=True)
    
    print("\n--- Test: Querying Broken Ball History ---")
    res = agent.chat("지금까지 발견된 파손된 공 이력(목록)을 확인해줘.", [])
    print("Response:", res)

if __name__ == "__main__":
    test()
