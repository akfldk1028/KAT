"""
Agent B ver9.0 3-Stage Pipeline Test
Test each stage and full pipeline with various smishing categories

9 MECE Categories:
A-1: Family/acquaintance impersonation
A-2: Condolence/celebration fraud
A-3: Romance scam
B-1: Investigation/financial institution impersonation
B-2: Public admin notification fraud
B-3: Delivery/logistics fraud
C-1: Loan fraud
C-2: Investment leading room
C-3: Body cam phishing
NORMAL: Normal conversation
"""
import os
import sys
import io
import json
import time
from pathlib import Path

# Fix encoding for Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Project root
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Load .env
from dotenv import load_dotenv
load_dotenv(project_root / "backend" / ".env")

print("=" * 70)
print("Agent B ver9.0 3-Stage Pipeline Test")
print("=" * 70)

# Test cases - 9 MECE categories + NORMAL
# Expected values use IncomingAgent's RiskLevel enum:
#   LOW (SAFE), MEDIUM (SUSPICIOUS), HIGH (DANGEROUS), CRITICAL
TEST_CASES = [
    # A-1: Family/acquaintance impersonation
    {
        "category": "A-1",
        "name": "Family Impersonation",
        "text": "[Web] Mom, my phone broke. Please send 500,000 won to account 110-123-456789. Urgent!",
        "text_ko": "[Web발신] 엄마 나 폰이 고장났어. 계좌번호 110-123-456789로 50만원만 보내줘. 급해!",
        "expected": "HIGH"  # DANGEROUS → HIGH
    },
    # A-2: Condolence/celebration fraud
    {
        "category": "A-2",
        "name": "Funeral Notice Fraud",
        "text": "[Web] Father passed away. Please come to funeral hall at http://funeral-notice.com/view",
        "text_ko": "[Web발신] 부고알림. 아버지께서 별세하셨습니다. http://funeral-notice.com/view",
        "expected": "HIGH"  # DANGEROUS → HIGH
    },
    # B-1: Investigation/financial institution impersonation
    {
        "category": "B-1",
        "name": "Prosecution Impersonation",
        "text": "This is Seoul Central Prosecutor's Office. Your account is suspected of fraud. Call 02-123-4567 now.",
        "text_ko": "서울중앙지검입니다. 귀하의 계좌가 범죄에 연루되어 조사 중입니다. 지금 바로 02-123-4567로 전화주세요.",
        "expected": "HIGH"  # 검찰사칭도 HIGH (CRITICAL은 DB HIT 시만)
    },
    # B-2: Public admin notification fraud
    {
        "category": "B-2",
        "name": "Traffic Fine Notification",
        "text": "[Traffic Police] You have unpaid fines. Install app to pay: http://fine-pay.kr/app",
        "text_ko": "[교통경찰청] 과태료 미납 고지. 앱 설치 후 납부: http://fine-pay.kr/app",
        "expected": "HIGH"  # 공공기관 사칭도 HIGH
    },
    # B-3: Delivery/logistics fraud
    {
        "category": "B-3",
        "name": "Delivery Fraud",
        "text": "[CJ Logistics] Delivery failed due to address issue. Check: http://cj-delivery.info/track",
        "text_ko": "[CJ대한통운] 주소 불명으로 배송 실패. 확인: http://cj-delivery.info/track",
        "expected": "HIGH"  # 택배 사칭도 HIGH (DANGEROUS)
    },
    # C-1: Loan fraud
    {
        "category": "C-1",
        "name": "Loan Fraud",
        "text": "Special low-interest loan up to 50M won, no credit check required. Apply: 010-1234-5678",
        "text_ko": "서민금융 저금리 대출 5천만원까지, 신용조회 없음. 신청: 010-1234-5678",
        "expected": "HIGH"  # DANGEROUS → HIGH
    },
    # C-2: Investment leading room
    {
        "category": "C-2",
        "name": "Investment Scam",
        "text": "VIP stock recommendation room, guaranteed 300% profit! Join: http://vip-stock.kr",
        "text_ko": "VIP 주식리딩방, 수익률 300% 보장! 가입: http://vip-stock.kr",
        "expected": "HIGH"  # DANGEROUS → HIGH
    },
    # NORMAL case
    {
        "category": "NORMAL",
        "name": "Normal Conversation",
        "text": "Mom, happy birthday! I'll visit this weekend with a gift.",
        "text_ko": "엄마 생일 축하해요! 이번 주말에 선물 들고 갈게요.",
        "expected": "LOW"  # SAFE → LOW
    },
    # NORMAL case 2 - Daily life
    {
        "category": "NORMAL",
        "name": "Daily Chat",
        "text": "Let's have dinner together today. Should we go to the Italian restaurant near the office?",
        "text_ko": "오늘 저녁 같이 먹자. 회사 앞 이탈리안 레스토랑 갈까?",
        "expected": "LOW"  # SAFE → LOW
    }
]

