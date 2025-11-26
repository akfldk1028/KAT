import requests
import sys

BASE_URL = "http://127.0.0.1:8001/api/auth"

def test_signup():
    print("Testing Signup...")
    payload = {
        "user_id": "testuser1",
        "password": "password123",
        "name": "Test User"
    }
    try:
        response = requests.post(f"{BASE_URL}/signup", json=payload)
        print(f"Status Code: {response.status_code}")
        try:
            print(f"Response: {response.json()}")
        except:
            print(f"Response Text: {response.text}")
        
        if response.status_code == 200:
            print("Signup Success!")
            return True
        elif response.status_code == 400 and "이미 사용중" in response.text:
             print("User already exists (Expected if re-running)")
             return True
        # Legacy frontend expects 200 even for some errors, but let's see what we implemented.
        # In auth.py we return AuthResponse (200) for duplicate user, BUT we also have unreachable raise HTTPException.
        # Actually, the return statement executes first, so it returns 200.
        else:
            print("Signup Failed")
            return False
    except Exception as e:
        print(f"Signup Error: {e}")
        return False

def test_login():
    print("\nTesting Login...")
    payload = {
        "user_id": "testuser1",
        "password": "password123"
    }
    try:
        response = requests.post(f"{BASE_URL}/login", json=payload)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        if response.status_code == 200 and "token" in response.json().get("data", {}):
            print("Login Success!")
            return True
        else:
            print("Login Failed")
            return False
    except Exception as e:
        print(f"Login Error: {e}")
        return False

if __name__ == "__main__":
    if test_signup():
        test_login()
