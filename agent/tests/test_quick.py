# Quick test for threat detection
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Reset cache
from agent.core import threat_matcher
threat_matcher._threat_cache = None

from agent.core.threat_matcher import analyze_incoming_message

# Test 1
msg1 = "eommaya poni gojangnaeseo sae beonhoya. geupande 30manwonman bonaejwo"
msg1_ko = "엄마야 폰이 고장나서 새 번호야. 급한데 30만원만 보내줘"
result1 = analyze_incoming_message(msg1_ko)
print("Test 1: Family Impersonate")
print(f"  Level: {result1['final_assessment']['threat_level']} (expected: CRITICAL)")
print(f"  Threats: {[t['name_ko'] for t in result1['threat_detection']['found_threats']]}")
print()

# Test 2
msg2 = "https://kakao-security.net/update"
result2 = analyze_incoming_message(msg2)
print("Test 2: Suspicious Domain")
print(f"  Level: {result2['final_assessment']['threat_level']} (expected: DANGEROUS)")
print(f"  Threats: {[t['name_ko'] for t in result2['threat_detection']['found_threats']]}")
