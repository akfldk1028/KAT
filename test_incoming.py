# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, 'D:/Data/18_KAT/KAT')

from agent.mcp.tools import analyze_incoming

# 테스트 케이스
test_cases = [
    ("C-1", "이번에 세력 매집주 정보 입수했습니다. 300% 수익 보장. 체험방 들어오세요."),
    ("A-1", "엄마, 나 폰 액정 깨져서 수리 맡겼어. 급하게 인증번호 좀 받아줘."),
    ("SAFE", "오늘 저녁 뭐 먹을까?"),
]

for name, text in test_cases:
    result = analyze_incoming(text, use_ai=False)
    print(f"[{name}] risk_level={result.risk_level.value}, scam_prob={result.scam_probability}")
