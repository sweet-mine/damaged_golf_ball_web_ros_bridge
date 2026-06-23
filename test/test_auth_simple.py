import sys
import os
import time
from fastapi.testclient import TestClient

# Add parent directory to path to import app and routers
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ros2_fastapi_bridge import app
from routers.auth import login_attempts, active_tokens

client = TestClient(app)

def run_tests():
    print("Running auth tests...")
    
    # Reset state
    login_attempts.clear()
    active_tokens.clear()
    
    # 1. Test Success & Token Validation
    payload = {
        "username": "admin",
        "password_hash": "af546aa7c671a0ddea8c4abd22f0c46761f94fc197cf3119e1e2cd3576424d20"
    }
    response = client.post("/api/auth/login", json=payload)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    data = response.json()
    assert data["status"] == "success", f"Expected success status, got {data['status']}"
    assert "token" in data, "Token not found in response"
    assert "expires_at" in data, "Expiration time not found in response"
    
    token = data["token"]
    original_expires_at = data["expires_at"]
    
    # Manually backdate the expiration time in memory to simulate time elapsed
    active_tokens[token]["expires_at"] = original_expires_at - 10000
    
    # Validate the token (this should slide/extend the expiration time)
    headers = {"Authorization": f"Bearer {token}"}
    val_response = client.get("/api/auth/validate", headers=headers)
    assert val_response.status_code == 200
    val_data = val_response.json()
    assert val_data["status"] == "success"
    assert val_data["username"] == "admin"
    # The new expires_at must be updated (larger than the backdated value)
    assert val_data["expires_at"] > original_expires_at - 5000
    print("Test 1: Success login and sliding token validation passed!")
    
    # 2. Test Invalid Token
    bad_headers = {"Authorization": "Bearer invalid_token_value"}
    val_response = client.get("/api/auth/validate", headers=bad_headers)
    assert val_response.status_code == 401
    
    bad_headers_no_bearer = {"Authorization": "invalid_format"}
    val_response = client.get("/api/auth/validate", headers=bad_headers_no_bearer)
    assert val_response.status_code == 401
    print("Test 2: Invalid/missing token validation passed!")
    
    # 3. Test Expired Token
    # Manually expire the token in the store
    active_tokens[token]["expires_at"] = int((time.time() - 10) * 1000)
    val_response = client.get("/api/auth/validate", headers=headers)
    assert val_response.status_code == 401
    assert token not in active_tokens  # Verify token was cleaned up
    print("Test 3: Token expiration detection and cleanup passed!")
    
    # Reset state for brute force test
    login_attempts.clear()
    active_tokens.clear()
    
    # 4. Test Brute Force Lockout (5 attempts)
    payload = {
        "username": "admin",
        "password_hash": "wrong_hash_value"
    }
    
    # 1st to 4th failed attempts: returns 400 with remaining attempts
    for i in range(4):
        response = client.post("/api/auth/login", json=payload)
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        expected_remaining = 5 - (i + 1)
        assert f"남은 시도 횟수: {expected_remaining}회" in response.json()["detail"], f"Unexpected error detail: {response.json()['detail']}"
        
    # The 5th fail: should return 429 and start lockout
    response = client.post("/api/auth/login", json=payload)
    assert response.status_code == 429, f"Expected 429, got {response.status_code}"
    assert "차단됩니다" in response.json()["detail"], f"Unexpected detail: {response.json()['detail']}"
    
    # The 6th request: should return 429 immediately indicating lockout is active
    response = client.post("/api/auth/login", json=payload)
    assert response.status_code == 429, f"Expected 429, got {response.status_code}"
    assert "너무 많은 로그인 시도가 발생했습니다" in response.json()["detail"], f"Unexpected detail: {response.json()['detail']}"
    print("Test 4: Brute force lockout protection passed!")
    
    print("All auth tests completed successfully!")

if __name__ == "__main__":
    run_tests()

