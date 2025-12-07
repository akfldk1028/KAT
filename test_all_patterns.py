"""
Agent B 전체 MECE 카테고리 대화 흐름 테스트

테스트 대상:
- A: 관계 사칭형 (A-1, A-2, A-3)
- B: 공포/권위 악용형 (B-1, B-2, B-3)
- C: 욕망/감정 자극형 (C-1, C-2, C-3)
"""
import sys
sys.path.insert(0, ".")

from agent.core.threat_matcher import analyze_conversation_flow

print("=" * 70)
print("Agent B 전체 MECE 카테고리 대화 흐름 테스트")
print("=" * 70)

# 테스트 시나리오 정의
TEST_SCENARIOS = {
    # ============================================================
    # A: 관계 사칭형 (Targeting Trust)
    # ============================================================
    "A-1": {
        "name": "가족 사칭 (액정 파손)",
        "conversation": [
            {"sender_id": 1, "message": "엄마야?"},
            {"sender_id": 2, "message": "응? 누구야?"},
            {"sender_id": 1, "message": "나 폰 바꿨어"},
            {"sender_id": 1, "message": "폰 액정 깨져서 수리 맡겼어"},
            {"sender_id": 1, "message": "급하게 인증해야 하는데 인증번호 좀 받아줘"},
        ]
    },
    "A-2": {
        "name": "지인/상사 사칭 (급전)",
        "conversation": [
            {"sender_id": 1, "message": "김 대리, 나야 팀장"},
            {"sender_id": 2, "message": "네 팀장님"},
            {"sender_id": 1, "message": "나 지금 미팅 중이라 폰뱅킹 안돼"},
            {"sender_id": 1, "message": "거래처에 급하게 300만원만 먼저 보내줄 수 있어?"},
            {"sender_id": 1, "message": "2시간 뒤에 바로 줄게"},
        ]
    },
    "A-3": {
        "name": "상품권 대리 구매",
        "conversation": [
            {"sender_id": 1, "message": "이모 나야"},
            {"sender_id": 2, "message": "응 왜?"},
            {"sender_id": 1, "message": "내가 지금 결제가 안 돼서 그래"},
            {"sender_id": 1, "message": "편의점 가서 구글 기프트카드 10만원짜리 좀 사줘"},
            {"sender_id": 1, "message": "뒤에 핀번호 사진 찍어 보내줘"},
        ]
    },

    # ============================================================
    # B: 공포/권위 악용형 (Targeting Fear & Authority)
    # ============================================================
    "B-1": {
        "name": "생활 밀착형 (택배/경조사)",
        "conversation": [
            {"sender_id": 1, "message": "[CJ대한통운] 택배 배송 안내"},
            {"sender_id": 1, "message": "운송장번호 주소 불일치로 배송 보류"},
            {"sender_id": 1, "message": "주소 수정: bit.ly/xxx 확인해주세요"},
        ]
    },
    "B-2": {
        "name": "기관 사칭 (건강/법무)",
        "conversation": [
            {"sender_id": 1, "message": "검찰청에서 연락드립니다"},
            {"sender_id": 1, "message": "귀하의 계좌가 범죄에 연루되어 조사 중입니다"},
            {"sender_id": 1, "message": "계좌 동결 전에 안전계좌로 이체가 필요합니다"},
            {"sender_id": 1, "message": "지금 당장 협조해주셔야 합니다"},
        ]
    },
    "B-3": {
        "name": "결제 승인 (낚시성)",
        "conversation": [
            {"sender_id": 1, "message": "[국외발신] 해외결제 알림"},
            {"sender_id": 1, "message": "아마존 결제완료 98만원 승인"},
            {"sender_id": 1, "message": "본인 아닐 시 즉시 문의: 02-XXX-XXXX"},
        ]
    },

    # ============================================================
    # C: 욕망/감정 자극형 (Targeting Desire & Emotion)
    # ============================================================
    "C-1": {
        "name": "투자 권유 (리딩방)",
        "conversation": [
            {"sender_id": 1, "message": "주식리딩방 무료 체험 안내"},
            {"sender_id": 1, "message": "이번에 세력 매집주 정보 입수했습니다"},
            {"sender_id": 1, "message": "300% 수익 보장합니다"},
            {"sender_id": 1, "message": "선착순 모집중! VIP방 들어오세요"},
        ]
    },
    "C-2": {
        "name": "로맨스 스캠",
        "conversation": [
            {"sender_id": 1, "message": "자기야 보고싶어"},
            {"sender_id": 2, "message": "나도~"},
            {"sender_id": 1, "message": "내가 한국으로 선물 보냈는데"},
            {"sender_id": 1, "message": "세관에 걸려서 통관비 500만원이 필요해"},
            {"sender_id": 1, "message": "다음달에 꼭 갚을게 honey"},
        ]
    },
    "C-3": {
        "name": "몸캠 피싱",
        "conversation": [
            {"sender_id": 1, "message": "오빠 영상통화 하자"},
            {"sender_id": 1, "message": "얼굴 보고싶어"},
            {"sender_id": 2, "message": "그래"},
            {"sender_id": 1, "message": "어 소리가 안 들려"},
            {"sender_id": 1, "message": "이 앱 깔면 화질도 좋아져. 이거 깔고 다시 하자"},
            {"sender_id": 1, "message": "링크로 들어와서 설치해 xxx.apk"},
        ]
    },

    # ============================================================
    # 안전한 대화 (False Positive 테스트)
    # ============================================================
    "SAFE-1": {
        "name": "일반 가족 대화",
        "conversation": [
            {"sender_id": 1, "message": "엄마 오늘 저녁 뭐 먹어?"},
            {"sender_id": 2, "message": "뭐 먹고 싶어?"},
            {"sender_id": 1, "message": "치킨 먹고 싶어"},
            {"sender_id": 2, "message": "그래 치킨 시켜줄게"},
        ]
    },
    "SAFE-2": {
        "name": "일반 친구 대화",
        "conversation": [
            {"sender_id": 1, "message": "야 오늘 뭐해?"},
            {"sender_id": 2, "message": "그냥 집에 있어"},
            {"sender_id": 1, "message": "영화 보러 갈래?"},
            {"sender_id": 2, "message": "좋아 몇시에?"},
        ]
    },
}

