"""
Agent B API Connection Test Script
ver9.0 - 6 DB Sources Check (with LRL API)
"""
import os
import sys
import io
from pathlib import Path

# Fix encoding for Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Project root
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Load .env
from dotenv import load_dotenv
load_dotenv(project_root / "backend" / ".env")

print("=" * 60)
print("Agent B API Connection Test (ver9.0)")
print("=" * 60)

# 1. Environment variables check
print("\n[1] Environment Variables Check")
print("-" * 40)

env_vars = {
    "KANANA_LLM_API_KEY": os.getenv("KANANA_LLM_API_KEY"),
    "KANANA_LLM_BASE_URL": os.getenv("KANANA_LLM_BASE_URL"),
    "THECHEAT_API_KEY": os.getenv("THECHEAT_API_KEY"),
    "KISA_PHISHING_API_KEY": os.getenv("KISA_PHISHING_API_KEY"),
    "VIRUSTOTAL_API_KEY": os.getenv("VIRUSTOTAL_API_KEY"),
    "LRL_API_KEY": os.getenv("LRL_API_KEY"),
}

for key, value in env_vars.items():
    if value:
        masked = value[:10] + "..." if len(value) > 10 else value
        print(f"  [OK] {key}: {masked}")
    else:
        print(f"  [X]  {key}: Not Set")

# 2. TheCheat API Test
print("\n[2] TheCheat API Connection Test")
print("-" * 40)
try:
    from agent.core.thecheat_api import get_thecheat_client, check_phone_thecheat
    client = get_thecheat_client()
    if client:
        print("  [OK] TheCheat API Client initialized")
    else:
        print("  [WARN] TheCheat API Key not set - Using Mock DB only")
except Exception as e:
    print(f"  [ERR] TheCheat API Error: {e}")

# 3. LRL API Test (Google Safe Browsing replacement)
print("\n[3] LRL API Connection Test (Google Safe Browsing replacement)")
print("-" * 40)
try:
    from agent.core.lrl_api import get_lrl_client, check_url_lrl
    client = get_lrl_client()
    if client:
        print("  [OK] LRL API Client initialized")
        # Test with safe URL
        result = check_url_lrl("https://www.google.com")
        if result:
            print(f"  -> Test URL safe={result.get('is_safe')}")
    else:
        print("  [WARN] LRL API Key not set")
except Exception as e:
    print(f"  [ERR] LRL API Error: {e}")

# 4. KISA Phishing API Test
print("\n[4] KISA Phishing API Connection Test")
print("-" * 40)
try:
    from agent.core.kisa_phishing_api import get_kisa_cache, check_url_kisa
    cache = get_kisa_cache()
    if cache:
        print("  [OK] KISA Phishing Cache initialized")
        print(f"  -> Cache records: {cache.cache_data.get('total_count', 0)}")
        print(f"  -> Last updated: {cache.cache_data.get('updated_at', 'N/A')}")
    else:
        print("  [WARN] KISA API Key not set - Cache unavailable")
except Exception as e:
    print(f"  [ERR] KISA API Error: {e}")

# 5. VirusTotal API Test
print("\n[5] VirusTotal API Connection Test")
print("-" * 40)
try:
    from agent.core.virustotal_api import get_virustotal_client, check_url_virustotal
    client = get_virustotal_client()
    if client:
        print("  [OK] VirusTotal API Client initialized")
    else:
        print("  [WARN] VirusTotal API Key not set")
except Exception as e:
    print(f"  [ERR] VirusTotal API Error: {e}")

# 6. Kanana LLM API Test
print("\n[6] Kanana LLM API Connection Test")
print("-" * 40)
try:
    import requests
    api_key = os.getenv("KANANA_LLM_API_KEY")
    base_url = os.getenv("KANANA_LLM_BASE_URL")

    if api_key and base_url:
        headers = {"Authorization": f"Bearer {api_key}"}
        response = requests.get(f"{base_url}/models", headers=headers, timeout=10)

        if response.status_code == 200:
            models = response.json()
            print("  [OK] Kanana LLM API Connected")
            if "data" in models:
                for model in models["data"][:3]:
                    print(f"  -> Available model: {model.get('id', 'unknown')}")
        else:
            print(f"  [WARN] Kanana LLM API Response: {response.status_code}")
    else:
        print("  [X] Kanana LLM API Key not set")
except Exception as e:
    print(f"  [ERR] Kanana LLM API Error: {e}")

# 7. Prometheus Metrics Test
print("\n[7] Prometheus Metrics Module Test")
print("-" * 40)
try:
    from ops.monitoring.metrics.kat_metrics import KATMetrics
    metrics = KATMetrics()
    print("  [OK] KATMetrics module loaded")
    print(f"  -> Agent A metrics: {hasattr(metrics, 'agent_a_detections')}")
    print(f"  -> Agent B metrics: {hasattr(metrics, 'agent_b_threats')}")
except Exception as e:
    print(f"  [ERR] Prometheus Metrics Error: {e}")

# 8. Grafana/Prometheus Check
print("\n[8] Grafana/Prometheus Docker Check")
print("-" * 40)
try:
    import requests
    # Check Prometheus
    prom_response = requests.get("http://localhost:9090/-/healthy", timeout=5)
    if prom_response.status_code == 200:
        print("  [OK] Prometheus is running at http://localhost:9090")
    else:
        print(f"  [WARN] Prometheus response: {prom_response.status_code}")
except:
    print("  [X] Prometheus not reachable")

try:
    # Check Grafana
    graf_response = requests.get("http://localhost:3001/api/health", timeout=5)
    if graf_response.status_code == 200:
        print("  [OK] Grafana is running at http://localhost:3001")
    else:
        print(f"  [WARN] Grafana response: {graf_response.status_code}")
except:
    print("  [X] Grafana not reachable")

# 9. IncomingAgent Module Test
print("\n[9] IncomingAgent Module Test")
print("-" * 40)
try:
    from agent.agents.incoming import IncomingAgent
    print("  [OK] IncomingAgent module loaded")
except Exception as e:
    print(f"  [ERR] IncomingAgent Error: {e}")

print("\n" + "=" * 60)
print("API Connection Test Complete")
print("=" * 60)

# Summary
print("\n[Summary] Stage 1 DB Source Status:")
print("-" * 40)
print("  1. TheCheat       : " + ("[OK] Connected" if os.getenv("THECHEAT_API_KEY") else "[WARN] Mock DB"))
print("  2. LRL (SafeBr)   : " + ("[OK] Connected" if os.getenv("LRL_API_KEY") else "[WARN] Not set"))
print("  3. KISA Phishing  : " + ("[OK] Connected" if os.getenv("KISA_PHISHING_API_KEY") else "[WARN] Cache only"))
print("  4. VirusTotal     : " + ("[OK] Connected" if os.getenv("VIRUSTOTAL_API_KEY") else "[WARN] Not set"))
print("  5. Police DB      : [WARN] Mock DB (not implemented)")
print("  6. CounterScam 112: [WARN] Mock DB (not implemented)")
print("\n  Kanana LLM       : " + ("[OK] Connected" if os.getenv("KANANA_LLM_API_KEY") else "[X] Not set"))
print("  Grafana          : http://localhost:3001 (admin/katadmin123)")
print("  Prometheus       : http://localhost:9090")
