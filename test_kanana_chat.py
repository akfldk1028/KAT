"""
Kanana LLM + MCP 도구 채팅 테스트
LLM이 직접 MCP 도구(scan_pii, analyze_full 등)를 호출해서 분석
"""
from agent.llm.kanana import LLMManager
from agent.core.pattern_matcher import detect_pii, calculate_risk, get_risk_action
from agent.prompts.outgoing_agent import get_outgoing_system_prompt


def analyze_full(text: str) -> dict:
    """analyze_full MCP 도구"""
    pii_result = detect_pii(text)
    risk_result = calculate_risk(pii_result["found_pii"])
    action = get_risk_action(risk_result["final_risk"])

    if pii_result["count"] == 0:
        summary = "민감정보가 감지되지 않았습니다."
    else:
        detected_names = list(set(item["name_ko"] for item in pii_result["found_pii"]))
        summary = f"{len(detected_names)}종의 민감정보 감지: {', '.join(detected_names)}. {action}"

    return {
        "pii_scan": pii_result,
        "risk_evaluation": risk_result,
        "recommended_action": action,
        "summary": summary
    }


def main():
    print("=" * 60)
    print("  Kanana LLM + MCP 보안 도구 테스트")
    print("  - Kanana가 MCP 도구를 호출해서 민감정보를 분석합니다")
    print("  - 'quit' 입력시 종료")
    print("  - 'rule' 입력시 Rule-based만 사용 (LLM 없이)")
    print("=" * 60)

    # LLM 로드
    print("\n[Kanana LLM 로딩 중...]")
    llm = LLMManager.get("instruct")

    if llm is None:
        print("[경고] LLM 로드 실패! Rule-based 모드로 동작합니다.")
        use_llm = False
    else:
        print("[OK] Kanana LLM 로드 완료!")
        use_llm = True

    # MCP 도구 정의
    tools = {
        "scan_pii": detect_pii,
        "evaluate_risk": calculate_risk,
        "analyze_full": analyze_full,
    }

    # 시스템 프롬프트
    system_prompt = get_outgoing_system_prompt()

    while True:
        print()
        text = input("메시지 입력 > ").strip()

        if text.lower() == 'quit':
            print("종료합니다.")
            break

        if not text:
            continue

        # Rule-based 모드
        if text.lower() == 'rule' or not use_llm:
            print("\n[Rule-based 모드]")
            result = analyze_full(text if text.lower() != 'rule' else input("분석할 메시지 > "))
            print_result(result)
            continue

        # LLM + MCP 도구 모드
        print("\n[Kanana LLM 분석 중...]")
        try:
            result = llm.analyze_with_tools(
                user_message=text,
                system_prompt=system_prompt,
                tools=tools,
                max_iterations=3
            )

            print("\n[LLM 분석 결과]")
            print(f"  위험도: {result.get('risk_level', 'N/A')}")
            print(f"  감지된 PII: {result.get('detected_pii', [])}")
            print(f"  이유: {result.get('reasons', [])}")
            print(f"  시크릿 전송: {'권장' if result.get('is_secret_recommended') else '불필요'}")
            print(f"  권장 조치: {result.get('recommended_action', 'N/A')}")

        except Exception as e:
            print(f"[오류] {e}")
            print("[Rule-based로 대체 분석]")
            result = analyze_full(text)
            print_result(result)


def print_result(result: dict):
    """분석 결과 출력"""
    print()
    print(f"[분석 결과]")
    print(f"  위험도: {result['risk_evaluation']['final_risk']}")
    print(f"  감지된 PII: {result['pii_scan']['count']}개")

    if result['pii_scan']['found_pii']:
        for item in result['pii_scan']['found_pii']:
            print(f"    - {item['name_ko']}: {item['value']}")

    if result['risk_evaluation']['escalation_reason']:
        print(f"  상향 이유: {result['risk_evaluation']['escalation_reason']}")

    print(f"  권장 조치: {result['recommended_action']}")
    print(f"  시크릿 전송: {'권장' if result['risk_evaluation']['is_secret_recommended'] else '불필요'}")


if __name__ == "__main__":
    main()
