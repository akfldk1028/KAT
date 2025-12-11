"""
KAT DualGuard Custom Prometheus Metrics
에이전트 탐지 결과 및 시스템 성능 메트릭

Metrics:
- kat_agent_a_detections_total: Agent A (안심 전송) PII 탐지 횟수
- kat_agent_b_threats_total: Agent B (안심 가드) 위협 탐지 횟수
- kat_scam_db_hits_total: 신고 DB 조회 히트 횟수
- kat_llm_inference_seconds: LLM 추론 시간
- kat_analysis_total: 전체 분석 요청 수
- kat_threat_intel_queries_total: 위협 정보 조회 요청 수
- kat_threat_intel_hits_total: 위협 정보 조회 히트 수
- kat_threat_intel_duration_seconds: 위협 정보 조회 응답 시간
"""

from prometheus_client import Counter, Histogram, Gauge, REGISTRY, generate_latest
from prometheus_fastapi_instrumentator import Instrumentator
from fastapi import FastAPI, Response
import time
from contextlib import contextmanager


class KATMetrics:
    """KAT DualGuard 커스텀 메트릭 관리자"""

    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if KATMetrics._initialized:
            return

        # ===========================================
        # Agent A (안심 전송) 메트릭
        # ===========================================
        self.agent_a_detections = Counter(
            'kat_agent_a_detections_total',
            'Agent A PII 탐지 횟수',
            ['risk_level', 'pii_type']
        )

        self.agent_a_blocked = Counter(
            'kat_agent_a_blocked_total',
            'Agent A 차단 권장 횟수',
            ['risk_level']
        )

        # ===========================================
        # Agent B (안심 가드) 메트릭
        # ===========================================
        self.agent_b_threats = Counter(
            'kat_agent_b_threats_total',
            'Agent B 위협 탐지 횟수',
            ['risk_level', 'category']
        )

        self.agent_b_scam_probability = Histogram(
            'kat_agent_b_scam_probability',
            'Agent B 사기 확률 분포',
            buckets=[10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
        )

        # ===========================================
        # 신고 DB 메트릭
        # ===========================================
        self.scam_db_hits = Counter(
            'kat_scam_db_hits_total',
            '신고 DB 조회 히트 횟수',
            ['source']  # kisa, thecheat, local
        )

        self.scam_db_queries = Counter(
            'kat_scam_db_queries_total',
            '신고 DB 조회 요청 횟수',
            ['source']
        )

        # ===========================================
        # LLM 메트릭
        # ===========================================
        self.llm_inference_seconds = Histogram(
            'kat_llm_inference_seconds',
            'LLM 추론 시간 (초)',
            ['model_type'],  # instruct, vision
            buckets=[0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0]
        )

        self.llm_requests = Counter(
            'kat_llm_requests_total',
            'LLM 요청 횟수',
            ['model_type', 'status']  # success, error
        )

        # ===========================================
        # 전체 분석 메트릭
        # ===========================================
        self.analysis_total = Counter(
            'kat_analysis_total',
            '전체 분석 요청 수',
            ['agent_type', 'status']  # agent_a/agent_b, success/error
        )

        self.analysis_duration = Histogram(
            'kat_analysis_duration_seconds',
            '분석 소요 시간 (초)',
            ['agent_type'],
            buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0]
        )

        # ===========================================
        # 시크릿 메시지 메트릭
        # ===========================================
        self.secret_messages_created = Counter(
            'kat_secret_messages_created_total',
            '시크릿 메시지 생성 횟수'
        )

        self.secret_messages_viewed = Counter(
            'kat_secret_messages_viewed_total',
            '시크릿 메시지 열람 횟수'
        )

        # ===========================================
        # MCP 도구 메트릭
        # ===========================================
        self.mcp_calls = Counter(
            'kat_mcp_calls_total',
            'MCP 도구 호출 횟수',
            ['tool_name', 'status']  # analyze_outgoing/incoming, success/error
        )

        self.mcp_duration = Histogram(
            'kat_mcp_duration_seconds',
            'MCP 도구 응답 시간 (초)',
            ['tool_name'],
            buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0]
        )

        self.mcp_active = Gauge(
            'kat_mcp_active_calls',
            '현재 진행 중인 MCP 호출 수',
            ['tool_name']
        )

        # ===========================================
        # MCP 서버 상태 메트릭
        # ===========================================
        self.mcp_server_up = Gauge(
            'kat_mcp_server_up',
            'MCP 서버 가동 상태 (1=healthy, 0=unhealthy)'
        )

        self.mcp_tools_registered = Gauge(
            'kat_mcp_tools_registered',
            '등록된 MCP 도구 수'
        )

        self.mcp_health_check_duration = Histogram(
            'kat_mcp_health_check_duration_seconds',
            'MCP 헬스체크 응답 시간 (초)',
            buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0]
        )

        # ===========================================
        # Threat Intelligence 메트릭
        # ===========================================
        self.threat_intel_queries = Counter(
            'kat_threat_intel_queries_total',
            '위협 정보 조회 요청 수',
            ['source', 'type']  # source: lrl/kisa/thecheat/virustotal, type: phone/url/account
        )

        self.threat_intel_hits = Counter(
            'kat_threat_intel_hits_total',
            '위협 정보 조회 히트 수 (위협 발견)',
            ['source', 'type']
        )

        self.threat_intel_duration = Histogram(
            'kat_threat_intel_duration_seconds',
            '위협 정보 조회 응답 시간',
            ['source'],
            buckets=[0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0]
        )

        KATMetrics._initialized = True

    # ===========================================
    # Agent A 기록 메서드
    # ===========================================
    def record_agent_a_detection(self, risk_level: str, pii_type: str = "unknown"):
        """Agent A PII 탐지 기록"""
        self.agent_a_detections.labels(
            risk_level=risk_level,
            pii_type=pii_type
        ).inc()

    def record_agent_a_blocked(self, risk_level: str):
        """Agent A 차단 권장 기록"""
        self.agent_a_blocked.labels(risk_level=risk_level).inc()

    # ===========================================
    # Agent B 기록 메서드
    # ===========================================
    def record_agent_b_threat(self, risk_level: str, category: str = "unknown"):
        """Agent B 위협 탐지 기록"""
        self.agent_b_threats.labels(
            risk_level=risk_level,
            category=category
        ).inc()

    def record_scam_probability(self, probability: int):
        """Agent B 사기 확률 기록"""
        self.agent_b_scam_probability.observe(probability)

    # ===========================================
    # 신고 DB 기록 메서드
    # ===========================================
    def record_scam_db_query(self, source: str, hit: bool = False):
        """신고 DB 조회 기록"""
        self.scam_db_queries.labels(source=source).inc()
        if hit:
            self.scam_db_hits.labels(source=source).inc()

    # ===========================================
    # LLM 기록 메서드
    # ===========================================
    @contextmanager
    def measure_llm_inference(self, model_type: str):
        """LLM 추론 시간 측정 컨텍스트 매니저"""
        start = time.time()
        status = "success"
        try:
            yield
        except Exception:
            status = "error"
            raise
        finally:
            duration = time.time() - start
            self.llm_inference_seconds.labels(model_type=model_type).observe(duration)
            self.llm_requests.labels(model_type=model_type, status=status).inc()

    # ===========================================
    # 분석 기록 메서드
    # ===========================================
    @contextmanager
    def measure_analysis(self, agent_type: str):
        """분석 시간 측정 컨텍스트 매니저"""
        start = time.time()
        status = "success"
        try:
            yield
        except Exception:
            status = "error"
            raise
        finally:
            duration = time.time() - start
            self.analysis_duration.labels(agent_type=agent_type).observe(duration)
            self.analysis_total.labels(agent_type=agent_type, status=status).inc()

    def record_analysis(self, agent_type: str, status: str = "success"):
        """분석 요청 기록"""
        self.analysis_total.labels(agent_type=agent_type, status=status).inc()

    # ===========================================
    # 시크릿 메시지 기록 메서드
    # ===========================================
    def record_secret_created(self):
        """시크릿 메시지 생성 기록"""
        self.secret_messages_created.inc()

    def record_secret_viewed(self):
        """시크릿 메시지 열람 기록"""
        self.secret_messages_viewed.inc()

    # ===========================================
    # MCP 도구 기록 메서드
    # ===========================================
    @contextmanager
    def measure_mcp_call(self, tool_name: str):
        """MCP 도구 호출 시간 측정 컨텍스트 매니저"""
        self.mcp_active.labels(tool_name=tool_name).inc()
        start = time.time()
        status = "success"
        try:
            yield
        except Exception:
            status = "error"
            raise
        finally:
            self.mcp_active.labels(tool_name=tool_name).dec()
            duration = time.time() - start
            self.mcp_duration.labels(tool_name=tool_name).observe(duration)
            self.mcp_calls.labels(tool_name=tool_name, status=status).inc()

    def record_mcp_call(self, tool_name: str, status: str = "success"):
        """MCP 도구 호출 기록"""
        self.mcp_calls.labels(tool_name=tool_name, status=status).inc()

    # ===========================================
    # MCP 서버 상태 기록 메서드
    # ===========================================
    def record_mcp_server_status(self, is_healthy: bool, tools_count: int = 0):
        """MCP 서버 상태 기록"""
        self.mcp_server_up.set(1 if is_healthy else 0)
        self.mcp_tools_registered.set(tools_count)

    def record_mcp_health_check(self, duration_seconds: float):
        """MCP 헬스체크 시간 기록"""
        self.mcp_health_check_duration.observe(duration_seconds)

    # ===========================================
    # Threat Intelligence 기록 메서드
    # ===========================================
    def record_threat_intel_query(self, source: str, type: str, hit: bool = False):
        """위협 정보 조회 기록"""
        self.threat_intel_queries.labels(source=source, type=type).inc()
        if hit:
            self.threat_intel_hits.labels(source=source, type=type).inc()

    @contextmanager
    def measure_threat_intel(self, source: str):
        """위협 정보 조회 시간 측정 컨텍스트 매니저"""
        start = time.time()
        try:
            yield
        finally:
            duration = time.time() - start
            self.threat_intel_duration.labels(source=source).observe(duration)


def setup_metrics(app: FastAPI) -> Instrumentator:
    """
    FastAPI 앱에 Prometheus 메트릭 설정

    Args:
        app: FastAPI 애플리케이션 인스턴스

    Returns:
        Instrumentator 인스턴스
    """
    # prometheus-fastapi-instrumentator로 기본 HTTP 메트릭 수집
    instrumentator = Instrumentator(
        should_group_status_codes=True,
        should_ignore_untemplated=True,
        should_respect_env_var=True,
        should_instrument_requests_inprogress=True,
        excluded_handlers=["/metrics", "/health", "/docs", "/openapi.json"],
        inprogress_name="http_requests_inprogress",
        inprogress_labels=True,
    )

    # FastAPI 앱에 instrument 적용
    instrumentator.instrument(app)

    # /metrics 엔드포인트 노출
    @app.get("/metrics", include_in_schema=False)
    async def metrics():
        """Prometheus 메트릭 엔드포인트"""
        return Response(
            content=generate_latest(REGISTRY),
            media_type="text/plain; charset=utf-8"
        )

    print("[Metrics] Prometheus 메트릭 설정 완료 - /metrics 엔드포인트 활성화")

    return instrumentator
