"""
Kanana Safeguard AI 모델 테스트
⚠️ 주의: 가상환경 활성화 후 실행
"""

import sys
import os

# Windows UTF-8 출력 설정
if os.name == 'nt':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

sys.path.append('agent')

from agent.tools import kanana_safeguard, analyze_incoming

def test_kanana_safeguard_direct():
    """Kanana Safeguard 모델 직접 테스트"""
    print("=" * 60)
    print("🛡️ Kanana Safeguard 모델 직접 테스트")
    print("=" * 60)

    test_cases = [
        {
            "name": "일반 메시지",
            "text": "오늘 점심 뭐 먹을래?"
        },
        {
            "name": "가족 사칭 + 송금 요구",
            "text": "엄마 나야. 폰 고장났어. 급한데 돈 좀 송금해줄 수 있어?"
        },
        {
            "name": "피싱 링크",
            "text": "택배가 도착했습니다. http://suspicious-link.com에서 확인하세요"
        },
        {
            "name": "유해 콘텐츠 (테스트)",
            "text": "폭력적이고 위험한 내용의 메시지"
        }
    ]

    for i, case in enumerate(test_cases, 1):
        print(f"\n[테스트 {i}] {case['name']}")
        print(f"메시지: {case['text']}")

        if kanana_safeguard and kanana_safeguard.model:
            result = kanana_safeguard.classify_safety(
                user_prompt=case['text'],
                assistant_prompt=""
            )

            print(f"안전 여부: {'✅ 안전' if result['is_safe'] else '⚠️ 위험'}")
            print(f"카테고리: {result['category']}")
            print(f"원시 출력: {result['raw_output']}")
        else:
            print("⚠️ Kanana Safeguard 모델이 로드되지 않았습니다 (fallback mode)")

def test_incoming_agent_with_ai():
    """안심 가드 Agent + Kanana Safeguard AI 통합 테스트"""
    print("\n\n" + "=" * 60)
    print("🤖 안심 가드 Agent + Kanana Safeguard AI 통합 테스트")
    print("=" * 60)

    test_cases = [
        {
            "name": "일반 메시지",
            "text": "오늘 저녁 같이 먹을래?"
        },
        {
            "name": "가족 사칭 + 급전 요구",
            "text": "엄마, 나 폰 고장나서 번호 바뀌었어. 급해서 그런데 돈 좀 빨리 보내줄 수 있어?"
        },
        {
            "name": "피싱 링크",
            "text": "택배가 도착했습니다. http://phishing.com에서 확인하세요"
        }
    ]

    for i, case in enumerate(test_cases, 1):
        print(f"\n[테스트 {i}] {case['name']}")
        print(f"메시지: {case['text']}")

        # AI 사용 (Kanana Safeguard)
        result_ai = analyze_incoming(case['text'], use_ai=True)
        print(f"\n📊 AI 분석 결과 (Kanana Safeguard):")
        print(f"  위험도: {result_ai.risk_level.value}")
        print(f"  이유: {', '.join(result_ai.reasons) if result_ai.reasons else '없음'}")
        print(f"  권장 조치: {result_ai.recommended_action}")

        # 룰 기반만 (비교용)
        result_rule = analyze_incoming(case['text'], use_ai=False)
        print(f"\n📋 룰 기반 결과 (비교):")
        print(f"  위험도: {result_rule.risk_level.value}")
        print(f"  이유: {', '.join(result_rule.reasons) if result_rule.reasons else '없음'}")

if __name__ == "__main__":
    print("\n🚀 Kanana Safeguard AI 보안 모델 테스트 시작\n")
    print("⚠️ 주의: 이 테스트는 가상환경 활성화 후 실행해야 합니다!")
    print("⚠️ Kanana Safeguard 8B 모델 로딩에 시간이 걸릴 수 있습니다...\n")

    # 직접 테스트
    test_kanana_safeguard_direct()

    # 통합 테스트
    test_incoming_agent_with_ai()

    print("\n\n✅ 모든 테스트 완료!")
