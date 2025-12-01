# KAT 채팅 테스트 가이드

## 서버 구성

| 포트 | 서비스 | 설명 |
|------|--------|------|
| 3000 | Frontend (React) | 카카오톡 클론 UI |
| 8001 | Node.js Express | 채팅/인증 서버 |
| 8002 | FastAPI Agent API | 보안 분석 API |

## 서버 실행 명령어

```bash
# 터미널 1: Frontend Client (포트 3000)
cd frontend/KakaoTalk/client && npm start

# 터미널 2: Node.js Server (포트 8001)
cd frontend/KakaoTalk/server && npm start

# 터미널 3: FastAPI Agent Server (포트 8002)
python -m uvicorn backend.api.server:app --host 0.0.0.0 --port 8002
```

## 테스트 계정

| user_id | 비밀번호 (추정) |
|---------|----------------|
| test1234 | test1234 |
| test123 | test123 |
| test12 | test12 |

## 채팅 테스트 방법

### 1. 브라우저 2개 준비
- **브라우저 A**: Chrome → http://localhost:3000
- **브라우저 B**: Chrome 시크릿 모드 또는 Edge → http://localhost:3000

### 2. 로그인
- 브라우저 A: `test1234` 로그인
- 브라우저 B: `test123` 로그인

### 3. 친구 추가 및 채팅방 생성
1. 친구 목록에서 상대방 추가
2. 채팅방 생성
3. 메시지 주고받기

## 보안 기능 테스트

### 안심 전송 (발신 분석) - Outgoing Guard
민감정보 감지 테스트 메시지:

```
내 계좌번호는 110-123-456789야
```
```
주민번호 901234-1234567 보내줄게
```
```
카드번호 1234-5678-9012-3456
```
```
비밀번호는 password123!
```

### 안심 가드 (수신 분석) - Incoming Guard
피싱/사기 감지 테스트 메시지:

```
엄마인데 급하게 200만원만 보내줘
```
```
축하합니다! 당첨되셨습니다. 링크 클릭하세요
```
```
긴급! 계정이 정지됩니다. 지금 바로 확인하세요
```
```
경찰입니다. 수사 협조 부탁드립니다. 계좌번호 알려주세요
```

## API 직접 테스트

### 발신 분석 API
```bash
curl -X POST http://localhost:8002/api/agents/analyze/outgoing \
  -H "Content-Type: application/json" \
  -d '{"text": "내 계좌번호는 110-123-456789야", "use_ai": true}'
```

### 수신 분석 API
```bash
curl -X POST http://localhost:8002/api/agents/analyze/incoming \
  -H "Content-Type: application/json" \
  -d '{"text": "엄마인데 급하게 200만원만 보내줘", "use_ai": true}'
```

### 헬스체크
```bash
curl http://localhost:8002/api/agents/health
```

## 예상 응답

### 민감정보 감지 시
```json
{
  "risk_level": "high",
  "reasons": ["계좌번호 감지"],
  "recommended_action": "시크릿 메시지로 전송을 권장합니다",
  "is_secret_recommended": true
}
```

### 피싱 감지 시
```json
{
  "risk_level": "critical",
  "reasons": ["가족 사칭 의심", "긴급 송금 요청"],
  "recommended_action": "주의! 사기 메시지일 가능성이 높습니다",
  "is_secret_recommended": false
}
```

## 문제 해결

### 서버 연결 안됨
- 각 포트가 사용 중인지 확인: `netstat -ano | findstr :3000`
- 방화벽 확인

### 로그인 실패
- 새 계정 회원가입 시도
- DB 파일 확인: `backend/kanana_dualguard.db`

### 보안 분석 안됨
- 8002 서버 로그 확인
- `use_ai: false`로 rule-based 분석 테스트
