# -*- coding: utf-8 -*-
"""
Agent B ver9.0.2 Multi-message Conversation Flow Test Script

Tests 26 scam conversation scenarios with context-based analysis.
Each case sends messages sequentially while accumulating conversation history.

Usage:
    python test_conversation_flow.py
    python test_conversation_flow.py --case A-001  # Test specific case
    python test_conversation_flow.py --verbose     # Verbose output
"""

import json
import requests
import time
import argparse
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

# Config
API_BASE_URL = "http://localhost:8002/api/agents"
TEST_DATA_PATH = Path(__file__).parent / "docs" / "dev_test_sample.json"

# Expected category mapping (case_id -> expected_category)
EXPECTED_CATEGORIES = {
    "A-001": "A-1",   # Family impersonation - money request
    "A-002": "A-1",   # Family impersonation - broken screen
    "A-003": "C-2",   # Investment scam - VIP profit
    "A-004": "C-1",   # Loan fraud
    "A-005": "B-3",   # Delivery scam
    "B-006": "A-1",   # Family impersonation - PC KakaoTalk
    "B-007": "A-1",   # Family impersonation - ID card request
    "B-008": "A-1",   # Family impersonation - gift card
    "B-009": "A-3",   # Acquaintance impersonation
    "B-010": "C-3",   # Romance scam
    "A-011": "B-1",   # Institution impersonation - security notice
    "A-012": "B-2",   # Institution impersonation - coupon
    "A-013": "B-2",   # Institution impersonation - card delivery
    "A-014": "B-1",   # Institution impersonation - KISA
    "B-015": "A-1",   # Family impersonation - SKT hack
    "B-016": "B-2",   # Institution impersonation - SIM swap
    "B-017": "A-1",   # Family impersonation - Coupang hack
    "A-018": "A-2",   # Funeral notice
    "A-019": "A-2",   # Wedding invitation
    "A-020": "B-1",   # Prosecutor impersonation
    "A-021": "C-2",   # Investment scam - review job
    "A-022": "B-2",   # Institution impersonation - health insurance
    "B-023": "C-3",   # Romance scam
    "B-024": "C-2",   # Investment scam - loss recovery
    "B-025": "B-3",   # Second-hand trade scam
    "B-026": "B-2",   # Institution impersonation - customs
}

# Category names
CATEGORY_NAMES = {
    "A-1": "Family/Friend Impersonation",
    "A-2": "Funeral/Wedding Link",
    "A-3": "Acquaintance Impersonation",
    "B-1": "Prosecutor/Police Impersonation",
    "B-2": "Institution/Card Company",
    "B-3": "Delivery/Shipping Scam",
    "C-1": "Loan Fraud",
    "C-2": "Investment/Trading Scam",
    "C-3": "Romance Scam",
    "NORMAL": "Normal Conversation",
}


