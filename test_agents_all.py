"""
Agent A (Outgoing) + Agent B (Incoming) 전체 테스트
"""
import sys
sys.path.insert(0, ".")

from agent.agents.outgoing import OutgoingAgent
from agent.agents.incoming import IncomingAgent
from agent.core.models import RiskLevel

print("=" * 70)
print("Agent A (Outgoing) + Agent B (Incoming) 전체 테스트")
print("=" * 70)

results = []

# ============================================================
# Agent A (Outgoing) - 민감정보 감지 테스트
# ============================================================
print("\n" + "=" * 70)
print("[Agent A] 발신 메시지 민감정보 감지 테스트")
print("=" * 70)

agent_a = OutgoingAgent()

AGENT_A_TESTS = [
    # 계좌번호
    {
        "name": "계좌번호 감지",
        "text": "내 계좌번호는 110-123-456789이야",
        "expected_risk": "CRITICAL",
        "expected_secret": True
    },
    # 주민등록번호
    {
        "name": "주민등록번호 감지",
        "text": "주민번호 900101-1234567 보내줄게",
        "expected_risk": "CRITICAL",
        "expected_secret": True
    },
    # 전화번호
    {
        "name": "전화번호 감지",
        "text": "연락처는 010-1234-5678이야",
        "expected_risk": "MEDIUM",
        "expected_secret": True
    },
    # 신용카드번호
    {
        "name": "신용카드번호 감지",
        "text": "카드번호 1234-5678-9012-3456",
        "expected_risk": "CRITICAL",
        "expected_secret": True
    },
    # 복합 민감정보
    {
        "name": "계좌+주민번호 복합 감지",
        "text": "계좌 110-123-456789, 주민번호 900101-1234567",
        "expected_risk": "CRITICAL",
        "expected_secret": True
    },
    # 비밀번호
    {
        "name": "비밀번호 감지",
        "text": "내 비밀번호는 mypassword123이야",
        "expected_risk": "CRITICAL",
        "expected_secret": True
    },
    # 여권번호
    {
        "name": "여권번호 감지",
        "text": "여권번호 M12345678 입니다",
        "expected_risk": "CRITICAL",
        "expected_secret": True
    },
    # 운전면허번호
    {
        "name": "운전면허번호 감지",
        "text": "면허번호 12-34-567890-12 입니다",
        "expected_risk": "HIGH",
        "expected_secret": True
    },
    # 안전한 메시지
    {
        "name": "안전한 메시지 (감지 없음)",
        "text": "안녕하세요 오늘 날씨 좋네요",
        "expected_risk": "LOW",
        "expected_secret": False
    },
    # 이메일 주소
    {
        "name": "이메일 주소 감지",
        "text": "내 이메일은 test@example.com 이야",
        "expected_risk": "LOW",
        "expected_secret": False
    },
]

for test in AGENT_A_TESTS:
    print(f"\n[테스트] {test['name']}")
    print(f"  입력: {test['text']}")

    result = agent_a.analyze(test['text'], use_ai=False)
    actual_risk = result.risk_level.value
    actual_secret = result.is_secret_recommended

    risk_pass = actual_risk == test['expected_risk']
    secret_pass = actual_secret == test['expected_secret']

    print(f"  예상 위험도: {test['expected_risk']}, 실제: {actual_risk} {'PASS' if risk_pass else 'FAIL'}")
    print(f"  예상 시크릿: {test['expected_secret']}, 실제: {actual_secret} {'PASS' if secret_pass else 'FAIL'}")
    print(f"  감지 이유: {result.reasons}")

    results.append({
        "agent": "A",
        "test": test['name'],
        "passed": risk_pass and secret_pass
    })

# ============================================================
# Agent B (Incoming) - 사기 패턴 감지 테스트
# ============================================================
print("\n" + "=" * 70)
print("[Agent B] 수신 메시지 사기 패턴 감지 테스트")
print("=" * 70)

agent_b = IncomingAgent()

