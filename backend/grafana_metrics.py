"""
Grafana Dashboard Metrics API
포트 3001에서 실행되며 KAT 시스템의 메트릭을 제공합니다.
"""
from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import psutil
import time
from datetime import datetime
from typing import Dict, Any
import json

app = FastAPI(title="KAT Grafana Metrics API", version="1.0.0")

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 메트릭 저장소
metrics_store = {
    "start_time": time.time(),
    "request_count": 0,
    "frontend_status": "unknown",
    "backend_status": "unknown",
    "agent_status": "unknown",
    # Agent B 테스트 결과
    "agent_b_test": {
        "total_cases": 0,
        "high_risk_count": 0,
        "medium_risk_count": 0,
        "low_risk_count": 0,
        "avg_scam_probability": 0,
        "category_distribution": {},
        "last_updated": None
    }
}


@app.get("/")
async def root():
    """루트 엔드포인트"""
    return {
        "service": "KAT Grafana Metrics API",
        "version": "1.0.0",
        "endpoints": {
            "metrics": "/metrics",
            "prometheus": "/metrics/prometheus",
            "json": "/api/metrics",
            "health": "/health"
        }
    }


@app.get("/health")
async def health_check():
    """헬스 체크 엔드포인트"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "uptime_seconds": time.time() - metrics_store["start_time"]
    }


@app.get("/api/metrics")
async def get_metrics_json():
    """JSON 형식의 메트릭 반환 (Grafana JSON API 플러그인용)"""
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')

    metrics_store["request_count"] += 1
    uptime = time.time() - metrics_store["start_time"]

    return {
        "timestamp": datetime.now().isoformat(),
        "uptime_seconds": uptime,
        "system": {
            "cpu_percent": cpu_percent,
            "memory_percent": memory.percent,
            "memory_used_mb": memory.used / (1024 * 1024),
            "memory_total_mb": memory.total / (1024 * 1024),
            "disk_percent": disk.percent,
            "disk_used_gb": disk.used / (1024 * 1024 * 1024),
            "disk_total_gb": disk.total / (1024 * 1024 * 1024)
        },
        "services": {
            "frontend": metrics_store.get("frontend_status", "unknown"),
            "backend": metrics_store.get("backend_status", "unknown"),
            "agent": metrics_store.get("agent_status", "unknown")
        },
        "stats": {
            "request_count": metrics_store["request_count"]
        }
    }


@app.get("/metrics")
@app.get("/metrics/prometheus")
async def get_metrics_prometheus():
    """Prometheus 형식의 메트릭 반환"""
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')

    metrics_store["request_count"] += 1
    uptime = time.time() - metrics_store["start_time"]

    # Agent B 메트릭
    agent_b = metrics_store["agent_b_test"]

    # Prometheus 형식으로 메트릭 생성
    prometheus_metrics = f"""# HELP kat_uptime_seconds KAT system uptime in seconds
# TYPE kat_uptime_seconds gauge
kat_uptime_seconds {uptime}

# HELP kat_request_total Total number of requests
# TYPE kat_request_total counter
kat_request_total {metrics_store["request_count"]}

# HELP kat_cpu_percent CPU usage percentage
# TYPE kat_cpu_percent gauge
kat_cpu_percent {cpu_percent}

# HELP kat_memory_percent Memory usage percentage
# TYPE kat_memory_percent gauge
kat_memory_percent {memory.percent}

# HELP kat_memory_used_bytes Memory used in bytes
# TYPE kat_memory_used_bytes gauge
kat_memory_used_bytes {memory.used}

# HELP kat_memory_total_bytes Total memory in bytes
# TYPE kat_memory_total_bytes gauge
kat_memory_total_bytes {memory.total}

# HELP kat_disk_percent Disk usage percentage
# TYPE kat_disk_percent gauge
kat_disk_percent {disk.percent}

# HELP kat_disk_used_bytes Disk used in bytes
# TYPE kat_disk_used_bytes gauge
kat_disk_used_bytes {disk.used}

# HELP kat_disk_total_bytes Total disk in bytes
# TYPE kat_disk_total_bytes gauge
kat_disk_total_bytes {disk.total}

# HELP kat_agent_b_total_cases Total number of Agent B test cases
# TYPE kat_agent_b_total_cases gauge
kat_agent_b_total_cases {agent_b["total_cases"]}

