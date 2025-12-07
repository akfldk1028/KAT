"""
Scam Checker - 사기 신고 DB 조회 모듈
계좌번호/전화번호로 신고 이력을 확인

실제 운영 환경에서는 경찰청/금감원 API와 연동
현재는 Mock DB (scam_db.json) + TheCheat API 병행 사용
"""
import json
import re
from pathlib import Path
from typing import Dict, Any, Optional, List

# TheCheat API 통합
try:
    from .thecheat_api import check_phone_thecheat, check_account_thecheat
    THECHEAT_AVAILABLE = True
except ImportError:
    THECHEAT_AVAILABLE = False
    print("[ScamChecker] TheCheat API 모듈을 찾을 수 없습니다. Mock DB만 사용합니다.")


# 데이터 로드
_DATA_DIR = Path(__file__).parent.parent / "data"
_scam_db: Optional[Dict] = None


def _load_scam_db() -> Dict:
    """사기 신고 DB 로드 (lazy loading)"""
    global _scam_db
    if _scam_db is None:
        db_path = _DATA_DIR / "scam_db.json"
        if db_path.exists():
            with open(db_path, "r", encoding="utf-8") as f:
                _scam_db = json.load(f)
        else:
            _scam_db = {"reported_accounts": {"data": []}, "reported_phones": {"data": []}}
    return _scam_db


def normalize_account_number(account: str) -> str:
    """계좌번호 정규화 (하이픈 제거)"""
    return re.sub(r'[-\s]', '', account)


def normalize_phone_number(phone: str) -> str:
    """전화번호 정규화 (하이픈 제거)"""
    return re.sub(r'[-\s]', '', phone)


def check_reported_account(account_number: str) -> Dict[str, Any]:
    """
    계좌번호 신고 이력 조회 (Mock DB + TheCheat API 병행)

    Args:
        account_number: 조회할 계좌번호

    Returns:
        is_reported: 신고 여부
        report_info: 신고 정보 (있는 경우)
        risk_score: 위험 점수 (0-100)
        recommended_action: 권장 조치
        sources: 조회된 소스 목록 ["MockDB", "TheCheat"]
    """
    normalized = normalize_account_number(account_number)
    sources = []

    # 1. Mock DB 조회
    db = _load_scam_db()
    mock_result = None

    for record in db.get("reported_accounts", {}).get("data", []):
        record_normalized = normalize_account_number(record["account_number"])
        if record_normalized == normalized:
            status_info = db.get("status_definitions", {}).get(record["status"], {})
            mock_result = {
                "is_reported": True,
                "report_info": {
                    "account_number": record["account_number"],
                    "bank": record.get("bank", "알 수 없음"),
                    "report_count": record["report_count"],
                    "report_type": record["report_type"],
                    "status": record["status"],
                    "status_name_ko": status_info.get("name_ko", record["status"]),
                    "last_reported": record.get("last_reported", ""),
                    "source": "MockDB"
                },
                "risk_score": record["risk_score"],
                "recommended_action": status_info.get("action", "warn")
            }
            sources.append("MockDB")
            break

    # 2. TheCheat API 조회
    thecheat_result = None
    if THECHEAT_AVAILABLE:
        try:
            tc_data = check_account_thecheat(account_number)
            if tc_data and tc_data.get("is_reported"):
                thecheat_result = {
                    "is_reported": True,
                    "report_info": {
                        "account_number": tc_data.get("keyword", account_number),
                        "bank": "알 수 없음",
                        "report_count": 1,  # TheCheat API는 count 미제공
                        "report_type": "fraud",
                        "status": "reported",
                        "status_name_ko": "사기 신고됨 (TheCheat)",
                        "last_reported": tc_data.get("reported_date", ""),
                        "details": tc_data.get("details", ""),
                        "source": "TheCheat"
                    },
                    "risk_score": 95,  # TheCheat 신고건은 고위험으로 판정
                    "recommended_action": "block_and_report"
                }
                sources.append("TheCheat")
        except Exception as e:
            print(f"[ScamChecker] TheCheat API 계좌 조회 실패: {e}")

    # 3. 결과 병합 (TheCheat 우선)
    if thecheat_result:
        thecheat_result["sources"] = sources
        return thecheat_result
    elif mock_result:
        mock_result["sources"] = sources
        return mock_result
    else:
        return {
            "is_reported": False,
            "report_info": None,
            "risk_score": 0,
            "recommended_action": "none",
            "sources": []
        }


