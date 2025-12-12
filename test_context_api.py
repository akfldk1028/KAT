# -*- coding: utf-8 -*-
"""
ver9.0 대화 맥락 기반 API 테스트
실제 API를 호출하여 대화 흐름에서 사기 패턴을 감지하는지 테스트
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import requests
import json
import time

API_URL = "http://localhost:8002/api/agents/analyze/incoming"

# ver9.0 카테고리별 테스트 시나리오
TEST_SCENARIOS = {
    "A-1": {
        "name": "지인/가족 사칭",
        "expected_category": "A-1",
        "conversation": [
            {"role": "incoming", "content": "엄마야?"},
            {"role": "outgoing", "content": "응? 누구야?"},
            {"role": "incoming", "content": "나 폰 바꿨어"},
            {"role": "incoming", "content": "폰 액정이 깨져서 수리 맡겼거든"},
            {"role": "incoming", "content": "급하게 인증해야 하는데 인증번호 좀 받아줘"}
        ]
    },
    "A-2": {
        "name": "경조사 빙자",
        "expected_category": "A-2",
        "conversation": [
            {"role": "incoming", "content": "[모바일 청첩장] 결혼식에 초대합니다"},
            {"role": "incoming", "content": "일시: 12월 25일 오후 2시"},
            {"role": "incoming", "content": "식장 약도 및 참석 확인: bit.ly/wedding123"}
        ]
    },
    "A-3": {
        "name": "로맨스 스캠",
        "expected_category": "A-3",
        "conversation": [
            {"role": "incoming", "content": "자기야 보고싶어"},
            {"role": "outgoing", "content": "나도~"},
            {"role": "incoming", "content": "내가 한국으로 선물 보냈는데"},
            {"role": "incoming", "content": "세관에 걸려서 통관비 500만원이 필요해"},
            {"role": "incoming", "content": "다음달에 꼭 갚을게 honey"}
        ]
    },
    "B-1": {
        "name": "수사/금융 기관 사칭",
        "expected_category": "B-1",
        "conversation": [
            {"role": "incoming", "content": "검찰청에서 연락드립니다"},
            {"role": "incoming", "content": "귀하의 계좌가 범죄에 연루되어 수사 중입니다"},
            {"role": "incoming", "content": "즉시 안전계좌로 자금을 이체해야 합니다"},
            {"role": "incoming", "content": "지금 당장 협조해주셔야 합니다"}
        ]
    },
    "B-2": {
        "name": "공공 행정 알림 사칭",
        "expected_category": "B-2",
        "conversation": [
            {"role": "incoming", "content": "[국민건강보험] 건강검진 결과 안내"},
            {"role": "incoming", "content": "검진 결과 확인이 필요합니다"},
            {"role": "incoming", "content": "결과 확인: bit.ly/nhis-result"}
        ]
    },
    "B-3": {
        "name": "택배/물류 사칭",
        "expected_category": "B-3",
        "conversation": [
            {"role": "incoming", "content": "[CJ대한통운] 택배 배송 안내"},
            {"role": "incoming", "content": "운송장번호 주소 불일치로 배송 보류"},
            {"role": "incoming", "content": "주소 수정: bit.ly/cj-delivery"}
        ]
    },
    "C-1": {
        "name": "대출 빙자",
        "expected_category": "C-1",
        "conversation": [
            {"role": "incoming", "content": "[XX캐피탈] 정부지원 저금리 대출 안내"},
            {"role": "incoming", "content": "신용등급 무관 최대 5천만원 대출 가능"},
            {"role": "incoming", "content": "보증료만 입금하시면 즉시 대출 실행됩니다"}
        ]
    },
    "C-2": {
        "name": "투자 리딩방",
        "expected_category": "C-2",
        "conversation": [
            {"role": "incoming", "content": "주식리딩방 무료 체험 안내"},
            {"role": "incoming", "content": "이번에 세력 매집주 정보 입수했습니다"},
            {"role": "incoming", "content": "300% 수익 보장합니다"},
            {"role": "incoming", "content": "선착순 VIP방 들어오세요"}
        ]
    },
    "C-3": {
        "name": "몸캠 피싱",
        "expected_category": "C-3",
        "conversation": [
            {"role": "incoming", "content": "오빠 영상통화 하자"},
            {"role": "incoming", "content": "얼굴 보고싶어"},
            {"role": "outgoing", "content": "그래"},
            {"role": "incoming", "content": "어 소리가 안 들려"},
            {"role": "incoming", "content": "이 앱 깔면 화질도 좋아. 이거 깔고 다시 하자"},
            {"role": "incoming", "content": "링크로 들어와서 설치해 xxx.apk"}
        ]
    },
    "NORMAL": {
        "name": "일반 대화",
        "expected_category": "NORMAL",
        "conversation": [
            {"role": "incoming", "content": "오늘 저녁 뭐 먹을까?"},
            {"role": "outgoing", "content": "뭐 먹고 싶어?"},
            {"role": "incoming", "content": "치킨 먹고 싶다"},
            {"role": "outgoing", "content": "그럼 치킨 시키자"}
        ]
    }
}

def test_scenario(scenario_id, scenario):
    """단일 시나리오 테스트"""
    print(f"\n{'='*70}")
    print(f"[{scenario_id}] {scenario['name']}")
    print(f"{'='*70}")

    # 대화 내용 출력
    print("\n대화 내용:")
    for msg in scenario['conversation']:
        role = "발신" if msg['role'] == 'outgoing' else "수신"
        print(f"  [{role}] {msg['content']}")

    # API 호출
    last_incoming = None
    for msg in reversed(scenario['conversation']):
        if msg['role'] == 'incoming':
            last_incoming = msg['content']
            break

    # ConversationMessage 형식으로 변환
    # sender_id: 1=발신자(상대), 2=수신자(나)
    conversation_history = []
    for msg in scenario['conversation']:
        conversation_history.append({
            "sender_id": 1 if msg['role'] == 'incoming' else 2,
            "message": msg['content'],
            "timestamp": None
        })

    payload = {
        "text": last_incoming,
        "conversation_history": conversation_history,
        "sender_id": 1,
        "receiver_id": 2,
        "use_ai": True
    }

    try:
        start_time = time.time()
        response = requests.post(API_URL, json=payload, timeout=60)
        elapsed = time.time() - start_time

        if response.status_code == 200:
            result = response.json()

            print(f"\n분석 결과 (소요시간: {elapsed:.2f}s):")
            print(f"  위험도: {result.get('risk_level', 'N/A')}")
            print(f"  확률: {result.get('probability', 0)}%")
            print(f"  카테고리: {result.get('category', 'N/A')}")
            print(f"  요약: {result.get('summary', 'N/A')}")

            # Stage 결과
            if 'stage_results' in result:
                print(f"\n  Stage 결과:")
                for stage, stage_result in result['stage_results'].items():
                    print(f"    {stage}: {stage_result}")

            # 예상 결과와 비교
            expected = scenario['expected_category']
            actual = result.get('category', 'N/A')

            # NORMAL의 경우 risk_level로 판단
            if expected == "NORMAL":
                is_safe = result.get('risk_level') in ['safe', 'low'] or result.get('probability', 100) < 40
                status = "PASS" if is_safe else "FAIL"
            else:
                status = "PASS" if actual == expected else "PARTIAL" if actual.startswith(expected[0]) else "FAIL"

            print(f"\n  예상: {expected} | 실제: {actual} | 결과: {status}")

            return {
                "scenario_id": scenario_id,
                "name": scenario['name'],
                "expected": expected,
                "actual": actual,
                "probability": result.get('probability', 0),
                "risk_level": result.get('risk_level', 'N/A'),
                "elapsed": elapsed,
                "status": status
            }
        else:
            print(f"\n  API 오류: {response.status_code}")
            print(f"  응답: {response.text[:200]}")
            return {
                "scenario_id": scenario_id,
                "name": scenario['name'],
                "expected": scenario['expected_category'],
                "actual": "ERROR",
                "status": "ERROR"
            }
    except Exception as e:
        print(f"\n  예외 발생: {e}")
        return {
            "scenario_id": scenario_id,
            "name": scenario['name'],
            "expected": scenario['expected_category'],
            "actual": "EXCEPTION",
            "status": "ERROR"
        }

def main():
    print("="*70)
    print("ver9.0 대화 맥락 기반 API 테스트")
    print("="*70)

    # 서버 상태 확인
    try:
        health = requests.get("http://localhost:8002/api/agents/health", timeout=5)
        print(f"\n서버 상태: {health.json()}")
    except Exception as e:
        print(f"\n서버 연결 실패: {e}")
        return

    results = []

    for scenario_id, scenario in TEST_SCENARIOS.items():
        result = test_scenario(scenario_id, scenario)
        results.append(result)
        time.sleep(1)  # API 부하 방지

    # 결과 요약
    print("\n" + "="*70)
    print("테스트 결과 요약")
    print("="*70)
    print(f"{'ID':<8} {'이름':<20} {'예상':<10} {'실제':<10} {'확률':<8} {'상태':<8}")
    print("-"*70)

    pass_count = 0
    for r in results:
        prob = f"{r.get('probability', 0)}%" if r.get('probability') else "N/A"
        print(f"{r['scenario_id']:<8} {r['name']:<20} {r['expected']:<10} {r.get('actual', 'N/A'):<10} {prob:<8} {r['status']:<8}")
        if r['status'] == 'PASS':
            pass_count += 1

    print("-"*70)
    print(f"총 {len(results)}개 중 {pass_count}개 통과 ({pass_count/len(results)*100:.1f}%)")

if __name__ == "__main__":
    main()
