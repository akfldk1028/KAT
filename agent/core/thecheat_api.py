"""
TheCheat API Client - 외부 사기 신고 DB 조회 모듈
TheCheat API를 활용하여 전화번호/계좌번호의 사기 이력을 조회합니다.

API 문서: https://apidocs.thecheat.co.kr/docs/api-usage/api-common
테스트 가이드: https://apidocs.thecheat.co.kr/docs/api-usage/api-search-guide

환경변수:
- THECHEAT_API_KEY: TheCheat API 인증 키
- THECHEAT_BASE_URL: API 베이스 URL (기본: https://api.thecheat.co.kr)
"""
import os
import re
import requests
from typing import Dict, Any, Optional


class TheCheatAPIError(Exception):
    """TheCheat API 에러"""
    pass


class TheCheatClient:
    """TheCheat 사기조회 API 클라이언트"""

    def __init__(self, api_key: str = None, base_url: str = None):
        """
        TheCheat API 클라이언트 초기화

        Args:
            api_key: API 인증 키 (없으면 환경변수 THECHEAT_API_KEY 사용)
            base_url: API 베이스 URL (없으면 환경변수 또는 기본값 사용)

        Raises:
            TheCheatAPIError: API 키가 없는 경우
        """
        self.api_key = api_key or os.getenv("THECHEAT_API_KEY")
        if not self.api_key:
            raise TheCheatAPIError("THECHEAT_API_KEY 환경변수가 설정되지 않았습니다")

        self.base_url = (base_url or os.getenv("THECHEAT_BASE_URL", "https://api.thecheat.co.kr")).rstrip("/")
        self.endpoint = f"{self.base_url}/api/v2/fraud/search"

    def _normalize_phone(self, phone: str) -> str:
        """전화번호 정규화 (하이픈, 공백 제거)"""
        return re.sub(r'[-\s]', '', phone)

    def _normalize_account(self, account: str) -> str:
        """계좌번호 정규화 (하이픈, 공백 제거)"""
        return re.sub(r'[-\s]', '', account)

    def _request(self, keyword_type: str, keyword: str, bank_code: str = None) -> Dict:
        """
        TheCheat API 호출

        Args:
            keyword_type: "phone" 또는 "account"
            keyword: 조회할 전화번호 또는 계좌번호 (숫자만)
            bank_code: 은행 코드 (계좌번호 조회 시 선택)

        Returns:
            API 응답 data 필드

        Raises:
            TheCheatAPIError: API 호출 실패 시
        """
        headers = {
            "X-TheCheat-ApiKey": self.api_key,
            "Content-Type": "application/json"
        }

        payload = {
            "keyword_type": keyword_type,
            "keyword": keyword
        }

        if bank_code:
            payload["bank_code"] = bank_code

        try:
            response = requests.post(
                self.endpoint,
                headers=headers,
                json=payload,
                timeout=10
            )
            response.raise_for_status()
            result = response.json()
        except requests.exceptions.Timeout:
            raise TheCheatAPIError("API 요청 타임아웃 (10초 초과)")
        except requests.exceptions.RequestException as e:
            raise TheCheatAPIError(f"API 요청 실패: {str(e)}")
        except ValueError:
            raise TheCheatAPIError("API 응답 JSON 파싱 실패")

        # 에러 코드 처리
        result_code = result.get("result_code")

        if result_code == 1:
            # 정상 응답
            return result.get("data", {})
        elif result_code == -1:
            raise TheCheatAPIError("서버 에러 (result_code: -1)")
        elif result_code == -2:
            raise TheCheatAPIError("유효하지 않은 API Key (result_code: -2)")
        elif result_code == -3:
            raise TheCheatAPIError("필수 파라미터 누락 (result_code: -3)")
        elif result_code == -4:
            raise TheCheatAPIError("허용되지 않은 IP (result_code: -4)")
        else:
            raise TheCheatAPIError(f"알 수 없는 에러 코드: {result_code}")

    def search_phone(self, phone_number: str) -> Dict[str, Any]:
        """
        전화번호 사기 이력 조회

        Args:
            phone_number: 조회할 전화번호 (하이픈 포함 가능)

        Returns:
            is_reported: 신고 여부 (bool)
            keyword: 조회된 전화번호
            reported_date: 신고 일시
            details: 신고 상세 내용
            source: "TheCheat"
        """
        normalized = self._normalize_phone(phone_number)

        try:
            data = self._request("phone", normalized)

            return {
                "is_reported": data.get("caution") == "Y",
                "keyword": data.get("keyword", normalized),
                "reported_date": data.get("created_date", ""),
                "details": data.get("content", ""),
                "caution": data.get("caution", "N"),
                "source": "TheCheat"
            }
        except TheCheatAPIError as e:
            # API 에러 시 None 반환하지 않고 예외 전파
            raise

    def search_account(self, account_number: str, bank_code: str = None) -> Dict[str, Any]:
        """
        계좌번호 사기 이력 조회

        Args:
            account_number: 조회할 계좌번호 (하이픈 포함 가능)
            bank_code: 은행 코드 (선택)

        Returns:
            is_reported: 신고 여부 (bool)
            keyword: 조회된 계좌번호
            reported_date: 신고 일시
            details: 신고 상세 내용
            source: "TheCheat"
        """
        normalized = self._normalize_account(account_number)

        try:
            data = self._request("account", normalized, bank_code)

            return {
                "is_reported": data.get("caution") == "Y",
                "keyword": data.get("keyword", normalized),
                "reported_date": data.get("created_date", ""),
                "details": data.get("content", ""),
                "caution": data.get("caution", "N"),
                "source": "TheCheat"
            }
        except TheCheatAPIError as e:
            # API 에러 시 None 반환하지 않고 예외 전파
            raise


