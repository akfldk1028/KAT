import requests
import json

BASE_URL = "http://localhost:8002/api/security"

def test_outgoing():
    print("\nTesting Outgoing Analysis...")
    # 1. Normal text
    payload = {"text": "안녕하세요"}
    response = requests.post(f"{BASE_URL}/analyze/outgoing", json=payload)
    print(f"Normal: {response.json()}")

    # 2. Sensitive text (Account Number)
    payload = {"text": "계좌번호 123-45-67890 보내줘"}
    response = requests.post(f"{BASE_URL}/analyze/outgoing", json=payload)
    print(f"Sensitive: {response.json()}")

def test_incoming():
    print("\nTesting Incoming Analysis...")
    # 1. Normal text
    payload = {"text": "밥 먹었니?"}
    response = requests.post(f"{BASE_URL}/analyze/incoming", json=payload)
    print(f"Normal: {response.json()}")

    # 2. Phishing text
    payload = {"text": "엄마 나 폰 고장났어 급하게 돈 좀 보내줘"}
    response = requests.post(f"{BASE_URL}/analyze/incoming", json=payload)
    print(f"Phishing: {response.json()}")

if __name__ == "__main__":
    try:
        test_outgoing()
        test_incoming()
    except Exception as e:
        print(f"Test failed: {e}")
