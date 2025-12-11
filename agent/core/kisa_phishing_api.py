"""
KISA (한국인터넷진흥원) 피싱사이트 URL API 클라이언트

TheCheat API와 동일한 패턴으로 구현:
- API 클라이언트 (KISAPhishingClient)
- 로컬 캐시 시스템 (KISAPhishingCache) - O(1) 검색 성능
- Graceful fallback (API Key 없으면 빈 결과 반환)
"""

import os
import re
import json
import requests
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from urllib.parse import urlparse


# ============================================================================
# 에러 클래스
# ============================================================================

class KISAAPIError(Exception):
    """KISA API 에러 베이스 클래스"""
    pass


class InvalidAPIKeyError(KISAAPIError):
    """유효하지 않은 API Key (401)"""
    pass


class ServerError(KISAAPIError):
    """서버 에러 (500)"""
    pass


# ============================================================================
# KISA 피싱사이트 URL API 클라이언트
# ============================================================================

class KISAPhishingClient:
    """
    KISA 피싱사이트 URL Open API 클라이언트

    API 스펙:
    - 엔드포인트: GET https://api.odcloud.kr/api/15109780/v1/uddi:707478dd-938f-4155-badb-fae6202ee7ed
    - 인증: serviceKey 쿼리 파라미터 (공공데이터포털 표준)
    - 응답: 페이지네이션 (27,582개 레코드)

    주의사항:
    - 검색 기능 없음 → 전체 DB 다운로드 필요
    - 로컬 캐싱 전략 필수 (KISAPhishingCache 사용)
    """

    def __init__(self, api_key: str, base_url: str = "https://api.odcloud.kr"):
        """
        Args:
            api_key: KISA Open API 서비스 키
            base_url: API 베이스 URL (기본: https://api.odcloud.kr)
        """
        self.api_key = api_key
        self.base_url = base_url
        self.endpoint = f"{base_url}/api/15109780/v1/uddi:707478dd-938f-4155-badb-fae6202ee7ed"

    def fetch_page(self, page: int = 1, per_page: int = 1000) -> Dict[str, Any]:
        """
        KISA 피싱사이트 DB에서 페이지 단위로 데이터 가져오기

        Args:
            page: 페이지 번호 (1부터 시작)
            per_page: 페이지당 레코드 수 (기본: 1000, 최대: 1000)

        Returns:
            {
                "page": 1,
                "perPage": 1000,
                "totalCount": 27582,
                "currentCount": 1000,
                "data": [
                    {"날짜": "2024-12-01", "홈페이지주소": "http://phishing.com"}
                ]
            }

        Raises:
            InvalidAPIKeyError: API Key 인증 실패 (401)
            ServerError: 서버 에러 (500)
            KISAAPIError: 기타 API 에러
        """
        try:
            params = {
                "page": page,
                "perPage": min(per_page, 1000),  # 최대 1000개
                "returnType": "JSON",
                "serviceKey": self.api_key  # 공공데이터포털 인증 방식
            }

            response = requests.get(
                self.endpoint,
                params=params,
                timeout=30
            )

            # 에러 처리
            if response.status_code == 401:
                raise InvalidAPIKeyError("유효하지 않은 KISA API Key")
            elif response.status_code == 500:
                raise ServerError("KISA API 서버 에러")
            elif response.status_code != 200:
                raise KISAAPIError(f"KISA API 에러: {response.status_code}")

            return response.json()

        except requests.RequestException as e:
            raise KISAAPIError(f"KISA API 호출 실패: {str(e)}")

    def fetch_all(self, max_pages: int = None) -> List[Dict]:
        """
        전체 피싱사이트 DB 다운로드 (페이지네이션 자동 처리)

        Args:
            max_pages: 최대 페이지 수 (None이면 전체)

        Returns:
            전체 피싱사이트 레코드 리스트
            [
                {"날짜": "2024-12-01", "홈페이지주소": "http://phishing.com"},
                ...
            ]
        """
        all_data = []
        page = 1
        per_page = 1000

        while True:
            response = self.fetch_page(page=page, per_page=per_page)
            all_data.extend(response["data"])

            # 마지막 페이지 확인
            if response["currentCount"] < per_page:
                break

            # 최대 페이지 제한
            if max_pages and page >= max_pages:
                break

            page += 1

        return all_data


# ============================================================================
# KISA 피싱사이트 로컬 캐시 시스템
# ============================================================================