class ConversationFlowTester:
    """Conversation flow tester class"""

    def __init__(self, api_url: str = API_BASE_URL, verbose: bool = False):
        self.api_url = api_url
        self.verbose = verbose
        self.results: List[Dict[str, Any]] = []

    def load_test_cases(self, test_data_path: Path) -> List[Dict]:
        """Load test cases"""
        with open(test_data_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data.get("conversations", [])

    def analyze_message(
        self,
        text: str,
        sender_id: int,
        receiver_id: int,
        conversation_history: List[Dict]
    ) -> Dict:
        """Call API to analyze message"""
        payload = {
            "text": text,
            "sender_id": str(sender_id),
            "receiver_id": str(receiver_id),
            "conversation_history": conversation_history,
            "use_ai": True
        }

        try:
            response = requests.post(
                f"{self.api_url}/analyze/incoming",
                json=payload,
                timeout=60
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": str(e), "risk_level": "ERROR"}

    def run_single_case(self, case: Dict) -> Dict:
        """Run single test case (send all messages sequentially)"""
        case_id = case["case_id"]
        sessions = case["sessions"]
        expected_category = EXPECTED_CATEGORIES.get(case_id, "UNKNOWN")

        print(f"\n{'='*60}")
        print(f"[{case_id}] Test Start - Expected: {expected_category} ({CATEGORY_NAMES.get(expected_category, '?')})")
        print(f"{'='*60}")

        # Sender/Receiver ID (other=100, me=200)
        sender_id = 100  # Other party (scammer)
        receiver_id = 200  # Me (victim)

        conversation_history = []
        final_result = None
        total_messages = 0
        max_risk_level = "LOW"  # Track highest risk level in conversation
        max_risk_category = "NORMAL"  # Category when max risk detected
        start_time = time.time()

        # Risk level priority
        risk_priority = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3, "DANGEROUS": 4}

        for session in sessions:
            session_id = session["session_id"]
            messages = session["messages"]

            for msg in messages:
                total_messages += 1

                # Add to conversation history (before API call)
                history_entry = {
                    "sender_id": sender_id,
                    "message": msg,
                    "timestamp": datetime.now().isoformat()
                }

                # API call
                result = self.analyze_message(
                    text=msg,
                    sender_id=sender_id,
                    receiver_id=receiver_id,
                    conversation_history=conversation_history.copy()
                )

                # Add to history
                conversation_history.append(history_entry)

                # Output result
                risk_level = result.get("risk_level", "?")
                category = result.get("category", "-")
                category_name = result.get("category_name", "-")

                status_icon = self._get_status_icon(risk_level)

                if self.verbose:
                    msg_display = msg[:40] if len(msg) > 40 else msg
                    print(f"  [{session_id}-{total_messages}] {status_icon} {msg_display}...")
                    print(f"       -> risk={risk_level}, category={category} ({category_name})")
                else:
                    msg_display = msg[:30] if len(msg) > 30 else msg
                    print(f"  [{session_id}] {status_icon} \"{msg_display}...\" -> {risk_level}")

                # Track max risk level during conversation
                current_priority = risk_priority.get(risk_level, 0)
                max_priority = risk_priority.get(max_risk_level, 0)
                if current_priority > max_priority:
                    max_risk_level = risk_level
                    max_risk_category = category if category else "NORMAL"

                final_result = result

        elapsed_time = time.time() - start_time

        # Final result determination - use MAX risk level from conversation, not just last message
        final_category = max_risk_category if max_risk_level in ["HIGH", "CRITICAL", "DANGEROUS"] else (final_result.get("category", "NORMAL") if final_result else "ERROR")
        final_risk = max_risk_level  # Use max risk level from entire conversation

        # Category matching check (first 3 chars like A-1, B-2)
        is_category_match = (
            final_category and
            expected_category and
            len(final_category) >= 3 and
            len(expected_category) >= 3 and
            final_category[:3] == expected_category[:3]
        )

        # Risk level check (HIGH or above = detected)
        is_detected = max_risk_level in ["HIGH", "CRITICAL", "DANGEROUS"]

        # Overall pass/fail
        is_pass = is_detected or is_category_match

        result_summary = {
            "case_id": case_id,
            "expected_category": expected_category,
            "actual_category": final_category,
            "final_risk_level": final_risk,
            "is_category_match": is_category_match,
            "is_detected": is_detected,
            "is_pass": is_pass,
            "total_messages": total_messages,
            "elapsed_time_ms": int(elapsed_time * 1000),
            "final_result": final_result
        }

        # Output result
        pass_icon = "PASS" if is_pass else "FAIL"
        print(f"\n  Result: {pass_icon}")
        print(f"  - Expected: {expected_category} | Actual: {final_category}")
        print(f"  - Risk Level: {final_risk}")
        print(f"  - Messages: {total_messages} | Time: {elapsed_time:.1f}s")

        return result_summary

    def _get_status_icon(self, risk_level: str) -> str:
        """Risk level icon"""
        icons = {
            "LOW": "[OK]",
            "MEDIUM": "[!]",
            "HIGH": "[!!]",
            "CRITICAL": "[!!!]",
            "DANGEROUS": "[!!!]",
            "ERROR": "[ERR]"
        }
        return icons.get(risk_level, "[?]")

    def run_all_cases(self, cases: List[Dict], specific_case: str = None) -> Dict:
        """Run all test cases"""
        if specific_case:
            cases = [c for c in cases if c["case_id"] == specific_case]
            if not cases:
                print(f"[ERROR] Case '{specific_case}' not found.")
                return {"error": "Case not found"}

        print(f"\n{'#'*60}")
        print(f"# Agent B ver9.0.2 Conversation Flow Test")
        print(f"# Total {len(cases)} cases")
        print(f"# API: {self.api_url}")
        print(f"{'#'*60}")

        total_start = time.time()

        for case in cases:
            result = self.run_single_case(case)
            self.results.append(result)
            time.sleep(0.5)  # Prevent API overload

        total_elapsed = time.time() - total_start

        # Final summary
        return self._print_summary(total_elapsed)

    def _print_summary(self, total_elapsed: float) -> Dict:
        """Print result summary"""
        passed = sum(1 for r in self.results if r.get("is_pass"))
        failed = len(self.results) - passed

        print(f"\n{'='*60}")
        print(f"[SUMMARY] Test Results")
        print(f"{'='*60}")
        print(f"  Total Cases: {len(self.results)}")
        print(f"  PASS: {passed}")
        print(f"  FAIL: {failed}")
        print(f"  Success Rate: {(passed/len(self.results)*100):.1f}%")
        print(f"  Total Time: {total_elapsed:.1f}s")

        if failed > 0:
            print(f"\n[FAILED] Failed Cases:")
            for r in self.results:
                if not r.get("is_pass"):
                    print(f"  - {r['case_id']}: Expected={r['expected_category']}, Actual={r['actual_category']}")

        # Category statistics
        print(f"\n[STATS] Detection by Category:")
        category_stats = {}
        for r in self.results:
            expected = r["expected_category"]
            if expected not in category_stats:
                category_stats[expected] = {"total": 0, "detected": 0}
            category_stats[expected]["total"] += 1
            if r.get("is_pass"):
                category_stats[expected]["detected"] += 1

        for cat, stats in sorted(category_stats.items()):
            cat_name = CATEGORY_NAMES.get(cat, cat)
            rate = stats["detected"] / stats["total"] * 100
            print(f"  {cat} ({cat_name}): {stats['detected']}/{stats['total']} ({rate:.0f}%)")

        return {
            "total": len(self.results),
            "passed": passed,
            "failed": failed,
            "success_rate": passed / len(self.results) * 100,
            "elapsed_seconds": total_elapsed,
            "results": self.results
        }

    def save_results(self, output_path: Path):
        """Save results to JSON file"""
        output = {
            "test_date": datetime.now().isoformat(),
            "api_url": self.api_url,
            "results": self.results
        }
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        print(f"\n[SAVE] Results saved: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Agent B Conversation Flow Test")
    parser.add_argument("--case", type=str, help="Test specific case (e.g., A-001)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--api", type=str, default=API_BASE_URL, help="API URL")
    parser.add_argument("--output", type=str, help="Result save path")
    args = parser.parse_args()

    # Initialize tester
    tester = ConversationFlowTester(api_url=args.api, verbose=args.verbose)

    # Load test cases
    if not TEST_DATA_PATH.exists():
        print(f"[ERROR] Test data file not found: {TEST_DATA_PATH}")
        return

    cases = tester.load_test_cases(TEST_DATA_PATH)
    print(f"[LOAD] {len(cases)} test cases loaded")

    # Run tests
    summary = tester.run_all_cases(cases, specific_case=args.case)

    # Save results
    if args.output:
        tester.save_results(Path(args.output))
    else:
        # Default save path
        output_path = Path(__file__).parent / "test_results" / f"flow_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        output_path.parent.mkdir(exist_ok=True)
        tester.save_results(output_path)


if __name__ == "__main__":
    main()
