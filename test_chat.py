"""
간단한 채팅 테스트 도구
MCP 도구를 직접 호출해서 테스트
"""
from agent.mcp import scan_pii, analyze_full, identify_document

def main():
    print("=" * 50)
    print("  KAT 보안 MCP 테스트")
    print("  - 메시지를 입력하면 민감정보를 분석합니다")
    print("  - 'quit' 입력시 종료")
    print("=" * 50)

    while True:
        print()
        text = input("메시지 입력 > ").strip()

        if text.lower() == 'quit':
            print("종료합니다.")
            break

        if not text:
            continue

        # 분석 실행
        result = analyze_full(text)

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
