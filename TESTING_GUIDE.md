# Kanana DualGuard 테스트 가이드

## 서버 구성

| 포트 | 서비스 | 설명 |
|------|--------|------|
| **3000** | 프론트엔드 | KakaoTalk React 클라이언트 |
| **8001** | 백엔드 API | FastAPI 메인 서버 |
| **8002** | Agent API | MCP + 위협 분석 서버 |

---

## 1. 서버 시작

### 1.1 전체 서버 시작 (3개)

```bash
# 터미널 1: 프론트엔드 (3000)
cd D:\Data\18_KAT\KAT\frontend\KakaoTalk\client
npm start

# 터미널 2: 백엔드 API (8001)
cd D:\Data\18_KAT\KAT\backend
D:\Data\18_KAT\KAT\backend\venv_gpu\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload

# 터미널 3: Agent API (8002)
cd D:\Data\18_KAT\KAT\backend
D:\Data\18_KAT\KAT\backend\venv_gpu\Scripts\python.exe -m uvicorn api.server:app --host 0.0.0.0 --port 8002 --reload
```

### 1.2 포트 확인

```powershell
Get-NetTCPConnection -LocalPort 3000,8001,8002 | Select-Object LocalPort, State
```

---

## 2. Agent A 테스트 (안심 전송 - 발신 보호)

**기능**: 발신 메시지에서 민감정보(PII) 감지

### 2.1 API 테스트 (curl/PowerShell)

```powershell
# 계좌번호 감지 테스트
Invoke-RestMethod -Uri "http://localhost:8002/api/agents/analyze/outgoing" -Method POST -ContentType "application/json" -Body '{"text": "이 계좌로 보내줘 123-456-78901234"}'
```

**예상 결과:**
```json
{
  "risk_level": "MEDIUM",
  "reasons": ["계좌번호 패턴이 감지되었습니다."],
  "recommended_action": "시크릿 전송 추천",
  "is_secret_recommended": true
}
```

### 2.2 Python 직접 테스트

```python
# D:\Data\18_KAT\KAT\backend\venv_gpu\Scripts\python.exe
import sys
sys.path.insert(0, "D:/Data/18_KAT/KAT")

from agent.mcp.tools import scan_pii, analyze_full

# 테스트 1: PII 스캔
result = scan_pii("내 계좌번호는 123-456-78901234이고 주민번호는 901234-1234567이야")
print(f"감지된 PII: {result['found_pii']}")
print(f"위험도: {result['highest_risk']}")

# 테스트 2: 전체 분석
result = analyze_full("계좌번호 110-123-456789로 50만원 보내줘")
print(f"요약: {result['summary.md']}")
```

### 2.3 테스트 케이스

| 입력 | 예상 위험도 | 감지 항목 |
|------|------------|----------|
| `계좌번호 123-456-78901234` | MEDIUM | 계좌번호 |
| `주민번호 901234-1234567` | HIGH | 주민등록번호 |
| `카드번호 1234-5678-9012-3456` | HIGH | 신용카드번호 |
| `비밀번호 1234` | MEDIUM | 비밀번호 |
| `오늘 날씨 좋네` | LOW | 없음 |

---

## 3. Agent B 테스트 (안심 가드 - 수신 보호)

**기능**: 수신 메시지에서 피싱/사기 위협 감지 (MECE 카테고리 기반)

### 3.1 MECE 카테고리 구조

```
A: 관계 사칭형 (Targeting Trust)
├── A-1: 가족 사칭 (액정 파손)
├── A-2: 지인/상사 사칭 (급전)
└── A-3: 상품권 대리 구매

B: 공포/권위 악용형 (Targeting Fear & Authority)
├── B-1: 생활 밀착형 (택배/경조사)
├── B-2: 기관 사칭 (건강/법무)
└── B-3: 결제 승인 (낚시성)

C: 욕망/감정 자극형 (Targeting Desire & Emotion)
├── C-1: 투자 권유 (리딩방)
├── C-2: 로맨스 스캠
└── C-3: 몸캠 피싱
```

### 3.2 API 테스트 (curl/PowerShell)

