# Outgoing Agent → MCP 연결 아키텍처

## 관련 파일 목록

| 순서 | 파일 | 역할 |
|------|------|------|
| 1 | `backend/api/server.py` | HTTP API 엔드포인트 |
| 2 | `agent/mcp/tools.py` | MCP 도구 정의 (`@mcp.tool`) |
| 3 | `agent/agents/outgoing.py` | OutgoingAgent 클래스 |
| 4 | `agent/prompts/outgoing_agent.py` | ReAct 프롬프트 |
| 5 | `agent/llm/kanana.py` | LLM + `analyze_with_tools()` |

---

## 호출 흐름 (순차적)

```
[1] HTTP 요청
    POST /api/agents/analyze/outgoing
    └── backend/api/server.py:84-102
        │
        ▼
[2] MCP 도구 호출
    from agent.mcp.tools import analyze_outgoing
    └── agent/mcp/tools.py:33-48
        │
        │   @mcp.tool()  ◀── FastMCP 데코레이터
        │   def analyze_outgoing(text, use_ai):
        │       agent = _get_outgoing_agent()
        │       return agent.analyze(text, use_ai)
        │
        ▼
[3] OutgoingAgent.analyze()
    └── agent/agents/outgoing.py:63-91
        │
        │   Tier 1: _has_suspicious_pattern()  ← 빠른 필터링
        │   Tier 2: use_ai=True → _analyze_with_ai()
        │           use_ai=False → _analyze_rule_based()
        │
        ▼
[4] _analyze_with_ai() - LLM + ReAct
    └── agent/agents/outgoing.py:161-200
        │
        │   llm = LLMManager.get("instruct")
        │   tools = {
        │       "detect_pii": self._tool_detect_pii,
        │       "recommend_secret_mode": self._tool_recommend_secret_mode
        │   }
        │   system_prompt = get_outgoing_system_prompt()
        │
        │   result = llm.analyze_with_tools(
        │       user_message=text,
        │       system_prompt=system_prompt,
        │       tools=tools,
        │       max_iterations=3
        │   )
        │
        ▼
[5] LLM ReAct 루프
    └── agent/llm/kanana.py:272-363
        │
        │   for iteration in range(max_iterations):
        │       response = model.generate(conversation)
        │
        │       if "Answer:" in response:
        │           return json.loads(answer)  ← 최종 응답
        │
        │       if "Action:" in response:
        │           tool_result = tools[action_name](**input)
        │           conversation += f"Observation: {tool_result}"
        │           continue  ← 다시 LLM 호출
        │
        ▼
[6] 도구 실행 (LLM이 호출)
    └── agent/agents/outgoing.py:202-239
        │
        │   _tool_detect_pii(text):
        │       for pattern in PATTERNS:
        │           matches = re.findall(regex, text)
        │       return {"found_pii": [...], "risk_level": "..."}
        │
        ▼
[7] 최종 응답
    AnalysisResponse(
        risk_level="MEDIUM",
        reasons=["계좌번호 패턴이 감지되었습니다."],
        is_secret_recommended=True
    )
```

---

## ReAct 패턴 예시 (LLM 내부 동작)

```
User: 계좌번호 110-123-456789로 보내줘

Thought: 숫자 패턴이 있음. detect_pii로 확인
Action: detect_pii
Action Input: {"text": "계좌번호 110-123-456789로 보내줘"}

[도구 실행: _tool_detect_pii() 호출]

Observation: {"found_pii": ["account:110-123-456789"], "risk_level": "MEDIUM"}

Thought: 계좌번호 확인됨. MEDIUM 위험도
Answer: {"risk_level": "MEDIUM", "is_secret_recommended": true, ...}
```

---

## 핵심 개념

1. **MCP 도구**: `@mcp.tool()` 데코레이터로 함수를 MCP 도구로 등록
2. **2-Tier 분석**: 빠른 필터링(Regex) → LLM 정밀 분석
3. **ReAct 패턴**: LLM이 Thought → Action → Observation 반복
4. **도구 호출**: LLM이 텍스트로 도구 호출 → Python 함수 실행 → 결과 반환

---

## 코드 상세

### 1. server.py (HTTP 엔드포인트)
```python
@app.post("/api/agents/analyze/outgoing")
async def api_analyze_outgoing(request: OutgoingRequest):
    result = analyze_outgoing(request.text, use_ai=request.use_ai)
    return AnalysisResponse(...)
```

### 2. mcp/tools.py (MCP 도구)
```python
@mcp.tool()
def analyze_outgoing(text: str, use_ai: bool = False) -> AnalysisResponse:
    agent = _get_outgoing_agent()
    return agent.analyze(text, use_ai=use_ai)
```

### 3. agents/outgoing.py (Agent)
```python
class OutgoingAgent:
    def analyze(self, text, use_ai=True):
        if not self._has_suspicious_pattern(text):
            return LOW  # 빠른 통과
        if use_ai:
            return self._analyze_with_ai(text)
        return self._analyze_rule_based(text)

    def _analyze_with_ai(self, text):
        llm = LLMManager.get("instruct")
        tools = {"detect_pii": self._tool_detect_pii}
        return llm.analyze_with_tools(text, prompt, tools)
```

### 4. llm/kanana.py (ReAct 실행)
```python
def analyze_with_tools(self, user_message, system_prompt, tools, max_iterations=3):
    for iteration in range(max_iterations):
        response = model.generate(conversation)

        if "Answer:" in response:
            return json.loads(answer)

        if "Action:" in response:
            tool_result = tools[action_name](**input)
            conversation += f"Observation: {tool_result}"
```
