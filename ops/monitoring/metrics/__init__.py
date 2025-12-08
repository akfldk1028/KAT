"""
KAT DualGuard Monitoring Metrics Module
Prometheus 메트릭 수집 및 노출

사용법:
    from ops.monitoring.metrics import setup_metrics, kat_metrics

    # FastAPI 앱에 메트릭 설정
    setup_metrics(app)

    # 커스텀 메트릭 기록
    kat_metrics.record_agent_a_detection("HIGH", "account_number")
    kat_metrics.record_agent_b_threat("CRITICAL", "A-1")
"""

from .kat_metrics import KATMetrics, setup_metrics

# 싱글톤 인스턴스
kat_metrics = KATMetrics()

__all__ = ['setup_metrics', 'kat_metrics', 'KATMetrics']