```powershell
# 가족 사칭 테스트 (A-1)
Invoke-RestMethod -Uri "http://localhost:8002/api/agents/analyze/incoming" -Method POST -ContentType "application/json" -Body '{"text": "엄마, 나 폰 액정 깨져서 수리 맡겼어. 급하게 인증번호 좀 받아줘."}'
```

**예상 결과:**
```json
{
  "risk_level": "CRITICAL",
  "reasons": ["[A-1] 가족 사칭 (액정 파손) 패턴 감지"],
  "recommended_action": "차단 및 경고",
  "is_secret_recommended": false
}
```

### 3.3 Python 직접 테스트

```python
# D:\Data\18_KAT\KAT\backend\venv_gpu\Scripts\python.exe
import sys
sys.path.insert(0, "D:/Data/18_KAT/KAT")
sys.stdout.reconfigure(encoding='utf-8')

from agent.core.threat_matcher import analyze_incoming_message, reload_threat_data

reload_threat_data()

# 테스트 메시지들
test_cases = [
    ("A-1", "엄마, 나 폰 액정 깨져서 수리 맡겼어. 급하게 인증번호 좀 받아줘."),
    ("A-2", "김 대리, 나 지금 미팅 중이라 폰뱅킹이 안 되는데 급하게 300만원만 먼저 보내줄 수 있나?"),
    ("A-3", "편의점 가서 구글 기프트카드 10만원짜리 5개만 사서 핀번호 사진 찍어 보내줘"),
    ("B-1", "[CJ대한통운] 배송 보류. 주소 수정: bit.ly/xxx"),
    ("B-2", "[국민건강보험] 건강검진 결과 통보서. 확인: han.gl/xxx"),
    ("B-3", "[국외발신] 아마존 해외결제 980,000원. 본인 아닐 시 문의: 02-1234-5678"),
    ("C-1", "이번에 세력 매집주 정보 입수했습니다. 300% 수익 보장. 체험방 들어오세요."),
    ("C-2", "자기야, 세관에 걸려서 통관비 500만원이 필요해."),
    ("SAFE", "오늘 저녁 뭐 먹을까?"),
]

print("=" * 70)
print("Agent B (수신 보호) MECE 카테고리 테스트")
print("=" * 70)

for expected, text in test_cases:
    result = analyze_incoming_message(text)
    category = result['summary.md']['category'] or 'SAFE'
    prob = result['summary.md']['probability']
    pattern = result['summary.md']['pattern']

    match = "O" if category == expected or (category is None and expected == "SAFE") else "X"
    print(f"\n[{match}] 예상: {expected:5} | 감지: {str(category):5} | 확률: {prob}")
    print(f"    패턴: {pattern}")
    print(f"    입력: {text[:50]}...")
```

### 3.4 MCP 도구 테스트

```python
from agent.mcp.tools import analyze_threat_full

# MCP 도구로 전체 분석
result = analyze_threat_full("엄마 나야 폰 고장났어 인증번호 좀 받아줘")

print(f"카테고리: {result['summary.md']['category']}")
print(f"패턴: {result['summary.md']['pattern']}")
print(f"확률: {result['summary.md']['probability']}")
print(f"MCP 요약: {result['mcp_summary']}")
```

### 3.5 전체 테스트 케이스

| 카테고리 | 입력 예시 | 예상 확률 |
|----------|----------|----------|
| **A-1** | 엄마, 폰 액정 깨져서 인증번호 좀 받아줘 | 90%+ |
| **A-2** | 김 대리, 급하게 300만원만 보내줘 | 90%+ |
| **A-3** | 편의점에서 기프트카드 사서 핀번호 보내줘 | 90%+ |
| **B-1** | [택배] 배송 보류. 주소 수정: bit.ly/xxx | 85%+ |
| **B-2** | [건강보험] 검진결과 확인: han.gl/xxx | 85%+ |
| **B-3** | [국외발신] 해외결제 98만원. 문의: 02-xxx | 85%+ |
| **C-1** | 세력 매집주 정보! 300% 수익 보장 | 75%+ |
| **C-2** | 자기야, 통관비 500만원 필요해 | 75%+ |
| **SAFE** | 오늘 날씨 좋네 | 0% |