AGENT_B_TESTS = [
    # A-1: 가족 사칭
    {
        "name": "A-1 가족 사칭 (액정 파손)",
        "text": "엄마 나야 폰 고장나서 새번호야 급해서 인증번호 좀 받아줘",
        "expected_risk": ["MEDIUM", "HIGH", "CRITICAL"],
        "should_detect": True
    },
    # A-2: 지인 사칭
    {
        "name": "A-2 지인/상사 사칭 (급전)",
        "text": "김 대리 나 팀장이야 급하게 300만원 송금해줄 수 있어?",
        "expected_risk": ["MEDIUM", "HIGH", "CRITICAL"],
        "should_detect": True
    },
    # A-3: 상품권 요구
    {
        "name": "A-3 상품권 대리 구매",
        "text": "이모야 결제가 안돼서 그래 편의점 가서 기프트카드 사서 핀번호 보내줘",
        "expected_risk": ["MEDIUM", "HIGH", "CRITICAL"],
        "should_detect": True
    },
    # B-1: 택배 스미싱
    {
        "name": "B-1 택배 스미싱",
        "text": "[CJ대한통운] 주소 불일치로 배송 보류. 주소확인: bit.ly/xxx",
        "expected_risk": ["MEDIUM", "HIGH", "CRITICAL"],
        "should_detect": True
    },
    # B-2: 기관 사칭
    {
        "name": "B-2 기관 사칭 (검찰)",
        "text": "검찰청입니다. 귀하의 계좌가 범죄에 연루되어 조사 중입니다. 안전계좌로 이체해주세요.",
        "expected_risk": ["MEDIUM", "HIGH", "CRITICAL"],
        "should_detect": True
    },
    # B-3: 결제 승인
    {
        "name": "B-3 결제 승인 피싱",
        "text": "[국외발신] 아마존 결제완료 98만원. 본인 아닐 시 즉시 문의: 02-XXX-XXXX",
        "expected_risk": ["MEDIUM", "HIGH", "CRITICAL"],
        "should_detect": True
    },
    # C-1: 투자 리딩방
    {
        "name": "C-1 투자 리딩방",
        "text": "주식리딩방 무료체험! 세력 매집주 정보 입수. 300% 수익 보장합니다!",
        "expected_risk": ["MEDIUM", "HIGH", "CRITICAL"],
        "should_detect": True
    },
    # C-2: 로맨스 스캠
    {
        "name": "C-2 로맨스 스캠",
        "text": "자기야 내가 한국으로 선물 보냈는데 세관에 걸려서 통관비 500만원이 필요해",
        "expected_risk": ["MEDIUM", "HIGH", "CRITICAL"],
        "should_detect": True
    },
    # C-3: 몸캠 피싱
    {
        "name": "C-3 몸캠 피싱",
        "text": "오빠 영상통화 하자 소리가 안들려 이 앱 깔면 화질도 좋아져 xxx.apk",
        "expected_risk": ["MEDIUM", "HIGH", "CRITICAL"],
        "should_detect": True
    },
    # 안전한 대화
    {
        "name": "안전한 일상 대화",
        "text": "오늘 저녁에 치킨 먹을래? 맛있는 집 알아",
        "expected_risk": ["LOW"],
        "should_detect": False
    },
    # 안전한 대화 2
    {
        "name": "안전한 친구 대화",
        "text": "야 주말에 영화 보러 갈래?",
        "expected_risk": ["LOW"],
        "should_detect": False
    },
]

for test in AGENT_B_TESTS:
    print(f"\n[테스트] {test['name']}")
    print(f"  입력: {test['text'][:50]}...")

    result = agent_b.analyze(test['text'], use_ai=False)
    actual_risk = result.risk_level.value

    if test['should_detect']:
        risk_pass = actual_risk in test['expected_risk']
    else:
        risk_pass = actual_risk == "LOW"

    print(f"  예상 위험도: {test['expected_risk']}, 실제: {actual_risk} {'PASS' if risk_pass else 'FAIL'}")
    print(f"  카테고리: {result.category} - {result.category_name}")
    print(f"  사기 확률: {result.scam_probability}%")
    print(f"  감지 이유: {result.reasons[:2] if result.reasons else []}")

    results.append({
        "agent": "B",
        "test": test['name'],
        "passed": risk_pass
    })

# ============================================================
# 결과 요약
# ============================================================
print("\n" + "=" * 70)
print("테스트 결과 요약")
print("=" * 70)

agent_a_results = [r for r in results if r['agent'] == 'A']
agent_b_results = [r for r in results if r['agent'] == 'B']

agent_a_passed = sum(1 for r in agent_a_results if r['passed'])
agent_b_passed = sum(1 for r in agent_b_results if r['passed'])

print(f"\n[Agent A] 발신 민감정보 감지: {agent_a_passed}/{len(agent_a_results)}")
for r in agent_a_results:
    status = "PASS" if r['passed'] else "FAIL"
    print(f"  - {r['test']}: {status}")

print(f"\n[Agent B] 수신 사기 패턴 감지: {agent_b_passed}/{len(agent_b_results)}")
for r in agent_b_results:
    status = "PASS" if r['passed'] else "FAIL"
    print(f"  - {r['test']}: {status}")

total_passed = agent_a_passed + agent_b_passed
total_tests = len(results)

print(f"\n" + "-" * 70)
print(f"전체: {total_passed}/{total_tests} ({100*total_passed/total_tests:.1f}%)")
print("=" * 70)
