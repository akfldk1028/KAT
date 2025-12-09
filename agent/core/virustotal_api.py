"""
VirusTotal API Client - URL 악성코드 검사 모듈
VirusTotal API를 활용하여 URL의 악성 여부를 검사합니다.

API 문서: https://developers.virustotal.com/reference/urls

환경변수:
- VIRUSTOTAL_API_KEY: VirusTotal API 인증 키
"""
import os
import base64
import time
import requests
from typing import Dict, Any, Optional


class VirusTotalAPIError(Exception):
    """VirusTotal API 에러"""
    pass


class VirusTotalClient:
    """VirusTotal URL 검사 API 클라이언트"""

    def __init__(self, api_key: str = None):
        """
        VirusTotal API 클라이언트 초기화

        Args:
            api_key: API 인증 키 (없으면 환경변수 VIRUSTOTAL_API_KEY 사용)

        Raises:
            VirusTotalAPIError: API 키가 없는 경우
        """
        self.api_key = api_key or os.getenv("VIRUSTOTAL_API_KEY")
        if not self.api_key:
            raise VirusTotalAPIError("VIRUSTOTAL_API_KEY 환경변수가 설정되지 않았습니다")

        self.base_url = "https://www.virustotal.com/api/v3"
        self.last_request_time = 0
        self.min_interval = 15  # 무료 계정: 분당 4회 제한 (15초 간격)

    def _get_url_id(self, url: str) -> str:
        """
        URL을 VirusTotal URL ID로 변환

        Args:
            url: 검사할 URL

        Returns:
            base64로 인코딩된 URL ID (패딩 제거)
        """
        url_id = base64.urlsafe_b64encode(url.encode()).decode().strip("=")
        return url_id

    def _rate_limit_wait(self):
        """Rate limit 준수를 위한 대기"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_interval:
            wait_time = self.min_interval - elapsed
            print(f"[VirusTotal] Rate limit: {wait_time:.1f}초 대기 중...")
            time.sleep(wait_time)
        self.last_request_time = time.time()

    def check_url(self, url: str) -> Dict[str, Any]:
        """
        URL 악성 여부 검사

        Args:
            url: 검사할 URL

        Returns:
            malicious: 악성 판정 엔진 수
            suspicious: 의심 판정 엔진 수
            harmless: 무해 판정 엔진 수
            undetected: 미탐지 엔진 수
            total_engines: 전체 검사 엔진 수
            is_malicious: 악성 여부 (malicious > 0)
            url: 검사된 URL
            source: "VirusTotal"

        Raises:
            VirusTotalAPIError: API 호출 실패 시
        """
        # Rate limit 체크
        self._rate_limit_wait()

        url_id = self._get_url_id(url)
        endpoint = f"{self.base_url}/urls/{url_id}"

        headers = {
            "x-apikey": self.api_key
        }

        try:
            response = requests.get(
                endpoint,
                headers=headers,
                timeout=10
            )
            response.raise_for_status()
            result = response.json()

        except requests.exceptions.Timeout:
            raise VirusTotalAPIError("API 요청 타임아웃 (10초 초과)")
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                raise VirusTotalAPIError("API 키 오류 (HTTP 401)")
            elif e.response.status_code == 404:
                raise VirusTotalAPIError("URL 정보 없음 (HTTP 404)")
            elif e.response.status_code == 429:
                raise VirusTotalAPIError("Rate limit 초과 (HTTP 429)")
            else:
                raise VirusTotalAPIError(f"API 요청 실패: {str(e)}")
        except requests.exceptions.RequestException as e:
            raise VirusTotalAPIError(f"API 요청 실패: {str(e)}")
        except ValueError:
            raise VirusTotalAPIError("API 응답 JSON 파싱 실패")

        # 결과 파싱
        try:
            data = result.get("data", {})
            attributes = data.get("attributes", {})
            stats = attributes.get("last_analysis_stats", {})

            malicious = stats.get("malicious", 0)
            suspicious = stats.get("suspicious", 0)
            harmless = stats.get("harmless", 0)
            undetected = stats.get("undetected", 0)
            total = malicious + suspicious + harmless + undetected

            return {
                "malicious": malicious,
                "suspicious": suspicious,
                "harmless": harmless,
                "undetected": undetected,
                "total_engines": total,
                "is_malicious": malicious > 0,
                "url": url,
                "source": "VirusTotal"
            }

        except (KeyError, TypeError) as e:
            raise VirusTotalAPIError(f"API 응답 파싱 실패: {str(e)}")


# Singleton 패턴 - 글로벌 클라이언트 인스턴스
_client: Optional[VirusTotalClient] = None


def get_virustotal_client() -> Optional[VirusTotalClient]:
    """
    VirusTotal 클라이언트 인스턴스 반환 (Lazy Loading)

    Returns:
        VirusTotalClient 인스턴스 또는 None (API Key 없는 경우)
    """
    global _client

    if _client is None:
        if os.getenv("VIRUSTOTAL_API_KEY"):
            try:
                _client = VirusTotalClient()
                print("[VirusTotal] API 클라이언트 초기화 완료")
            except VirusTotalAPIError as e:
                print(f"[VirusTotal] 초기화 실패: {e}")
                return None
        else:
            print("[VirusTotal] VIRUSTOTAL_API_KEY 환경변수가 설정되지 않았습니다.")
            return None

    return _client


def check_url_virustotal(url: str) -> Optional[Dict]:
    """
    VirusTotal API로 URL 악성 여부 검사 (Wrapper Function)

    Args:
        url: 검사할 URL

    Returns:
        검사 결과 또는 None (API 사용 불가 또는 에러 시)
    """
    client = get_virustotal_client()
    if not client:
        return None

    try:
        result = client.check_url(url)
        print(f"[VirusTotal] URL 검사 성공: {url} → malicious={result.get('malicious')}, suspicious={result.get('suspicious')}")
        return result
    except VirusTotalAPIError as e:
        print(f"[VirusTotal] URL 검사 실패: {url} → {e}")
        return None
