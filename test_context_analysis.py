"""
대화 맥락 분석 테스트 (SE-OmniGuard 연구 기반)

LLM이 대화 흐름을 분석하여 사기 패턴을 감지하는지 확인
"""
import requests
import json

API_URL = "http://localhost:8002/api/agents/analyze/incoming"

def test_context_analysis():
    """
    다중 턴 대화에서 사기 패턴 감지 테스트

    시나리오: 가족 사칭 사기
    1단계 - 관계형성: "엄마 나야"
    2단계 - 상황조성: "폰이 고장났어"
    3단계 - 요구실행: "급하게 돈 보내줘"
    """
    print("=" * 60)
    print("대화 맥락 분석 테스트 (LLM Context Analysis)")
    print("=" * 60)

    # 대화 히스토리 (시간순)
    conversation_history = [
        {"sender_id": 999, "message": "엄마 나야", "timestamp": "2025-01-01T10:00:00"},
        {"sender_id": 999, "message": "폰이 고장나서 새 번호로 연락해", "timestamp": "2025-01-01T10:01:00"},
        {"sender_id": 1, "message": "어? 무슨 일이야?", "timestamp": "2025-01-01T10:02:00"},
        {"sender_id": 999, "message": "급하게 돈이 필요해", "timestamp": "2025-01-01T10:03:00"},
    ]

    # 현재 분석할 메시지 (마지막 메시지)
    current_message = "50만원만 이 계좌로 보내줘 3333-04-1234567"

    request_data = {
        "text": current_message,
        "sender_id": 999,
        "receiver_id": 1,
        "conversation_history": conversation_history,
        "use_ai": True
    }

    print(f"\n[대화 히스토리]")
    for i, msg in enumerate(conversation_history, 1):
        sender = "상대방" if msg["sender_id"] == 999 else "나"
        print(f"  {i}. [{sender}] {msg['message']}")

    print(f"\n[현재 메시지 (분석 대상)]")
    print(f"  → {current_message}")

    print(f"\n[API 요청 중...]")

    try:
        response = requests.post(
            API_URL,
            json=request_data,
            headers={"Content-Type": "application/json"},
            timeout=60
        )

        if response.status_code == 200:
            result = response.json()
            print(f"\n[분석 결과]")
            print(f"  - 위험 레벨: {result.get('risk_level')}")
            print(f"  - 이유: {result.get('reasons')}")
            print(f"  - 카테고리: {result.get('category')}")
            print(f"  - 카테고리명: {result.get('category_name')}")
            print(f"  - 사기 확률: {result.get('scam_probability')}%")
            print(f"  - 권장 조치: {result.get('recommended_action')}")

            # 성공 여부 확인
            if result.get('risk_level') in ['HIGH', 'CRITICAL']:
                print(f"\n✅ 테스트 성공! 대화 맥락에서 사기 패턴을 감지했습니다.")
            else:
                print(f"\n⚠️  위험 레벨이 낮음 - LLM 맥락 분석 확인 필요")
        else:
            print(f"❌ API 오류: {response.status_code}")
            print(response.text)

    except Exception as e:
        print(f"❌ 요청 실패: {e}")


def test_single_message():
    """단일 메시지 분석 (대화 맥락 없음) - 비교용"""
    print("\n" + "=" * 60)
    print("단일 메시지 분석 (맥락 없음) - 비교용")
    print("=" * 60)

    current_message = "50만원만 이 계좌로 보내줘 3333-04-1234567"

    request_data = {
        "text": current_message,
        "sender_id": 999,
        "receiver_id": 1,
        "use_ai": True
        # conversation_history 없음!
    }

    print(f"\n[메시지]")
    print(f"  → {current_message}")

    try:
        response = requests.post(
            API_URL,
            json=request_data,
            headers={"Content-Type": "application/json"},
            timeout=60
        )

        if response.status_code == 200:
            result = response.json()
            print(f"\n[분석 결과]")
            print(f"  - 위험 레벨: {result.get('risk_level')}")
            print(f"  - 이유: {result.get('reasons')}")

    except Exception as e:
        print(f"❌ 요청 실패: {e}")


if __name__ == "__main__":
    test_context_analysis()
    test_single_message()
    print("\n" + "=" * 60)
    print("테스트 완료!")