---

## 4. 통합 테스트

### 4.1 API 헬스체크

```powershell
# 8001 백엔드
Invoke-RestMethod -Uri "http://localhost:8001/"

# 8002 Agent API
Invoke-RestMethod -Uri "http://localhost:8002/api/agents/health"

# MCP 정보
Invoke-RestMethod -Uri "http://localhost:8002/api/mcp/info"
```

### 4.2 전체 시스템 테스트 스크립트

```python
# test_all.py
import sys
sys.path.insert(0, "D:/Data/18_KAT/KAT")
sys.stdout.reconfigure(encoding='utf-8')

from agent.core.threat_matcher import analyze_incoming_message, reload_threat_data
from agent.mcp.tools import scan_pii, analyze_full

print("=" * 70)
print("Kanana DualGuard 통합 테스트")
print("=" * 70)

# Agent A 테스트
print("\n[Agent A - 발신 보호]")
pii_result = scan_pii("계좌번호 123-456-78901234")
print(f"  PII 감지: {len(pii_result['found_pii'])}개")
print(f"  위험도: {pii_result['highest_risk']}")

# Agent B 테스트
print("\n[Agent B - 수신 보호]")
reload_threat_data()

tests = [
    ("A-1", "엄마 폰 고장났어 인증번호 받아줘"),
    ("B-1", "[택배] 배송보류 bit.ly/xxx"),
    ("SAFE", "오늘 뭐 먹을까"),
]

passed = 0
for expected, text in tests:
    result = analyze_incoming_message(text)
    detected = result['summary.md']['category'] or 'SAFE'
    if detected == expected or (detected is None and expected == "SAFE"):
        passed += 1
        print(f"  [O] {expected}: {result['summary.md']['probability']}")
    else:
        print(f"  [X] 예상 {expected}, 감지 {detected}")

print(f"\n결과: {passed}/{len(tests)} 통과")
print("=" * 70)
```

---

## 5. Swagger UI 테스트

서버가 실행 중일 때 브라우저에서:

- **8001 백엔드 API**: http://localhost:8001/docs
- **8002 Agent API**: http://localhost:8002/docs

Swagger UI에서 직접 API 테스트 가능.

---

## 6. 트러블슈팅

### 포트 충돌

```powershell
# 포트 사용 확인
Get-NetTCPConnection -LocalPort 8002 | Select-Object OwningProcess

# 프로세스 종료
Stop-Process -Id <PID> -Force
```

### 한글 인코딩 오류

```python
import sys
sys.stdout.reconfigure(encoding='utf-8')
```

### 모듈 import 오류

```python
import sys
sys.path.insert(0, "D:/Data/18_KAT/KAT")
```

### 캐시 리셋

```python
from agent.core.threat_matcher import reload_threat_data
reload_threat_data()
```

---

## 7. 빠른 테스트 명령어

```bash
# Agent B 빠른 테스트 (PowerShell)
D:\Data\18_KAT\KAT\backend\venv_gpu\Scripts\python.exe -c "
import sys
sys.path.insert(0, 'D:/Data/18_KAT/KAT')
sys.stdout.reconfigure(encoding='utf-8')
from agent.core.threat_matcher import analyze_incoming_message, reload_threat_data
reload_threat_data()
r = analyze_incoming_message('엄마 폰고장 인증번호 받아줘')
print(f'카테고리: {r[\"summary\"][\"category\"]}')
print(f'확률: {r[\"summary\"][\"probability\"]}')
print(f'패턴: {r[\"summary\"][\"pattern\"]}')
"
```

---

## 8. 테스트 성공 기준

### 최소 통과 기준
- [ ] 서버 3개 모두 실행 (3000, 8001, 8002)
- [ ] Agent A: 계좌번호 감지 성공
- [ ] Agent B: A-1 (가족 사칭) 감지 성공
- [ ] Agent B: SAFE 메시지 0% 확률

### 완전 통과 기준
- [ ] Agent B: 9개 카테고리 모두 정확히 분류
- [ ] MCP 도구 정상 동작
- [ ] Swagger UI 접근 가능
