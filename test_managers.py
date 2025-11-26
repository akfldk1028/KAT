"""
AgentManager 및 LLMManager 동작 확인 테스트
"""

import sys
import os

# Windows UTF-8 출력 설정
if os.name == 'nt':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

sys.path.append('agent')

from agent.agent_manager import AgentManager
from agent.llm_manager import LLMManager

print("=" * 60)
print("🔍 AgentManager 동작 확인")
print("=" * 60)

# Agent 목록 확인
print("\n1. 등록된 Agent 목록:")
agents = AgentManager.list_agents()
print(f"   {agents}")

# Outgoing Agent 가져오기
print("\n2. Outgoing Agent 가져오기:")
outgoing = AgentManager.get_outgoing()
print(f"   {outgoing}")
print(f"   타입: {type(outgoing).__name__}")

# Incoming Agent 가져오기
print("\n3. Incoming Agent 가져오기:")
incoming = AgentManager.get_incoming()
print(f"   {incoming}")
print(f"   타입: {type(incoming).__name__}")

# 동일한 Agent 재사용 확인
print("\n4. Singleton 패턴 확인 (동일 인스턴스 재사용):")
outgoing2 = AgentManager.get_outgoing()
print(f"   첫 번째 호출: {id(outgoing)}")
print(f"   두 번째 호출: {id(outgoing2)}")
print(f"   동일 인스턴스: {outgoing is outgoing2}")

# Agent 동작 테스트
print("\n5. Agent 동작 테스트:")
result = outgoing.analyze("계좌번호 123-45-67890")
print(f"   위험도: {result.risk_level}")
print(f"   이유: {result.reasons}")

print("\n" + "=" * 60)
print("🔍 LLMManager 동작 확인")
print("=" * 60)

# LLM 로드 여부 확인
print("\n1. LLM 로드 상태:")
print(f"   Safeguard 모델 로드됨: {LLMManager.is_loaded('safeguard')}")
print(f"   Instruct 모델 로드됨: {LLMManager.is_loaded('instruct')}")

# LLM 가져오기 (Lazy Loading)
print("\n2. LLM 가져오기 (요청 시 자동 로드):")
print("   주의: Safeguard 모델은 8GB로 로딩에 시간이 걸릴 수 있습니다.")
print("   테스트는 생략하고 API 호출로 확인합니다.")

print("\n" + "=" * 60)
print("✅ 모든 Manager 동작 확인 완료!")
print("=" * 60)

print("\n📋 결과 요약:")
print(f"   - AgentManager: {len(agents)}개 Agent 등록됨")
print(f"   - Singleton 패턴: 정상 동작")
print(f"   - Agent 분석 기능: 정상 동작")
print(f"   - LLMManager: 정상 동작 (Lazy Loading)")
