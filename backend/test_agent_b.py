"""
Agent B 테스트 스크립트
dev_test_sample.json의 케이스들을 Agent B API로 테스트하고 결과를 출력합니다.
"""
import json
import requests
import time
from pathlib import Path
from typing import Dict, List
from datetime import datetime

# API 엔드포인트
AGENT_B_URL = "http://localhost:8002/api/agents/analyze/incoming"
METRICS_URL = "http://localhost:3001/api/metrics"

# 테스트 데이터 경로
TEST_DATA_PATH = Path(__file__).parent.parent / "docs" / "dev_test_sample.json"


def load_test_data() -> dict:
    """테스트 데이터 로드"""
    with open(TEST_DATA_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)


def analyze_conversation(case_id: str, sessions: List[dict], use_ai: bool = True) -> dict:
    """
    대화 세션들을 Agent B로 분석

    Args:
        case_id: 케이스 ID (A-001, B-006 등)
        sessions: 세션 리스트
        use_ai: AI 분석 사용 여부

    Returns:
        분석 결과 딕셔너리
    """
    results = []

    # 각 세션의 메시지를 순차적으로 분석
    conversation_history = []

    for session in sessions:
        session_id = session["session_id"]
        messages = session["messages"]

        # 세션의 모든 메시지를 하나의 텍스트로 결합
        combined_text = " ".join(messages)

        # API 요청
        payload = {
            "text": combined_text,
            "sender_id": 999,  # 테스트용 발신자 ID
            "receiver_id": 1,  # 테스트용 수신자 ID
            "conversation_history": conversation_history,  # 이전 대화 맥락
            "use_ai": use_ai
        }

        try:
            response = requests.post(AGENT_B_URL, json=payload, timeout=30)
            response.raise_for_status()
            result = response.json()

            # 결과 저장
            results.append({
                "session_id": session_id,
                "messages": messages,
                "analysis": result
            })

            # 대화 히스토리에 추가 (다음 세션 분석에 사용)
            for msg in messages:
                conversation_history.append({
                    "sender_id": 999,
                    "message": msg,
                    "timestamp": datetime.now().isoformat()
                })

            print(f"  세션 {session_id}: {result['risk_level']} - {result.get('category', 'N/A')} - {result.get('scam_probability', 0)}%")

        except Exception as e:
            print(f"  세션 {session_id} 분석 실패: {e}")
            results.append({
                "session_id": session_id,
                "messages": messages,
                "error": str(e)
            })

    return {
        "case_id": case_id,
        "total_sessions": len(sessions),
        "results": results
    }


def print_case_summary(case_result: dict):
    """케이스 분석 결과 요약 출력"""
    case_id = case_result["case_id"]
    results = case_result["results"]

    # 최종 위험도 (마지막 세션 기준)
    final_result = results[-1]["analysis"] if results and "analysis" in results[-1] else None

    if final_result:
        print(f"\n{'='*80}")
        print(f"케이스: {case_id}")
        print(f"총 세션 수: {case_result['total_sessions']}")
        print(f"최종 위험도: {final_result['risk_level']}")
        print(f"카테고리: {final_result.get('category', 'N/A')} - {final_result.get('category_name', 'N/A')}")
        print(f"사기 확률: {final_result.get('scam_probability', 0)}%")
        print(f"이유: {', '.join(final_result.get('reasons', []))}")
        print(f"권장 조치: {final_result['recommended_action']}")
        print(f"{'='*80}\n")
    else:
        print(f"\n케이스 {case_id}: 분석 실패\n")


