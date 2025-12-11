"""
Agent B 대화 흐름 분석 테스트

테스트 시나리오:
1. 단일 메시지만 분석 → 낮은 확률
2. 대화 흐름 분석 → 높은 확률 (가족 사칭 패턴)
"""
import sys
sys.path.insert(0, ".")

from agent.core.threat_matcher import (
    analyze_incoming_message,
    analyze_conversation_flow,
    detect_threats
)

print("=" * 60)
print("Agent B 대화 흐름 분석 테스트")
print("=" * 60)

# 테스트 1: 단일 메시지만 분석
print("\n[테스트 1] 단일 메시지 분석")
print("-" * 40)
single_message = "50만원만 보내줘"
result1 = analyze_incoming_message(single_message)
print(f"메시지: '{single_message}'")
print(f"사기 확률: {result1['final_assessment']['scam_probability']}%")
print(f"위험 레벨: {result1['final_assessment']['risk_level']}")

# 테스트 2: 대화 흐름 분석 (가족 사칭 시나리오)
print("\n[테스트 2] 대화 흐름 분석 (가족 사칭 A-1)")
print("-" * 40)
conversation_history = [
    {"sender_id": 1, "message": "엄마야?"},
    {"sender_id": 2, "message": "응? 누구야?"},
    {"sender_id": 1, "message": "나 폰 바꿨어"},
    {"sender_id": 1, "message": "폰 액정 깨졌어"},
    {"sender_id": 1, "message": "50만원만 보내줘"},
]

print("대화 히스토리:")
for msg in conversation_history:
    role = "발신자" if msg["sender_id"] == 1 else "수신자"
    print(f"  [{role}] {msg['message']}")

# 대화 흐름 분석
flow_result = analyze_conversation_flow(conversation_history, current_sender_id=1)
print(f"\n대화 흐름 분석 결과:")
print(f"  흐름 감지: {flow_result['flow_matched']}")
print(f"  감지된 패턴: {flow_result.get('matched_flow', 'N/A')} - {flow_result.get('matched_flow_name', 'N/A')}")
print(f"  매칭된 단계: {flow_result['matched_stages']}")
print(f"  확률 배율: x{flow_result['probability_multiplier']}")
print(f"  설명: {flow_result['flow_description']}")

# 테스트 3: 단일 메시지 vs 대화 흐름 비교
print("\n[테스트 3] 확률 비교")
print("-" * 40)
# 마지막 메시지만 분석
last_message = "50만원만 보내줘"
single_result = analyze_incoming_message(last_message)
single_prob = single_result['final_assessment']['scam_probability']

# 대화 흐름 적용 시 조정된 확률
if flow_result['flow_matched']:
    adjusted_prob = min(int(single_prob * flow_result['probability_multiplier']), 100)
    # 최소 확률 보장 (흐름 패턴 감지 시)
    if adjusted_prob < 40 and flow_result['stages_matched_count'] >= 3:
        adjusted_prob = max(adjusted_prob, 60)
else:
    adjusted_prob = single_prob

print(f"단일 메시지 분석: {single_prob}%")
print(f"대화 흐름 적용: {adjusted_prob}% (x{flow_result['probability_multiplier']} 배율)")
print(f"확률 상승: +{adjusted_prob - single_prob}%p")

# 테스트 4: 안전한 대화 (false positive 테스트)
print("\n[테스트 4] 안전한 대화 (False Positive 테스트)")
print("-" * 40)
safe_conversation = [
    {"sender_id": 1, "message": "엄마 오늘 저녁 뭐 먹어?"},
    {"sender_id": 2, "message": "뭐 먹고 싶어?"},
    {"sender_id": 1, "message": "치킨 먹고 싶어"},
    {"sender_id": 2, "message": "그래 치킨 시켜줄게"},
]

print("대화 히스토리:")
for msg in safe_conversation:
    role = "발신자" if msg["sender_id"] == 1 else "수신자"
    print(f"  [{role}] {msg['message']}")

safe_flow_result = analyze_conversation_flow(safe_conversation, current_sender_id=1)
print(f"\n대화 흐름 분석 결과:")
print(f"  흐름 감지: {safe_flow_result['flow_matched']}")
print(f"  설명: {safe_flow_result['flow_description']}")

print("\n" + "=" * 60)
print("테스트 완료!")
print("=" * 60)
