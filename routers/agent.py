import sys
import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from typing import List, Dict, Any

# Ensure parent directory is in path for absolute/relative imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agents.agent import GolfbotAgent

router = APIRouter(prefix="/api/agent", tags=["agent"])

# Instantiate the conversational agent as a singleton for the dashboard
agent = GolfbotAgent(verbose=True)

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="Message to send to the LLM agent")
    history: List[Dict[str, Any]] = Field(default_factory=list, description="Chat history context")

@router.post("/chat")
async def chat_with_agent(req: ChatRequest):
    try:
        response_text = agent.chat(req.message, req.history)
        return {
            "status": "success",
            "response": response_text
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Agent execution error: {str(e)}")