# Singleton 패턴 - 글로벌 클라이언트 인스턴스
_client: Optional[TheCheatClient] = None


def get_thecheat_client() -> Optional[TheCheatClient]:
    """
    TheCheat 클라이언트 인스턴스 반환 (Lazy Loading)

    Returns:
        TheCheatClient 인스턴스 또는 None (API Key 없는 경우)
    """
    global _client

    if _client is None:
        if os.getenv("THECHEAT_API_KEY"):
            try:
                _client = TheCheatClient()
                print("[TheCheat] API 클라이언트 초기화 완료")
            except TheCheatAPIError as e:
                print(f"[TheCheat] 초기화 실패: {e}")
                return None
        else:
            print("[TheCheat] THECHEAT_API_KEY 환경변수가 설정되지 않았습니다. Mock DB만 사용합니다.")
            return None

    return _client


def check_phone_thecheat(phone_number: str) -> Optional[Dict]:
    """
    TheCheat API로 전화번호 조회 (Wrapper Function)

    Args:
        phone_number: 조회할 전화번호

    Returns:
        조회 결과 또는 None (API 사용 불가 또는 에러 시)
    """
    client = get_thecheat_client()
    if not client:
        return None

    try:
        result = client.search_phone(phone_number)
        print(f"[TheCheat] 전화번호 조회 성공: {phone_number} → caution={result.get('caution')}")
        return result
    except TheCheatAPIError as e:
        print(f"[TheCheat] 전화번호 조회 실패: {phone_number} → {e}")
        return None


def check_account_thecheat(account_number: str, bank_code: str = None) -> Optional[Dict]:
    """
    TheCheat API로 계좌번호 조회 (Wrapper Function)

    Args:
        account_number: 조회할 계좌번호
        bank_code: 은행 코드 (선택)

    Returns:
        조회 결과 또는 None (API 사용 불가 또는 에러 시)
    """
    client = get_thecheat_client()
    if not client:
        return None

    try:
        result = client.search_account(account_number, bank_code)
        print(f"[TheCheat] 계좌번호 조회 성공: {account_number} → caution={result.get('caution')}")
        return result
    except TheCheatAPIError as e:
        print(f"[TheCheat] 계좌번호 조회 실패: {account_number} → {e}")
        return None
