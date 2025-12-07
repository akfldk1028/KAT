"""
Agent B AI (LLM) 연동 테스트
use_ai=True로 Hybrid Analyzer가 동작하는지 확인
"""
import sys
sys.path.insert(0, ".")

from agent.agents.incoming import IncomingAgent

print("=" * 70)
print("Agent B AI (LLM) 연동 테스트")
print("=" * 70)

agent = IncomingAgent()

# 테스트 케이스
TEST_CASES = [
    {
        "name": "가족 사칭",
        "text": "엄마 나야 폰 고장나서 새번호야 급해서 인증번호 좀 받아줘",
    },
    {
        "name": "안전한 메시지",
        "text": "오늘 저녁에 치킨 먹을래?",
    },
    {
        "name": "기관 사칭 (검찰)",
        "text": "검찰청입니다. 귀하의 계좌가 범죄에 연루되어 조사 중입니다.",
    },
]

for test in TEST_CASES:
    print(f"\n{'='*70}")
    print(f"[테스트] {test['name']}")
    print(f"입력: {test['text']}")
    print("-" * 70)

    # use_ai=True로 분석
    result = agent.analyze(test['text'], use_ai=True)

    print(f"\n결과:")
    print(f"  위험 레벨: {result.risk_level.value}")
    print(f"  카테고리: {result.category} - {result.category_name}")
    print(f"  사기 확률: {result.scam_probability}%")
    print(f"  이유: {result.reasons}")
    print(f"  권장 조치: {result.recommended_action}")

print("\n" + "=" * 70)
print("테스트 완료")
print("=" * 70)
