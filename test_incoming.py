# -*- coding: utf-8 -*-
"""
IncomingAgent ver9.0 3-Stage Pipeline 테스트

테스트 케이스:
1. NORMAL 케이스 - "엄마 생일" vs "엄마 폰 고장" 구분
2. A-1 가족 사칭 - 금전 요구 패턴
3. B-3 택배 사칭 - 링크 포함
4. C-2 투자 리딩방 - 고수익 패턴
5. Rule-based 폴백 테스트 (use_ai=False)
"""
import sys
sys.path.insert(0, 'D:/Data/18_KAT/KAT')

from agent.mcp.tools import analyze_incoming

def test_v9_pipeline():
    """ver9.0 3-Stage Pipeline 테스트"""
    print("=" * 60)
    print("IncomingAgent ver9.0 3-Stage Pipeline 테스트")
    print("=" * 60)

    # 테스트 케이스 (ver9.0 핵심 - 맥락 구분)
    test_cases = [
        # NORMAL 케이스 (맥락 구분 테스트)
        ("NORMAL-1", "엄마 생일 선물 뭐가 좋을까?", "NORMAL"),
        ("NORMAL-2", "오늘 저녁 뭐 먹을까?", "NORMAL"),
        ("NORMAL-3", "회의 시간 3시로 변경됐어", "NORMAL"),

        # A-1 가족 사칭 (금전 요구)
        ("A-1", "엄마, 나 폰 액정 깨져서 수리 맡겼어. 급하게 인증번호 좀 받아줘.", "A-1"),
        ("A-1-2", "아빠야 폰 고장나서 급하게 30만원만 보내줘 계좌번호 110-123-456789", "A-1"),

        # B-3 택배 사칭
        ("B-3", "[CJ대한통운] 주소 불일치로 배송 보류. 주소 수정: bit.ly/xxx", "B-3"),

        # C-1 대출 빙자
        ("C-1", "정부지원 저금리 대출 승인되었습니다. 한도 3천만원", "C-1"),

        # C-2 투자 리딩방
        ("C-2", "이번에 세력 매집주 정보 입수했습니다. 300% 수익 보장. 체험방 들어오세요.", "C-2"),
    ]

    print("\n[1] Rule-based 폴백 테스트 (use_ai=False)")
    print("-" * 60)
    for name, text, expected in test_cases:
        result = analyze_incoming(text, use_ai=False)
        status = "OK" if (expected == "NORMAL" and result.risk_level.value == "LOW") or \
                         (expected != "NORMAL" and result.risk_level.value != "LOW") else "FAIL"
        print(f"  [{status}] {name}: risk={result.risk_level.value}, category={result.category}, prob={result.scam_probability}%")
        if result.reasons:
            print(f"      → {result.reasons[0][:50]}...")

    print("\n[2] AI Agent 테스트 (use_ai=True)")
    print("-" * 60)
    for name, text, expected in test_cases[:5]:  # 일부만 테스트 (AI 호출 시간 고려)
        result = analyze_incoming(text, use_ai=True)
        status = "OK" if (expected == "NORMAL" and result.risk_level.value == "LOW") or \
                         (expected != "NORMAL" and result.risk_level.value != "LOW") else "FAIL"
        print(f"  [{status}] {name}: risk={result.risk_level.value}, category={result.category}, prob={result.scam_probability}%")
        if result.reasons:
            print(f"      → {result.reasons[0][:50]}...")

    print("\n" + "=" * 60)
    print("테스트 완료!")
    print("=" * 60)


if __name__ == "__main__":
    test_v9_pipeline()
