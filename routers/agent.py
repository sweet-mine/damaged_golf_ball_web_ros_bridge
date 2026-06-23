import sys
import os
import tempfile
import json
from fastapi import APIRouter, HTTPException, File, UploadFile, Form
from pydantic import BaseModel, Field

from typing import List, Dict, Any
from faster_whisper import WhisperModel

# Ensure parent directory is in path for absolute/relative imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agents.agent import GolfbotAgent

router = APIRouter(prefix="/api/agent", tags=["agent"])

# Instantiate the conversational agent as a singleton for the dashboard
agent = GolfbotAgent(verbose=True)

# Lazy load WhisperModel to keep server startup fast
whisper_model = None

def get_whisper_model():
    global whisper_model
    if whisper_model is None:
        # Load the base model on CPU using int8 quantization for speed and low memory footprint
        whisper_model = WhisperModel("base", device="cpu", compute_type="int8")
    return whisper_model

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="Message to send to the LLM agent")
    history: List[Dict[str, Any]] = Field(default_factory=list, description="Chat history context")

@router.post("/chat")
async def chat_with_agent(req: ChatRequest):
    try:
        print("API REQUEST - MESSAGE:", req.message)
        print("API REQUEST - HISTORY:", req.history)
        response_text = agent.chat(req.message, req.history)
        print("API RESPONSE:", response_text)
        return {
            "status": "success",
            "response": response_text
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Agent execution error: {str(e)}")

@router.post("/voice")
async def chat_with_agent_voice(
    file: UploadFile = File(...),
    history: str = Form("[]")
):
    try:
        # 1. Save uploaded file to a temporary file
        suffix = os.path.splitext(file.filename)[1] or ".wav"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_audio:
            temp_audio.write(await file.read())
            temp_path = temp_audio.name
        
        # 2. Transcribe using faster-whisper (force Korean transcription)
        model = get_whisper_model()
        segments, info = model.transcribe(temp_path, beam_size=5, language="ko")
        transcription = "".join([segment.text for segment in segments]).strip()
        
        # Clean up temp file
        if os.path.exists(temp_path):
            os.remove(temp_path)
            
        if not transcription:
            return {
                "status": "success",
                "transcription": "",
                "response": "음성이 인식되지 않았습니다. 다시 말씀해 주세요."
            }
        
        # 3. Parse history from JSON string
        try:
            history_list = json.loads(history)
        except Exception:
            history_list = []
            
        # 4. Get LLM response
        response_text = agent.chat(transcription, history_list)
        
        return {
            "status": "success",
            "transcription": transcription,
            "response": response_text
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Voice agent error: {str(e)}")