class KISAPhishingCache:
    """
    KISA 피싱사이트 DB 로컬 캐시

    성능 최적화:
    - 전체 DB를 로컬 파일로 저장 (JSON)
    - 도메인별 인덱스 생성 (dict) → O(1) 검색
    - TTL: 24시간 (KISA DB는 수시 업데이트)

    캐시 구조:
    {
        "updated_at": "2025-12-06T10:00:00",
        "total_count": 27582,
        "domain_index": {
            "phishing-site.com": {
                "url": "http://phishing-site.com",
                "reported_date": "2024-12-01"
            }
        }
    }
    """

    def __init__(self, cache_file: str = None):
        """
        Args:
            cache_file: 캐시 파일 경로 (기본: agent/data/kisa_phishing_cache.json)
        """
        if cache_file is None:
            # 기본 경로: agent/data/kisa_phishing_cache.json
            base_dir = Path(__file__).parent.parent / "data"
            base_dir.mkdir(exist_ok=True)
            cache_file = base_dir / "kisa_phishing_cache.json"

        self.cache_file = Path(cache_file)
        self.cache_data = self._load_cache()

    def _load_cache(self) -> Dict[str, Any]:
        """캐시 파일 로드"""
        if not self.cache_file.exists():
            return {
                "updated_at": None,
                "total_count": 0,
                "domain_index": {}
            }

        try:
            with open(self.cache_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {
                "updated_at": None,
                "total_count": 0,
                "domain_index": {}
            }

    def _save_cache(self, cache_data: Dict[str, Any]):
        """캐시 파일 저장"""
        with open(self.cache_file, "w", encoding="utf-8") as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2)

    def is_expired(self, ttl: int = 86400) -> bool:
        """
        캐시 만료 여부 확인

        Args:
            ttl: Time to live (초 단위, 기본: 86400 = 24시간)

        Returns:
            True: 만료됨 (갱신 필요)
            False: 유효함
        """
        if not self.cache_data.get("updated_at"):
            return True

        updated_at = datetime.fromisoformat(self.cache_data["updated_at"])
        expiry_time = updated_at + timedelta(seconds=ttl)

        return datetime.now() >= expiry_time

    def update_cache(self, client: KISAPhishingClient):
        """
        전체 피싱사이트 DB를 다운로드하여 로컬 캐시 업데이트

        Args:
            client: KISAPhishingClient 인스턴스

        처리 시간: ~30초 (27,582개 레코드 다운로드)
        """
        print("[KISA] 피싱사이트 DB 캐시 업데이트 시작...")

        # 전체 DB 다운로드
        all_phishing_urls = client.fetch_all()

        # 도메인별 인덱스 생성 (O(1) 검색)
        domain_index = {}
        for record in all_phishing_urls:
            url = record.get("홈페이지주소", "")
            reported_date = record.get("날짜", "")

            if not url:
                continue

            domain = self._extract_domain(url)
            if domain:
                domain_index[domain] = {
                    "url": url,
                    "reported_date": reported_date
                }

        # 캐시 데이터 생성
        cache_data = {
            "updated_at": datetime.now().isoformat(),
            "total_count": len(all_phishing_urls),
            "domain_index": domain_index
        }

        # 캐시 파일 저장
        self._save_cache(cache_data)
        self.cache_data = cache_data

        print(f"[KISA] 캐시 업데이트 완료: {len(domain_index)} 도메인 인덱싱")

    def _extract_domain(self, url: str) -> Optional[str]:
        """
        URL에서 도메인 추출 및 정규화

        정규화 규칙:
        - 프로토콜 제거 (http://, https://)
        - www. 제거
        - 경로/쿼리 제거
        - 소문자 변환

        Examples:
            "http://www.phishing.com/login?id=123" → "phishing.com"
            "https://phishing.com" → "phishing.com"
            "PHISHING.COM" → "phishing.com"

        Args:
            url: 원본 URL

        Returns:
            정규화된 도메인 (추출 실패 시 None)
        """
        try:
            # URL 파싱
            if not url.startswith(("http://", "https://")):
                url = "http://" + url

            parsed = urlparse(url)
            domain = parsed.netloc.lower()

            # www. 제거
            if domain.startswith("www."):
                domain = domain[4:]

            return domain if domain else None

        except Exception:
            return None

    def is_phishing(self, url: str) -> Optional[Dict]:
        """
        캐시된 DB에서 URL 피싱 여부 확인 (O(1) 속도)

        Args:
            url: 확인할 URL

        Returns:
            피싱사이트인 경우:
            {
                "url": "http://phishing.com",
                "reported_date": "2024-12-01"
            }

            아닌 경우: None
        """
        domain = self._extract_domain(url)
        if not domain:
            return None

        return self.cache_data["domain_index"].get(domain)


# ============================================================================
# Wrapper 함수 (기존 코드 통합용)
# ============================================================================

# 전역 캐시 인스턴스 (싱글톤)
_cache_instance = None

def get_kisa_cache() -> Optional[KISAPhishingCache]:
    """
    KISA 피싱사이트 캐시 인스턴스 반환 (싱글톤)

    Returns:
        KISAPhishingCache 인스턴스 (API Key 없으면 None)
    """
    global _cache_instance

    # API Key 확인
    api_key = os.getenv("KISA_PHISHING_API_KEY")
    if not api_key or api_key == "your_kisa_api_key_here":
        return None

    # 캐시 인스턴스 초기화
    if _cache_instance is None:
        _cache_instance = KISAPhishingCache()

        # 캐시 만료 확인 (24시간)
        if _cache_instance.is_expired(ttl=86400):
            try:
                client = KISAPhishingClient(api_key=api_key)
                _cache_instance.update_cache(client)
            except Exception as e:
                print(f"[KISA] 캐시 업데이트 실패: {e}")

    return _cache_instance


def check_url_kisa(url: str) -> Optional[Dict]:
    """
    KISA 피싱사이트 DB에서 URL 조회 (Wrapper 함수)

    Args:
        url: 확인할 URL

    Returns:
        피싱사이트인 경우:
        {
            "is_phishing": True,
            "matched_url": "http://phishing.com",
            "reported_date": "2024-12-01",
            "source": "KISA"
        }

        아닌 경우 또는 API Key 없음: None
    """
    cache = get_kisa_cache()
    if not cache:
        return None

    result = cache.is_phishing(url)
    if result:
        return {
            "is_phishing": True,
            "matched_url": result["url"],
            "reported_date": result["reported_date"],
            "source": "KISA"
        }

    return None