# 테스트 실행
results = []
for pattern_id, scenario in TEST_SCENARIOS.items():
    print(f"\n{'='*70}")
    print(f"[{pattern_id}] {scenario['name']}")
    print("-" * 70)

    # 대화 출력
    print("대화 내용:")
    for msg in scenario['conversation']:
        role = "발신자" if msg["sender_id"] == 1 else "수신자"
        print(f"  [{role}] {msg['message']}")

    # 대화 흐름 분석
    result = analyze_conversation_flow(scenario['conversation'], current_sender_id=1)

    print(f"\n분석 결과:")
    print(f"  흐름 감지: {result['flow_matched']}")
    if result['flow_matched']:
        print(f"  감지된 패턴: {result.get('matched_flow', 'N/A')} - {result.get('matched_flow_name', 'N/A')}")
        print(f"  매칭 단계: {result['matched_stages']} ({result['stages_matched_count']}/{result.get('total_stages', '?')})")
        print(f"  확률 배율: x{result['probability_multiplier']}")
    print(f"  설명: {result['flow_description']}")

    # 결과 저장
    is_safe = pattern_id.startswith("SAFE")
    expected_match = not is_safe
    actual_match = result['flow_matched']

    if expected_match == actual_match:
        status = "✅ PASS"
    else:
        status = "❌ FAIL"

    results.append({
        "pattern_id": pattern_id,
        "name": scenario['name'],
        "expected": "감지" if expected_match else "미감지",
        "actual": "감지" if actual_match else "미감지",
        "status": status,
        "multiplier": result.get('probability_multiplier', 1.0)
    })

# 결과 요약
print("\n" + "=" * 70)
print("테스트 결과 요약")
print("=" * 70)
print(f"{'패턴':<10} {'이름':<25} {'예상':<8} {'실제':<8} {'배율':<8} {'상태'}")
print("-" * 70)

passed = 0
failed = 0
for r in results:
    print(f"{r['pattern_id']:<10} {r['name']:<25} {r['expected']:<8} {r['actual']:<8} x{r['multiplier']:<6} {r['status']}")
    if "PASS" in r['status']:
        passed += 1
    else:
        failed += 1

print("-" * 70)
print(f"통과: {passed}/{len(results)}, 실패: {failed}/{len(results)}")
print("=" * 70)