# HELP kat_agent_b_high_risk Number of high risk detections
# TYPE kat_agent_b_high_risk gauge
kat_agent_b_high_risk {agent_b["high_risk_count"]}

# HELP kat_agent_b_medium_risk Number of medium risk detections
# TYPE kat_agent_b_medium_risk gauge
kat_agent_b_medium_risk {agent_b["medium_risk_count"]}

# HELP kat_agent_b_low_risk Number of low risk detections
# TYPE kat_agent_b_low_risk gauge
kat_agent_b_low_risk {agent_b["low_risk_count"]}

# HELP kat_agent_b_avg_scam_probability Average scam probability percentage
# TYPE kat_agent_b_avg_scam_probability gauge
kat_agent_b_avg_scam_probability {agent_b["avg_scam_probability"]}
"""

    return Response(content=prometheus_metrics, media_type="text/plain")


@app.post("/api/metrics/update")
async def update_service_status(status_data: Dict[str, Any]):
    """서비스 상태 업데이트 (다른 서비스에서 호출)"""
    if "frontend_status" in status_data:
        metrics_store["frontend_status"] = status_data["frontend_status"]
    if "backend_status" in status_data:
        metrics_store["backend_status"] = status_data["backend_status"]
    if "agent_status" in status_data:
        metrics_store["agent_status"] = status_data["agent_status"]

    return {"status": "updated", "metrics": metrics_store}


@app.post("/api/metrics/agent-b")
async def update_agent_b_metrics(test_results: Dict[str, Any]):
    """Agent B 테스트 결과 업데이트"""
    if "agent_b_test_results" in test_results:
        metrics_store["agent_b_test"].update(test_results["agent_b_test_results"])
        metrics_store["agent_b_test"]["last_updated"] = datetime.now().isoformat()

    return {"status": "updated", "agent_b_metrics": metrics_store["agent_b_test"]}


@app.get("/api/metrics/agent-b")
async def get_agent_b_metrics():
    """Agent B 테스트 결과 조회"""
    return metrics_store["agent_b_test"]


@app.get("/api/query")
async def grafana_query(query: str = ""):
    """Grafana Simple JSON Datasource 쿼리 엔드포인트"""
    metrics = await get_metrics_json()

    # 쿼리에 따라 다른 데이터 반환
    if "cpu" in query.lower():
        return [{"target": "CPU Usage", "datapoints": [[metrics["system"]["cpu_percent"], int(time.time() * 1000)]]}]
    elif "memory" in query.lower():
        return [{"target": "Memory Usage", "datapoints": [[metrics["system"]["memory_percent"], int(time.time() * 1000)]]}]
    elif "disk" in query.lower():
        return [{"target": "Disk Usage", "datapoints": [[metrics["system"]["disk_percent"], int(time.time() * 1000)]]}]
    else:
        # 기본: 모든 주요 메트릭 반환
        return [
            {"target": "CPU Usage (%)", "datapoints": [[metrics["system"]["cpu_percent"], int(time.time() * 1000)]]},
            {"target": "Memory Usage (%)", "datapoints": [[metrics["system"]["memory_percent"], int(time.time() * 1000)]]},
            {"target": "Disk Usage (%)", "datapoints": [[metrics["system"]["disk_percent"], int(time.time() * 1000)]]},
            {"target": "Request Count", "datapoints": [[metrics["stats"]["request_count"], int(time.time() * 1000)]]}
        ]


@app.post("/api/search")
async def grafana_search():
    """Grafana Simple JSON Datasource 검색 엔드포인트"""
    return [
        "cpu_usage",
        "memory_usage",
        "disk_usage",
        "request_count",
        "uptime"
    ]


if __name__ == "__main__":
    print("=" * 60)
    print("KAT Grafana Metrics API 시작")
    print("=" * 60)
    print("포트: 3001")
    print("엔드포인트:")
    print("  - http://localhost:3001/           (API 정보)")
    print("  - http://localhost:3001/health     (헬스 체크)")
    print("  - http://localhost:3001/metrics    (Prometheus 형식)")
    print("  - http://localhost:3001/api/metrics (JSON 형식)")
    print("=" * 60)

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=3001,
        reload=True,
        log_level="info"
    )