def update_grafana_metrics(test_results: List[dict]):
    """Grafana 메트릭 업데이트"""
    try:
        # Agent B 테스트 결과 통계 계산
        total_cases = len(test_results)
        high_risk_count = 0
        medium_risk_count = 0
        low_risk_count = 0

        category_counts = {}
        total_scam_probability = 0
        scam_count = 0

        for case_result in test_results:
            results = case_result["results"]
            if results and "analysis" in results[-1]:
                final_result = results[-1]["analysis"]
                risk_level = final_result["risk_level"]

                if risk_level in ["HIGH", "CRITICAL"]:
                    high_risk_count += 1
                elif risk_level == "MEDIUM":
                    medium_risk_count += 1
                else:
                    low_risk_count += 1

                # 카테고리 집계
                category = final_result.get("category", "unknown")
                category_counts[category] = category_counts.get(category, 0) + 1

                # 사기 확률 평균 계산
                scam_prob = final_result.get("scam_probability", 0)
                if scam_prob > 0:
                    total_scam_probability += scam_prob
                    scam_count += 1

        avg_scam_probability = total_scam_probability / scam_count if scam_count > 0 else 0

        # 메트릭 데이터 구성
        metrics_data = {
            "agent_b_test_results": {
                "total_cases": total_cases,
                "high_risk_count": high_risk_count,
                "medium_risk_count": medium_risk_count,
                "low_risk_count": low_risk_count,
                "avg_scam_probability": round(avg_scam_probability, 2),
                "category_distribution": category_counts
            },
            "timestamp": datetime.now().isoformat()
        }

        # Grafana 메트릭 서버로 전송
        print("\n" + "="*80)
        print("Grafana 메트릭 업데이트 중...")
        print("="*80)

        try:
            # Grafana 메트릭 API로 POST 전송
            response = requests.post(
                "http://localhost:3001/api/metrics/agent-b",
                json=metrics_data,
                timeout=5
            )
            response.raise_for_status()
            print("✅ Grafana 메트릭 서버로 전송 완료!")
            print(f"   URL: http://localhost:3001/api/metrics/agent-b")
        except Exception as e:
            print(f"⚠️  Grafana 메트릭 서버 전송 실패: {e}")
            print("   (메트릭은 로컬에 저장됩니다)")

        print(json.dumps(metrics_data, indent=2, ensure_ascii=False))
        print("="*80 + "\n")

        return metrics_data

    except Exception as e:
        print(f"메트릭 업데이트 실패: {e}")
        return None


def main():
    """메인 테스트 실행"""
    print("\n" + "="*80)
    print("Agent B 테스트 시작")
    print("="*80 + "\n")

    # 테스트 데이터 로드
    test_data = load_test_data()
    conversations = test_data["conversations"]

    print(f"총 {len(conversations)}개 케이스 로드됨\n")

    # 각 케이스 테스트
    all_results = []

    for conversation in conversations:
        case_id = conversation["case_id"]
        sessions = conversation["sessions"]

        print(f"케이스 {case_id} 분석 중... ({len(sessions)}개 세션)")

        # 대화 분석
        case_result = analyze_conversation(case_id, sessions, use_ai=True)
        all_results.append(case_result)

        # 결과 요약 출력
        print_case_summary(case_result)

        # API Rate Limiting 방지
        time.sleep(0.5)

    # 전체 결과 통계
    print("\n" + "="*80)
    print("전체 테스트 결과 통계")
    print("="*80)
    print(f"총 케이스 수: {len(all_results)}")

    # 위험도별 집계
    risk_counts = {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0}
    category_counts = {}

    for case_result in all_results:
        results = case_result["results"]
        if results and "analysis" in results[-1]:
            final_result = results[-1]["analysis"]
            risk_level = final_result["risk_level"]
            category = final_result.get("category", "unknown")

            risk_counts[risk_level] = risk_counts.get(risk_level, 0) + 1
            category_counts[category] = category_counts.get(category, 0) + 1

    print(f"\n위험도 분포:")
    for level, count in risk_counts.items():
        print(f"  {level}: {count}개")

    print(f"\n카테고리 분포:")
    for category, count in sorted(category_counts.items()):
        print(f"  {category}: {count}개")

    # Grafana 메트릭 업데이트
    metrics_data = update_grafana_metrics(all_results)

    # 결과 저장
    output_path = Path(__file__).parent / "agent_b_test_results.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump({
            "test_date": datetime.now().isoformat(),
            "total_cases": len(all_results),
            "results": all_results,
            "metrics": metrics_data
        }, f, indent=2, ensure_ascii=False)

    print(f"\n테스트 결과가 {output_path}에 저장되었습니다.")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
