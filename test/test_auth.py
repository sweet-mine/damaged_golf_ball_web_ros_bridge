import sys
import os
import pytest
from fastapi.testclient import TestClient

# Add parent directory to path to import app and routers
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ros2_fastapi_bridge import app
from routers.auth import login_attempts

client = TestClient(app)

@pytest.fixture(autouse=True)
def run_before_and_after_tests():
    # Clear lockout tracker before and after each test
    login_attempts.clear()
    yield
    login_attempts.clear()

def test_login_success():
    payload = {
        "username": "admin",
        # SHA256 of "ssafy154"
        "password_hash": "af546aa7c671a0ddea8c4abd22f0c46761f94fc197cf3119e1e2cd3576424d20"
    }
    response = client.post("/api/auth/login", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "token" in data

def test_login_invalid_credentials():
    payload = {
        "username": "admin",
        "password_hash": "wrong_hash_value"
    }
    response = client.post("/api/auth/login", json=payload)
    assert response.status_code == 400
    data = response.json()
    assert "올바르지 않습니다" in data["detail"]

def test_login_brute_force_lockout():
    payload = {
        "username": "admin",
        "password_hash": "wrong_hash_value"
    }
    
    # 1st to 4th failed attempts: returns 400 with remaining attempts
    for i in range(4):
        response = client.post("/api/auth/login", json=payload)
        assert response.status_code == 400
        assert f"남은 시도 횟수: {4 - i}회" in response.json()["detail"]
        
    # 5th failed attempt: returns 429 indicating lockout has started
    response = client.post("/api/auth/login", json=payload)
    assert response.status_code == 429
    assert "차단됩니다" in response.json()["detail"]
    
    # 6th attempt: immediately locked out
    response = client.post("/api/auth/login", json=payload)
    assert response.status_code == 429
    assert "너무 많은 로그인 시도가 발생했습니다" in response.json()["detail"]
