# KAT DualGuard Monitoring Stack

PLG Stack (Prometheus + Loki + Grafana) 기반 모니터링 시스템

## 비용

**모두 무료 (오픈소스)**
- Prometheus: Apache 2.0 License
- Grafana: AGPLv3 (Community Edition)
- Loki: AGPLv3

## 사전 요구사항

- Docker Desktop for Windows
- Python 패키지: `prometheus-client`, `prometheus-fastapi-instrumentator`

```bash
pip install prometheus-client prometheus-fastapi-instrumentator
```

## 폴더 구조

```
ops/
├── monitoring/
│   ├── docker-compose.yml      # PLG 스택 컨테이너 설정
│   ├── prometheus/
│   │   └── prometheus.yml      # 스크래핑 설정
│   ├── grafana/
│   │   ├── provisioning/
│   │   │   ├── datasources/    # 데이터소스 자동 설정
│   │   │   └── dashboards/     # 대시보드 프로비저닝
│   │   └── dashboards/         # JSON 대시보드 파일
│   ├── loki/
│   │   └── loki-config.yml     # Loki 설정
│   └── metrics/                # Python 메트릭 모듈
│       ├── __init__.py
│       └── kat_metrics.py
└── scripts/
    ├── start-monitoring.bat    # Windows 시작 스크립트
    └── stop-monitoring.bat     # Windows 중지 스크립트
```

## 빠른 시작

### 1. 모니터링 스택 시작

```bash
# Windows
ops\scripts\start-monitoring.bat

# 또는 직접 실행
cd ops/monitoring
docker-compose up -d
```

### 2. 접속 정보

| 서비스 | URL | 인증 |
|--------|-----|------|
| Grafana | http://localhost:3001 | admin / katadmin123 |
| Prometheus | http://localhost:9090 | - |
| Loki | http://localhost:3100 | - |

### 3. FastAPI 서버 메트릭 통합

`backend/api/server.py` 파일에 다음 코드를 추가하세요:

```python
# === import 섹션 상단에 추가 ===
# Prometheus 메트릭 모듈 로드
METRICS_ENABLED = False
kat_metrics = None
setup_metrics = None
try:
    sys.path.insert(0, str(PROJECT_ROOT / "ops" / "monitoring"))
    from metrics import setup_metrics, kat_metrics
    METRICS_ENABLED = True
    print("[Metrics] 메트릭 모듈 로드 성공")
except ImportError as e:
    print(f"[Metrics] 메트릭 모듈 로드 실패 (무시됨): {e}")

# === app 생성 후에 추가 ===
# Prometheus 메트릭 설정
if METRICS_ENABLED and setup_metrics:
    setup_metrics(app)
    print("[Metrics] Prometheus /metrics 엔드포인트 활성화")
```

### 4. 커스텀 메트릭 기록 (선택)

```python
# Agent A 분석 엔드포인트에서
if METRICS_ENABLED and kat_metrics:
    kat_metrics.record_agent_a_detection("HIGH", "account_number")
    kat_metrics.record_agent_a_blocked("HIGH")

# Agent B 분석 엔드포인트에서
if METRICS_ENABLED and kat_metrics:
    kat_metrics.record_agent_b_threat("CRITICAL", "A-1")
    kat_metrics.record_scam_probability(85)
```

## 대시보드

Grafana에 자동으로 "KAT DualGuard Overview" 대시보드가 생성됩니다.

### 포함된 패널
- Agent A: PII 탐지 총계
- Agent B: 위협 탐지 총계
- CRITICAL 위험도 탐지
- API 응답시간 (p95)
- 위험도별 탐지 추이
- 카테고리별 위협 탐지 추이
- PII 유형 분포 (파이차트)
- 위협 카테고리 분포 (파이차트)
- API 요청량 (RPS)

## 커스텀 메트릭 목록

| 메트릭 이름 | 타입 | 설명 | 라벨 |
|-------------|------|------|------|
| `kat_agent_a_detections_total` | Counter | Agent A PII 탐지 횟수 | risk_level, pii_type |
| `kat_agent_a_blocked_total` | Counter | Agent A 차단 권장 횟수 | risk_level |
| `kat_agent_b_threats_total` | Counter | Agent B 위협 탐지 횟수 | risk_level, category |
| `kat_agent_b_scam_probability` | Histogram | 사기 확률 분포 | - |
| `kat_scam_db_hits_total` | Counter | 신고 DB 히트 횟수 | source |
| `kat_llm_inference_seconds` | Histogram | LLM 추론 시간 | model_type |
| `kat_analysis_total` | Counter | 전체 분석 요청 수 | agent_type, status |
| `kat_analysis_duration_seconds` | Histogram | 분석 소요 시간 | agent_type |

## 문제 해결

### Docker Compose 시작 실패
```bash
# Docker Desktop이 실행 중인지 확인
docker info

# 포트 충돌 확인
netstat -ano | findstr :3001
netstat -ano | findstr :9090
```

### 메트릭이 수집되지 않음
```bash
# FastAPI 서버 /metrics 엔드포인트 확인
curl http://localhost:8002/metrics

# Prometheus 타겟 상태 확인
# http://localhost:9090/targets 접속
```

### Grafana 대시보드가 비어있음
- Prometheus 데이터소스 연결 확인
- FastAPI 서버가 실행 중인지 확인
- 메트릭 이름이 올바른지 확인

## 중지

```bash
# Windows
ops\scripts\stop-monitoring.bat

# 또는 직접 실행
cd ops/monitoring
docker-compose down

# 볼륨까지 삭제 (데이터 초기화)
docker-compose down -v
```
