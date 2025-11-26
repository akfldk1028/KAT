"""
FastAPI 서브에이전트 API 테스트
"""

import sys
import os
import requests
import json

# Windows UTF-8 출력 설정
if os.name == 'nt':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

API_BASE_URL = "http://127.0.0.1:8000"

def test_outgoing_agent():
    """안심 전송 Agent API 테스트"""
    print("=" * 60)
    print("🔒 안심 전송 Agent API 테스트")
    print("=" * 60)

    test_cases = [
        {
            "name": "계좌번호 포함",
            "data": {"text": "이 계좌로 30만원 보내줘 123-45-67890"}
        },
        {
            "name": "주민번호 포함",
            "data": {"text": "주민번호 900101-1234567 이거야"}
        },
        {
            "name": "일반 메시지",
            "data": {"text": "오늘 저녁 같이 먹을래?"}
        }
    ]

    for i, case in enumerate(test_cases, 1):
        print(f"\n[테스트 {i}] {case['name']}")
        print(f"메시지: {case['data']['text']}")

        response = requests.post(
            f"{API_BASE_URL}/api/agents/analyze/outgoing",
            json=case['data']
        )

        if response.status_code == 200:
            result = response.json()
            print(f"✅ 위험도: {result['risk_level']}")
            print(f"   이유: {', '.join(result['reasons']) if result['reasons'] else '없음'}")
            print(f"   권장 조치: {result['recommended_action']}")
            print(f"   시크릿 전송 추천: {result['is_secret_recommended']}")
        else:
            print(f"❌ 오류: {response.status_code} - {response.text}")

def test_incoming_agent():
    """안심 가드 Agent API 테스트"""
    print("\n\n" + "=" * 60)
    print("🛡️ 안심 가드 Agent API 테스트")
    print("=" * 60)

    test_cases = [
        {
            "name": "가족 사칭 + 급전 요구",
            "data": {"text": "엄마, 나 폰 고장나서 번호 바뀌었어. 급해서 그런데 돈 좀 빨리 보내줄 수 있어?"}
        },
        {
            "name": "피싱 링크",
            "data": {"text": "택배가 도착했습니다. http://phishing.com에서 확인하세요"}
        },
        {
            "name": "일반 메시지",
            "data": {"text": "오늘 점심 뭐 먹을래?"}
        }
    ]

    for i, case in enumerate(test_cases, 1):
        print(f"\n[테스트 {i}] {case['name']}")
        print(f"메시지: {case['data']['text']}")

        response = requests.post(
            f"{API_BASE_URL}/api/agents/analyze/incoming",
            json=case['data']
        )

        if response.status_code == 200:
            result = response.json()
            print(f"✅ 위험도: {result['risk_level']}")
            print(f"   이유: {', '.join(result['reasons']) if result['reasons'] else '없음'}")
            print(f"   권장 조치: {result['recommended_action']}")
        else:
            print(f"❌ 오류: {response.status_code} - {response.text}")

def test_health():
    """헬스체크 테스트"""
    print("\n\n" + "=" * 60)
    print("💚 헬스체크 테스트")
    print("=" * 60)

    response = requests.get(f"{API_BASE_URL}/api/agents/health")

    if response.status_code == 200:
        result = response.json()
        print(f"✅ 상태: {result['status']}")
        print(f"   메시지: {result['message']}")
        print(f"   에이전트: {json.dumps(result['agents'], indent=2, ensure_ascii=False)}")
    else:
        print(f"❌ 오류: {response.status_code} - {response.text}")

if __name__ == "__main__":
    print("\n🚀 Kanana DualGuard REST API 테스트 시작\n")

    test_health()
    test_outgoing_agent()
    test_incoming_agent()

    print("\n\n✅ 모든 API 테스트 완료!")