def run_pipeline_test():
    """Run Agent B 3-Stage Pipeline tests"""

    # Import Agent
    try:
        from agent.agents.incoming import IncomingAgent
        agent = IncomingAgent()
        print("[OK] IncomingAgent loaded successfully")
    except Exception as e:
        print(f"[ERR] Failed to load IncomingAgent: {e}")
        return

    print("\n" + "-" * 70)
    print("Running 3-Stage Pipeline Tests")
    print("-" * 70)

    results = []

    for i, test in enumerate(TEST_CASES, 1):
        print(f"\n[Test {i}/{len(TEST_CASES)}] {test['category']} - {test['name']}")
        print(f"  Input: {test['text_ko'][:60]}...")
        print(f"  Expected: {test['expected']}")

        try:
            start = time.time()
            result = agent.analyze(
                text=test['text_ko'],
                use_ai=True  # ver9.0 3-Stage Pipeline
            )
            elapsed = time.time() - start

            # Extract key info
            risk_level = result.risk_level.value if hasattr(result.risk_level, 'value') else str(result.risk_level)

            # Check if result matches expected
            # RiskLevel enum: LOW, MEDIUM, HIGH, CRITICAL
            is_pass = (
                (test['expected'] == "LOW" and risk_level in ["LOW", "low", "SAFE", "safe"]) or
                (test['expected'] == "MEDIUM" and risk_level in ["MEDIUM", "medium", "SUSPICIOUS", "suspicious"]) or
                (test['expected'] == "HIGH" and risk_level in ["HIGH", "high", "DANGEROUS", "dangerous"]) or
                (test['expected'] == "CRITICAL" and risk_level in ["CRITICAL", "critical"])
            )

            status = "[PASS]" if is_pass else "[FAIL]"

            print(f"  Result: {risk_level}")
            print(f"  Time: {elapsed*1000:.1f}ms")
            print(f"  Status: {status}")

            # Print stage info if available
            if hasattr(result, 'analysis_stages') and result.analysis_stages:
                stages = result.analysis_stages
                if isinstance(stages, dict):
                    for stage_name, stage_data in stages.items():
                        if stage_data and isinstance(stage_data, dict):
                            print(f"    {stage_name}: {stage_data.get('decision', stage_data.get('category', 'N/A'))}")

            results.append({
                "category": test['category'],
                "name": test['name'],
                "expected": test['expected'],
                "actual": risk_level,
                "passed": is_pass,
                "time_ms": elapsed * 1000
            })

        except Exception as e:
            print(f"  [ERR] Test failed: {e}")
            import traceback
            traceback.print_exc()
            results.append({
                "category": test['category'],
                "name": test['name'],
                "expected": test['expected'],
                "actual": "ERROR",
                "passed": False,
                "error": str(e)
            })

    # Print summary
    print("\n" + "=" * 70)
    print("Test Summary")
    print("=" * 70)

    passed = sum(1 for r in results if r['passed'])
    failed = len(results) - passed

    print(f"\nTotal: {len(results)}, Passed: {passed}, Failed: {failed}")
    print(f"Pass Rate: {passed/len(results)*100:.1f}%")

    # Average time
    times = [r['time_ms'] for r in results if 'time_ms' in r]
    if times:
        print(f"Average Time: {sum(times)/len(times):.1f}ms")

    # Failed cases
    if failed > 0:
        print("\nFailed Cases:")
        for r in results:
            if not r['passed']:
                print(f"  - {r['category']} ({r['name']}): expected={r['expected']}, actual={r['actual']}")

    return results


def test_stage1_only():
    """Test Stage 1 DB blacklist check only"""
    print("\n" + "=" * 70)
    print("Stage 1 DB Blacklist Test")
    print("=" * 70)

    from agent.agents.incoming import IncomingAgent
    agent = IncomingAgent()

    # Test with known mock blacklisted number
    test_text = "Please send money to 010-1234-5678"
    test_text_ko = "010-1234-5678로 돈 보내줘"

    print(f"\nTest input: {test_text_ko}")
    print("Testing Stage 1 (DB blacklist) only...")

    try:
        result = agent._stage1_db_blacklist(test_text_ko)
        print(f"\nStage 1 Result:")
        print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    except Exception as e:
        print(f"[ERR] Stage 1 test failed: {e}")


def test_scam_checker():
    """Test scam_checker module directly"""
    print("\n" + "=" * 70)
    print("scam_checker Module Direct Test")
    print("=" * 70)

    from agent.core.scam_checker import check_scam_in_message

    test_messages = [
        "010-1234-5678로 연락주세요",
        "110-123-456789 계좌로 입금해주세요",
        "http://phishing-site.com/login 에서 확인하세요"
    ]

    for msg in test_messages:
        print(f"\nInput: {msg}")
        result = check_scam_in_message(msg)
        print(f"Result: has_reported={result.get('has_reported_identifier')}, max_risk={result.get('max_risk_score')}")


if __name__ == "__main__":
    # Run all tests
    print("\n[1] scam_checker Direct Test")
    test_scam_checker()

    print("\n[2] Stage 1 Only Test")
    test_stage1_only()

    print("\n[3] Full 3-Stage Pipeline Test")
    results = run_pipeline_test()
