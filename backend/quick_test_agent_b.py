"""
빠른 Agent B 테스트 - 간단한 데이터로 즉시 결과 확인
"""
import requests
import json
from datetime import datetime
import sys
import io

# UTF-8 출력 설정
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

AGENT_B_URL = "http://localhost:8002/api/agents/analyze/incoming"
METRICS_URL = "http://localhost:3001/api/metrics/agent-b"

# 간단한 테스트 케이스
test_cases = [
    {
        "case_id": "TEST-001",
        "text": "엄마 바빠? 급하게 돈 좀 보내줘. 폰 인증이 안돼서 이체가 안되네 ㅠㅠ",
        "expected": "HIGH"
    },
    {
        "case_id": "TEST-002",
        "text": "아빠 나 핸드폰 액정 깨져서 보험 신청해야 하는데 인증 좀 해줄 수 있어?",
        "expected": "HIGH"
    },
    {
        "case_id": "TEST-003",
        "text": "회원님들 오늘도 수익 축하드립니다. 무료 체험방 입장하기",
        "expected": "MEDIUM"
    },
    {
        "case_id": "TEST-004",
        "text": "안녕하세요. XX은행 대출상담팀입니다. 대출 심사 결과 승인 가능하십니다.",
        "expected": "MEDIUM"
    },
    {
        "case_id": "TEST-005",
        "text": "엄마 저녁에 뭐 먹어?",
        "expected": "LOW"
    }
]

print("="*80)
print("Agent B 빠른 테스트 시작")
print("="*80)

results = []
high_risk = 0
medium_risk = 0
low_risk = 0
total_scam_prob = 0

for i, case in enumerate(test_cases, 1):
    print(f"\n[{i}/{len(test_cases)}] {case['case_id']} 테스트 중...")

    try:
        response = requests.post(
            AGENT_B_URL,
            json={
                "text": case["text"],
                "sender_id": 999,
                "receiver_id": 1,
                "use_ai": True
            },
            timeout=30
        )
        response.raise_for_status()
        result = response.json()

        risk_level = result["risk_level"]
        category = result.get("category", "N/A")
        scam_prob = result.get("scam_probability", 0)

        print(f"  결과: {risk_level}")
        print(f"  카테고리: {category}")
        print(f"  사기 확률: {scam_prob}%")
        match = "OK" if risk_level == case['expected'] else "FAIL"
        print(f"  예상: {case['expected']} | 실제: {risk_level} [{match}]")

        results.append(result)

        if risk_level in ["HIGH", "CRITICAL"]:
            high_risk += 1
        elif risk_level == "MEDIUM":
            medium_risk += 1
        else:
            low_risk += 1

        if scam_prob:
            total_scam_prob += scam_prob

    except Exception as e:
        print(f"  [ERROR] 실패: {e}")

# 통계 계산
avg_scam_prob = total_scam_prob / len(test_cases) if test_cases else 0

print("\n" + "="*80)
print("테스트 결과 요약")
print("="*80)
print(f"총 케이스: {len(test_cases)}")
print(f"HIGH 위험: {high_risk}개")
print(f"MEDIUM 위험: {medium_risk}개")
print(f"LOW 위험: {low_risk}개")
print(f"평균 사기 확률: {avg_scam_prob:.2f}%")

# Grafana로 메트릭 전송
metrics_data = {
    "agent_b_test_results": {
        "total_cases": len(test_cases),
        "high_risk_count": high_risk,
        "medium_risk_count": medium_risk,
        "low_risk_count": low_risk,
        "avg_scam_probability": round(avg_scam_prob, 2),
        "category_distribution": {"quick_test": len(test_cases)}
    },
    "timestamp": datetime.now().isoformat()
}

print("\n" + "="*80)
print("Grafana 메트릭 전송 중...")
print("="*80)

try:
    response = requests.post(METRICS_URL, json=metrics_data, timeout=5)
    response.raise_for_status()
    print("[SUCCESS] Grafana에서 확인하세요:")
    print("   http://localhost:3001/api/metrics/agent-b")
    print("   http://localhost:3001/metrics (Prometheus 형식)")
except Exception as e:
    print(f"[ERROR] 전송 실패: {e}")

print("\n메트릭 데이터:")
print(json.dumps(metrics_data, indent=2, ensure_ascii=False))
print("="*80)
