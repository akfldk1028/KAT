"""
서브에이전트 테스트 스크립트
가상환경 활성화 후 실행: python test_agents.py
"""

import sys
import os

# Windows UTF-8 출력 설정
if os.name == 'nt':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# sys.path.append('agent')

from agent import OutgoingAgent, IncomingAgent

def test_outgoing_agent():
    """안심 전송 Agent 테스트"""
    print("=" * 60)
    print("🔒 안심 전송 Agent (Outgoing) 테스트")
    print("=" * 60)

    agent = OutgoingAgent()

    # 테스트 케이스 1: 계좌번호 포함
    test1 = "이 계좌로 30만원 보내줘 123-45-67890"
    result1 = agent.analyze(test1)
    print(f"\n[테스트 1] 메시지: {test1}")
    print(f"위험도: {result1.risk_level.value}")
    print(f"이유: {', '.join(result1.reasons)}")
    print(f"권장 조치: {result1.recommended_action}")
    print(f"시크릿 전송 추천: {result1.is_secret_recommended}")

    # 테스트 케이스 2: 주민번호 포함
    test2 = "주민번호 900101-1234567 이거야"
    result2 = agent.analyze(test2)
    print(f"\n[테스트 2] 메시지: {test2}")
    print(f"위험도: {result2.risk_level.value}")
    print(f"이유: {', '.join(result2.reasons)}")
    print(f"권장 조치: {result2.recommended_action}")
    print(f"시크릿 전송 추천: {result2.is_secret_recommended}")

    # 테스트 케이스 3: 일반 메시지
    test3 = "오늘 저녁 같이 먹을래?"
    result3 = agent.analyze(test3)
    print(f"\n[테스트 3] 메시지: {test3}")
    print(f"위험도: {result3.risk_level.value}")
    print(f"이유: {', '.join(result3.reasons) if result3.reasons else '없음'}")
    print(f"권장 조치: {result3.recommended_action}")
    print(f"시크릿 전송 추천: {result3.is_secret_recommended}")

def test_incoming_agent():
    """안심 가드 Agent 테스트"""
    print("\n\n" + "=" * 60)
    print("🛡️ 안심 가드 Agent (Incoming) 테스트")
    print("=" * 60)

    agent = IncomingAgent()

    # 테스트 케이스 1: 가족 사칭 + 급전 요구
    test1 = "엄마, 나 폰 고장나서 번호 바뀌었어. 급해서 그런데 돈 좀 빨리 보내줄 수 있어?"
    result1 = agent.analyze(test1)
    print(f"\n[테스트 1] 메시지: {test1}")
    print(f"위험도: {result1.risk_level.value}")
    print(f"이유: {', '.join(result1.reasons)}")
    print(f"권장 조치: {result1.recommended_action}")

    # 테스트 케이스 2: 피싱 링크
    test2 = "택배가 도착했습니다. http://suspicious-link.com에서 확인하세요"
    result2 = agent.analyze(test2)
    print(f"\n[테스트 2] 메시지: {test2}")
    print(f"위험도: {result2.risk_level.value}")
    print(f"이유: {', '.join(result2.reasons)}")
    print(f"권장 조치: {result2.recommended_action}")

    # 테스트 케이스 3: 일반 메시지
    test3 = "오늘 점심 뭐 먹을래?"
    result3 = agent.analyze(test3)
    print(f"\n[테스트 3] 메시지: {test3}")
    print(f"위험도: {result3.risk_level.value}")
    print(f"이유: {', '.join(result3.reasons) if result3.reasons else '없음'}")
    print(f"권장 조치: {result3.recommended_action}")

    # 테스트 케이스 4: 송금 유도
    test4 = "급해서 그런데 송금 좀 부탁해"
    result4 = agent.analyze(test4)
    print(f"\n[테스트 4] 메시지: {test4}")
    print(f"위험도: {result4.risk_level.value}")
    print(f"이유: {', '.join(result4.reasons)}")
    print(f"권장 조치: {result4.recommended_action}")

if __name__ == "__main__":
    print("\n🚀 Kanana DualGuard - 서브에이전트 테스트 시작\n")
    print("⚠️ 주의: 이 테스트는 가상환경 활성화 후 실행해야 합니다!\n")

    test_outgoing_agent()
    test_incoming_agent()

    print("\n\n✅ 모든 테스트 완료!")
