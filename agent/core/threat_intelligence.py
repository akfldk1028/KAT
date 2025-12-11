"""
Threat Intelligence - 통합 위협 정보 조회 모듈
모든 외부 위협 정보 소스를 통합하여 단일 인터페이스 제공

통합 소스:
- TheCheat API: 전화번호/계좌번호 사기 신고 조회
- KISA Phishing API: 피싱 사이트 URL 조회 (로컬 캐시, 1순위)
- VirusTotal API: URL/파일 악성코드 검사 (2순위)

참고:
- lrl.kr v6 API는 URL 안전검사 미지원 (URL 단축만 가능)
- lrl.kr v5 URL 체크는 별도 키 필요 (현재 미사용)

사용 패턴:
1. ThreatIntelligence 클래스: 전체 통합 조회
2. check_identifier() 함수: Hybrid Agent용 단일 식별자 조회
"""
import re
from typing import Dict, Any, Optional, List
from urllib.parse import urlparse

# 개별 API 클라이언트 import
from .thecheat_api import check_phone_thecheat, check_account_thecheat
from .kisa_phishing_api import check_url_kisa
from .virustotal_api import check_url_virustotal
# lrl.kr v6는 URL 체크 미지원 (URL 단축만 가능)
# from .lrl_api import check_url_lrl


class ThreatIntelligence:
    """
    통합 위협 정보 조회 클래스

    모든 외부 위협 정보 소스를 통합하여 제공합니다.
    """

    def __init__(self):
        """ThreatIntelligence 초기화"""
        pass

    def check_phone(self, phone: str) -> Dict[str, Any]:
        """
        전화번호 조회 (TheCheat API)

        Args:
            phone: 조회할 전화번호

        Returns:
            has_reported: 신고 여부 (bool)
            source: 조회된 소스 ("TheCheat" | None)
            report_count: 신고 건수 (int, 기본값 1)
            prior_probability: 사전 확률 (float)
            details: 상세 정보 (Dict)
        """
        result = check_phone_thecheat(phone)

        if result and result.get("is_reported"):
            # TheCheat API는 report_count를 제공하지 않으므로 기본값 1 사용
            report_count = 1

            return {
                "has_reported": True,
                "source": "TheCheat",
                "report_count": report_count,
                "prior_probability": calculate_prior_probability(report_count),
                "details": {
                    "phone_number": result.get("keyword", phone),
                    "reported_date": result.get("reported_date", ""),
                    "caution": result.get("caution", "N"),
                    "content": result.get("details", "")
                }
            }
        else:
            return {
                "has_reported": False,
                "source": None,
                "report_count": 0,
                "prior_probability": 0.0,
                "details": {}
            }

    def check_account(self, account: str, bank_code: str = None) -> Dict[str, Any]:
        """
        계좌번호 조회 (TheCheat API)

        Args:
            account: 조회할 계좌번호
            bank_code: 은행 코드 (선택)

        Returns:
            has_reported: 신고 여부 (bool)
            source: 조회된 소스 ("TheCheat" | None)
            report_count: 신고 건수 (int, 기본값 1)
            prior_probability: 사전 확률 (float)
            details: 상세 정보 (Dict)
        """
        result = check_account_thecheat(account, bank_code)

        if result and result.get("is_reported"):
            # TheCheat API는 report_count를 제공하지 않으므로 기본값 1 사용
            report_count = 1

            return {
                "has_reported": True,
                "source": "TheCheat",
                "report_count": report_count,
                "prior_probability": calculate_prior_probability(report_count),
                "details": {
                    "account_number": result.get("keyword", account),
                    "bank_code": bank_code,
                    "reported_date": result.get("reported_date", ""),
                    "caution": result.get("caution", "N"),
                    "content": result.get("details", "")
                }
            }
        else:
            return {
                "has_reported": False,
                "source": None,
                "report_count": 0,
                "prior_probability": 0.0,
                "details": {}
            }

    def check_url(self, url: str) -> Dict[str, Any]:
        """
        URL 조회 (KISA 캐시 → VirusTotal 순차)

        폴백 전략:
        1. KISA 피싱사이트 로컬 캐시 조회 (빠름, O(1))
        2. VirusTotal API 조회 (느림, 정밀)

        참고: lrl.kr v6는 URL 체크 미지원 (v5 전용키 필요)

        Args:
            url: 조회할 URL

        Returns:
            has_reported: 위협 URL 여부 (bool)
            source: 조회된 소스 ("KISA" | "VirusTotal" | None)
            report_count: 신고/탐지 건수 (VirusTotal인 경우 malicious_count)
            prior_probability: 사전 확률 (float)
            threat_type: 위협 유형 ("phishing" | "malware" | "safe" | "suspicious")
            details: 상세 정보 (Dict)
        """
        # 1. KISA 피싱사이트 캐시 조회 (1순위, O(1) 검색)
        kisa_result = check_url_kisa(url)
        if kisa_result:
            if kisa_result.get("is_phishing"):
                return {
                    "has_reported": True,
                    "source": "KISA",
                    "report_count": 1,
                    "prior_probability": calculate_prior_probability(1),
                    "threat_type": "phishing",
                    "details": {
                        "matched_url": kisa_result.get("matched_url", url),
                        "reported_date": kisa_result.get("reported_date", "")
                    }
                }

        # 2. VirusTotal 조회 (2순위, 정밀 검사)
        vt_result = check_url_virustotal(url)
        if vt_result:
            malicious_count = vt_result.get("malicious", 0)
            suspicious_count = vt_result.get("suspicious", 0)
            is_malicious = vt_result.get("is_malicious", False)

            # 악성 또는 의심 판정
            if is_malicious or suspicious_count > 0:
                # report_count는 악성 판정 엔진 수로 간주
                report_count = max(malicious_count, 1)

                # 위협 유형 결정
                threat_type = "malware" if malicious_count > 0 else "suspicious"

                return {
                    "has_reported": True,
                    "source": "VirusTotal",
                    "report_count": report_count,
                    "prior_probability": calculate_prior_probability(report_count),
                    "threat_type": threat_type,
                    "details": {
                        "malicious": malicious_count,
                        "suspicious": suspicious_count,
                        "harmless": vt_result.get("harmless", 0),
                        "undetected": vt_result.get("undetected", 0),
                        "total_engines": vt_result.get("total_engines", 0)
                    }
                }
            else:
                # 안전함
                return {
                    "has_reported": False,
                    "source": "VirusTotal",
                    "report_count": 0,
                    "prior_probability": 0.0,
                    "threat_type": "safe",
                    "details": {
                        "total_engines": vt_result.get("total_engines", 0),
                        "harmless": vt_result.get("harmless", 0),
                        "undetected": vt_result.get("undetected", 0)
                    }
                }

        # 모든 조회 실패 또는 API 사용 불가
        return {
            "has_reported": False,
            "source": None,
            "report_count": 0,
            "prior_probability": 0.0,
            "threat_type": "unknown",
            "details": {"error": "No threat intelligence source available"}
        }

    def check_identifier(self, identifier: str, type: str) -> Dict[str, Any]:
        """
        통합 조회 (Hybrid Agent용)

        단일 식별자(전화번호/URL/계좌번호)를 type에 따라 적절한 소스에서 조회합니다.

        Args:
            identifier: 조회할 식별자 (전화번호, URL, 계좌번호)
            type: 식별자 타입 ("phone" | "url" | "account")

        Returns:
            has_reported: 신고/위협 여부 (bool)
            source: 조회된 소스 (str | None)
            report_count: 신고 건수 (int)
            prior_probability: 사전 확률 (float)
            threat_type: 위협 유형 (str, URL인 경우만)
            details: 상세 정보 (Dict)

        Raises:
            ValueError: type이 잘못된 경우
        """
        if type == "phone":
            return self.check_phone(identifier)
        elif type == "url":
            return self.check_url(identifier)
        elif type == "account":
            return self.check_account(identifier)
        else:
            raise ValueError(f"Invalid type: {type}. Must be 'phone', 'url', or 'account'")


