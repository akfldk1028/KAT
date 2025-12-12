"""
LRL.kr URL 안전검사 API Client - URL 위협 탐지 모듈
LRL.kr API를 활용하여 URL의 안전성을 검사합니다.

API 문서: https://api.lrl.kr/v5/url/check

환경변수:
- LRL_API_KEY: LRL API 인증 키
"""
import os
import requests
from typing import Dict, Any, Optional


class LRLAPIError(Exception):
    """LRL API 에러"""
    pass


class LRLClient:
    """LRL URL 안전검사 API 클라이언트"""

    def __init__(self, api_key: str = None):
        """
        LRL API 클라이언트 초기화

        Args:
            api_key: API 인증 키 (없으면 환경변수 LRL_API_KEY 사용)

        Raises:
            LRLAPIError: API 키가 없는 경우
        """
        self.api_key = api_key or os.getenv("LRL_API_KEY")
        if not self.api_key:
            raise LRLAPIError("LRL_API_KEY 환경변수가 설정되지 않았습니다")

        self.endpoint = "https://api.lrl.kr/v5/url/check"

    def check_url(self, url: str) -> Dict[str, Any]:
        """
        URL 안전성 검사 (GET 방식 - 공식 문서 예제)

        Args:
            url: 검사할 URL

        Returns:
            is_safe: 안전 여부 (bool)
            threat: 위협 유형 (MALWARE, SOCIAL_ENGINEERING, UNWANTED_SOFTWARE, etc.)
            url: 검사된 URL
            source: "LRL"

        Raises:
            LRLAPIError: API 호출 실패 시
        """
        # GET 방식으로 호출 (공식 문서 예제)
        # https://api.lrl.kr/v5/url/check?key=API_KEY&url=검사URL
        params = {
            "key": self.api_key,
            "url": url
        }

        try:
            response = requests.get(
                self.endpoint,
                params=params,
                timeout=10
            )

            result = response.json()

            # HTTP 상태 코드별 처리
            if response.status_code == 201:
                # 성공
                pass
            elif response.status_code == 400:
                raise LRLAPIError("잘못된 요청 (HTTP 400)")
            elif response.status_code == 401:
                raise LRLAPIError("API 키 누락 또는 불일치 (HTTP 401)")
            elif response.status_code == 403:
                # ERR_INVALID_KEY 등
                msg = result.get("message", "접근 불가")
                raise LRLAPIError(f"API 키 오류: {msg} (HTTP 403)")
            elif response.status_code == 500:
                raise LRLAPIError("서버 오류 (HTTP 500)")

        except requests.exceptions.Timeout:
            raise LRLAPIError("API 요청 타임아웃 (10초 초과)")
        except requests.exceptions.RequestException as e:
            raise LRLAPIError(f"API 요청 실패: {str(e)}")
        except ValueError:
            raise LRLAPIError("API 응답 JSON 파싱 실패")

        # 응답 메시지 확인
        message = result.get("message", "")
        if message == "ERR_INVALID_KEY":
            raise LRLAPIError("API 키가 유효하지 않습니다. https://api.lrl.kr 에서 키 상태를 확인하세요.")
        if message == "ERR_NO_URL":
            raise LRLAPIError("URL 값이 누락되었습니다.")
        if message != "SUCCESS":
            raise LRLAPIError(f"API 응답 에러: {message}")

        # 결과 파싱
        result_data = result.get("result", {})
        safe_status = result_data.get("safe", "1")
        threat_type = result_data.get("threat", "")

        return {
            "is_safe": safe_status == "1",
            "threat": threat_type,
            "url": url,
            "source": "LRL"
        }


# Singleton 패턴 - 글로벌 클라이언트 인스턴스
_client: Optional[LRLClient] = None


def get_lrl_client() -> Optional[LRLClient]:
    """
    LRL 클라이언트 인스턴스 반환 (Lazy Loading)

    Returns:
        LRLClient 인스턴스 또는 None (API Key 없는 경우)
    """
    global _client

    if _client is None:
        if os.getenv("LRL_API_KEY"):
            try:
                _client = LRLClient()
                print("[LRL] API 클라이언트 초기화 완료")
            except LRLAPIError as e:
                print(f"[LRL] 초기화 실패: {e}")
                return None
        else:
            print("[LRL] LRL_API_KEY 환경변수가 설정되지 않았습니다.")
            return None

    return _client


def check_url_lrl(url: str) -> Optional[Dict]:
    """
    LRL API로 URL 안전성 검사 (Wrapper Function)

    Args:
        url: 검사할 URL

    Returns:
        검사 결과 또는 None (API 사용 불가 또는 에러 시)
    """
    client = get_lrl_client()
    if not client:
        return None

    try:
        result = client.check_url(url)
        print(f"[LRL] URL 검사 성공: {url} → safe={result.get('is_safe')}, threat={result.get('threat')}")
        return result
    except LRLAPIError as e:
        print(f"[LRL] URL 검사 실패: {url} → {e}")
        return None