def check_reported_phone(phone_number: str) -> Dict[str, Any]:
    """
    전화번호 신고 이력 조회 (Mock DB + TheCheat API 병행)

    Args:
        phone_number: 조회할 전화번호

    Returns:
        is_reported: 신고 여부
        report_info: 신고 정보 (있는 경우)
        risk_score: 위험 점수 (0-100)
        recommended_action: 권장 조치
        sources: 조회된 소스 목록 ["MockDB", "TheCheat"]
    """
    normalized = normalize_phone_number(phone_number)
    sources = []

    # 1. Mock DB 조회
    db = _load_scam_db()
    mock_result = None

    for record in db.get("reported_phones", {}).get("data", []):
        record_normalized = normalize_phone_number(record["phone_number"])
        if record_normalized == normalized:
            status_info = db.get("status_definitions", {}).get(record["status"], {})
            mock_result = {
                "is_reported": True,
                "report_info": {
                    "phone_number": record["phone_number"],
                    "report_count": record["report_count"],
                    "report_type": record["report_type"],
                    "caller_claim": record.get("caller_claim", ""),
                    "status": record["status"],
                    "status_name_ko": status_info.get("name_ko", record["status"]),
                    "last_reported": record.get("last_reported", ""),
                    "source": "MockDB"
                },
                "risk_score": record["risk_score"],
                "recommended_action": status_info.get("action", "warn")
            }
            sources.append("MockDB")
            break

    # 2. TheCheat API 조회
    thecheat_result = None
    if THECHEAT_AVAILABLE:
        try:
            tc_data = check_phone_thecheat(phone_number)
            if tc_data and tc_data.get("is_reported"):
                thecheat_result = {
                    "is_reported": True,
                    "report_info": {
                        "phone_number": tc_data.get("keyword", phone_number),
                        "report_count": 1,  # TheCheat API는 count 미제공
                        "report_type": "fraud",
                        "caller_claim": "",
                        "status": "reported",
                        "status_name_ko": "사기 신고됨 (TheCheat)",
                        "last_reported": tc_data.get("reported_date", ""),
                        "details": tc_data.get("details", ""),
                        "source": "TheCheat"
                    },
                    "risk_score": 95,  # TheCheat 신고건은 고위험으로 판정
                    "recommended_action": "block_and_report"
                }
                sources.append("TheCheat")
        except Exception as e:
            print(f"[ScamChecker] TheCheat API 전화번호 조회 실패: {e}")

    # 3. 결과 병합 (TheCheat 우선)
    if thecheat_result:
        thecheat_result["sources"] = sources
        return thecheat_result
    elif mock_result:
        mock_result["sources"] = sources
        return mock_result
    else:
        return {
            "is_reported": False,
            "report_info": None,
            "risk_score": 0,
            "recommended_action": "none",
            "sources": []
        }


def extract_identifiers_from_text(text: str) -> Dict[str, List[str]]:
    """
    텍스트에서 계좌번호와 전화번호 추출

    Args:
        text: 분석할 텍스트

    Returns:
        accounts: 추출된 계좌번호 목록
        phones: 추출된 전화번호 목록
    """
    # 계좌번호 패턴 (3-4자리-2-6자리-6-7자리)
    account_patterns = [
        r'\d{3,4}[-\s]?\d{2,6}[-\s]?\d{6,7}',  # 일반적인 계좌번호
        r'\d{11,14}',  # 하이픈 없는 계좌번호
    ]

    # 전화번호 패턴
    phone_patterns = [
        r'010[-\s]?\d{4}[-\s]?\d{4}',  # 휴대폰
        r'02[-\s]?\d{3,4}[-\s]?\d{4}',  # 서울
        r'0\d{1,2}[-\s]?\d{3,4}[-\s]?\d{4}',  # 지역번호
        r'070[-\s]?\d{4}[-\s]?\d{4}',  # 인터넷전화
    ]

    accounts = []
    phones = []

    for pattern in account_patterns:
        matches = re.findall(pattern, text)
        accounts.extend(matches)

    for pattern in phone_patterns:
        matches = re.findall(pattern, text)
        phones.extend(matches)

    # 중복 제거 및 정규화
    accounts = list(set(normalize_account_number(a) for a in accounts))
    phones = list(set(normalize_phone_number(p) for p in phones))

    # 전화번호로 잘못 잡힌 계좌번호 필터링 (010으로 시작하면 전화번호)
    accounts = [a for a in accounts if not a.startswith('010')]

    return {
        "accounts": accounts,
        "phones": phones
    }


def check_scam_in_message(text: str) -> Dict[str, Any]:
    """
    메시지 내 계좌번호/전화번호의 신고 이력 일괄 조회

    Args:
        text: 분석할 메시지

    Returns:
        has_reported_identifier: 신고된 식별자 포함 여부
        reported_accounts: 신고된 계좌 정보
        reported_phones: 신고된 전화번호 정보
        max_risk_score: 최대 위험 점수
        recommended_action: 권장 조치
    """
    identifiers = extract_identifiers_from_text(text)

    reported_accounts = []
    reported_phones = []
    max_risk_score = 0
    recommended_action = "none"

    # 계좌번호 조회
    for account in identifiers["accounts"]:
        result = check_reported_account(account)
        if result["is_reported"]:
            reported_accounts.append(result["report_info"])
            if result["risk_score"] > max_risk_score:
                max_risk_score = result["risk_score"]
                recommended_action = result["recommended_action"]

    # 전화번호 조회
    for phone in identifiers["phones"]:
        result = check_reported_phone(phone)
        if result["is_reported"]:
            reported_phones.append(result["report_info"])
            if result["risk_score"] > max_risk_score:
                max_risk_score = result["risk_score"]
                recommended_action = result["recommended_action"]

    return {
        "has_reported_identifier": len(reported_accounts) > 0 or len(reported_phones) > 0,
        "extracted_identifiers": identifiers,
        "reported_accounts": reported_accounts,
        "reported_phones": reported_phones,
        "max_risk_score": max_risk_score,
        "recommended_action": recommended_action
    }