def calculate_prior_probability(report_count: int) -> float:
    """
    사전 확률 계산: report_count / (report_count + 100)

    베이지안 추론에서 사용할 사전 확률을 계산합니다.
    - 신고 건수가 많을수록 높은 확률 (최대 1.0)
    - 신고 건수가 0이면 0.0
    - 100건 기준으로 정규화 (100건 = 0.5)

    Args:
        report_count: 신고 건수 (int, >= 0)

    Returns:
        사전 확률 (0.0 ~ 1.0)

    Examples:
        calculate_prior_probability(0) → 0.0
        calculate_prior_probability(1) → 0.0099 (약 1%)
        calculate_prior_probability(10) → 0.0909 (약 9%)
        calculate_prior_probability(100) → 0.5 (50%)
        calculate_prior_probability(1000) → 0.909 (약 91%)
    """
    if report_count < 0:
        report_count = 0

    return report_count / (report_count + 100)


# ============================================================
# 편의 함수 (Wrapper)
# ============================================================

def check_identifier(identifier: str, type: str) -> Dict[str, Any]:
    """
    통합 조회 (함수형 인터페이스)

    ThreatIntelligence 클래스를 사용하지 않고 직접 호출할 수 있는 함수입니다.

    Args:
        identifier: 조회할 식별자
        type: 식별자 타입 ("phone" | "url" | "account")

    Returns:
        ThreatIntelligence.check_identifier() 결과
    """
    ti = ThreatIntelligence()
    return ti.check_identifier(identifier, type)
