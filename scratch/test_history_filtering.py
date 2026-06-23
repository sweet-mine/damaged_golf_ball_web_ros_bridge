import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agents.agent import GolfbotAgent

def test():
    print("Initializing Agent...")
    agent = GolfbotAgent(verbose=True)
    
    print("\n--- Test: Querying Today's Broken Ball History ---")
    # Today's date will be resolved to 2026-06-23 by the server time return
    res = agent.chat("오늘 있었던 파손 공 이력 알려줘", [])
    print("Response:", res)

if __name__ == "__main__":
    test()
