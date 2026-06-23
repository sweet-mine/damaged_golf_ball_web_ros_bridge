import os
import time
import secrets
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
import dotenv

# Load environment variables from the .env file next to this routers folder
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
dotenv.load_dotenv(os.path.join(base_dir, ".env"))

router = APIRouter(prefix="/api/auth", tags=["auth"])

class LoginRequest(BaseModel):
    username: str
    password_hash: str

# In-memory stores:
# ip -> {"attempts": int, "lockout_until": float}
login_attempts = {}
# token -> {"username": str, "expires_at": int} (timestamp in ms)
active_tokens = {}

MAX_ATTEMPTS = 5
LOCKOUT_DURATION = 60 # seconds
TOKEN_EXPIRE_DURATION = 3600 # 1 hour (in seconds)

CORRECT_USERNAME = os.getenv("GOLFBOT_ADMIN_USERNAME", "admin")
CORRECT_PASSWORD_HASH = os.getenv(
    "GOLFBOT_ADMIN_PASSWORD_HASH",
    "af546aa7c671a0ddea8c4abd22f0c46761f94fc197cf3119e1e2cd3576424d20"
)

@router.post("/login")
async def login(req: LoginRequest, request: Request):
    ip = request.client.host
    now = time.time()
    
    # Check if this IP is currently locked out
    if ip in login_attempts:
        state = login_attempts[ip]
        if state["lockout_until"] > now:
            remaining = int(state["lockout_until"] - now)
            raise HTTPException(
                status_code=429,
                detail=f"너무 많은 로그인 시도가 발생했습니다. {remaining}초 후에 다시 시도하세요."
            )
        # If lockout duration has passed, reset attempts
        if state["lockout_until"] > 0:
            login_attempts[ip] = {"attempts": 0, "lockout_until": 0.0}
            
    # Verify username and password hash
    if req.username == CORRECT_USERNAME and req.password_hash == CORRECT_PASSWORD_HASH:
        # Success: reset attempts for this IP
        login_attempts[ip] = {"attempts": 0, "lockout_until": 0.0}
        
        # Generate a secure random token
        token = secrets.token_hex(32)
        # Calculate expiration time in milliseconds (since JavaScript uses ms)
        expires_at = int((now + TOKEN_EXPIRE_DURATION) * 1000)
        
        active_tokens[token] = {
            "username": req.username,
            "expires_at": expires_at
        }
        
        return {
            "status": "success",
            "message": "로그인에 성공했습니다.",
            "token": token,
            "expires_at": expires_at
        }
    else:
        # Failure: record attempt
        if ip not in login_attempts:
            login_attempts[ip] = {"attempts": 0, "lockout_until": 0.0}
        
        login_attempts[ip]["attempts"] += 1
        
        if login_attempts[ip]["attempts"] >= MAX_ATTEMPTS:
            login_attempts[ip]["lockout_until"] = now + LOCKOUT_DURATION
            raise HTTPException(
                status_code=429,
                detail=f"로그인 시도가 5회 실패하여 {LOCKOUT_DURATION}초 동안 차단됩니다."
            )
        else:
            remaining_attempts = MAX_ATTEMPTS - login_attempts[ip]["attempts"]
            raise HTTPException(
                status_code=400,
                detail=f"아이디 또는 비밀번호가 올바르지 않습니다. (남은 시도 횟수: {remaining_attempts}회)"
            )

@router.get("/validate")
async def validate_token(request: Request):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="인증 헤더가 누락되었거나 형식이 올바르지 않습니다.")
    
    token = auth_header.split(" ")[1]
    
    if token not in active_tokens:
        raise HTTPException(status_code=401, detail="유효하지 않은 토큰입니다.")
        
    token_info = active_tokens[token]
    current_time_ms = int(time.time() * 1000)
    
    if current_time_ms > token_info["expires_at"]:
        # Token expired, clean it up
        del active_tokens[token]
        raise HTTPException(status_code=401, detail="인증 토큰의 유효시간이 만료되었습니다.")
        
    # Slide expiration: extend by another TOKEN_EXPIRE_DURATION
    new_expires_at = int((time.time() + TOKEN_EXPIRE_DURATION) * 1000)
    token_info["expires_at"] = new_expires_at
    
    return {
        "status": "success",
        "username": token_info["username"],
        "expires_at": new_expires_at
    }

