"""
Entity Extractor - 메시지에서 식별자 추출 모듈

Agent B Hybrid Agent용 엔티티 추출기.
전화번호, URL, 계좌번호, 이메일 등을 정규식으로 추출.

사용 목적:
- threat_intelligence_mcp 호출 전 식별자 추출
- 위험 요소 자동 식별
"""
import re
from typing import Dict, List, Any


# ============================================================
# 정규식 패턴 정의
# ============================================================

PATTERNS = {
    # 한국 휴대폰 번호 (010, 011, 016, 017, 018, 019)
    "phone": r'01[0-9]-?\d{3,4}-?\d{4}',

    # URL (http/https + 단축 URL)
    "url": r'(?:https?://[^\s<>"\']+|(?:bit\.ly|han\.gl|tinyurl\.com|goo\.gl|t\.co|is\.gd|lrl\.kr)/[^\s<>"\']+)',

    # 계좌번호 (다양한 형식)
    "account": r'\d{3,4}-\d{2,6}-\d{4,8}',

    # 이메일
    "email": r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',

    # 주민등록번호 (마스킹된 형태 포함)
    "resident_id": r'\d{6}-?[1-4]\d{6}|\d{6}-?[1-4]\*{6}',

    # 신용카드 번호 (16자리)
    "credit_card": r'\d{4}-?\d{4}-?\d{4}-?\d{4}',
}

# 전화번호 정규화용 패턴
PHONE_NORMALIZE_PATTERN = re.compile(r'[^\d]')


def normalize_phone(phone: str) -> str:
    """
    전화번호 정규화 (하이픈 제거)

    Args:
        phone: 원본 전화번호

    Returns:
        정규화된 전화번호 (숫자만)
    """
    return PHONE_NORMALIZE_PATTERN.sub('', phone)


def format_phone(phone: str) -> str:
    """
    전화번호 포맷팅 (010-1234-5678 형식)

    Args:
        phone: 정규화된 전화번호

    Returns:
        포맷팅된 전화번호
    """
    digits = normalize_phone(phone)
    if len(digits) == 11:
        return f"{digits[:3]}-{digits[3:7]}-{digits[7:]}"
    elif len(digits) == 10:
        return f"{digits[:3]}-{digits[3:6]}-{digits[6:]}"
    return phone


def extract_phones(text: str) -> List[str]:
    """
    전화번호 추출

    Args:
        text: 분석할 텍스트

    Returns:
        추출된 전화번호 리스트 (정규화됨)
    """
    matches = re.findall(PATTERNS["phone"], text)
    # 중복 제거 및 정규화
    unique = list(set(format_phone(m) for m in matches))
    return unique


def extract_urls(text: str) -> List[str]:
    """
    URL 추출

    Args:
        text: 분석할 텍스트

    Returns:
        추출된 URL 리스트
    """
    matches = re.findall(PATTERNS["url"], text, re.IGNORECASE)
    return list(set(matches))


def extract_accounts(text: str) -> List[str]:
    """
    계좌번호 추출

    Args:
        text: 분석할 텍스트

    Returns:
        추출된 계좌번호 리스트
    """
    matches = re.findall(PATTERNS["account"], text)
    # 전화번호와 중복 제거 (형식이 비슷함)
    phones = set(normalize_phone(p) for p in extract_phones(text))
    filtered = [m for m in matches if normalize_phone(m) not in phones]
    return list(set(filtered))


def extract_emails(text: str) -> List[str]:
    """
    이메일 추출

    Args:
        text: 분석할 텍스트

    Returns:
        추출된 이메일 리스트
    """
    matches = re.findall(PATTERNS["email"], text, re.IGNORECASE)
    return list(set(m.lower() for m in matches))


def extract_entities(message: str) -> Dict[str, Any]:
    """
    메시지에서 모든 엔티티 추출 (메인 함수)

    Args:
        message: 분석할 메시지

    Returns:
        {
            "phone_numbers": List[str],  # 전화번호
            "urls": List[str],           # URL
            "accounts": List[str],       # 계좌번호
            "emails": List[str],         # 이메일
            "total_count": int,          # 총 추출 수
            "has_suspicious": bool       # 의심 요소 포함 여부
        }

    Examples:
        extract_entities("전화 010-1234-5678, 입금 110-123-456789")
        → {
            "phone_numbers": ["010-1234-5678"],
            "accounts": ["110-123-456789"],
            "urls": [],
            "emails": [],
            "total_count": 2,
            "has_suspicious": False
        }
    """
    phone_numbers = extract_phones(message)
    urls = extract_urls(message)
    accounts = extract_accounts(message)
    emails = extract_emails(message)

    total_count = len(phone_numbers) + len(urls) + len(accounts) + len(emails)

    # 의심 요소 판단 (단축 URL 또는 이메일 포함)
    has_suspicious = False
    suspicious_domains = ['bit.ly', 'han.gl', 'tinyurl', 'goo.gl', 't.co']
    for url in urls:
        if any(d in url.lower() for d in suspicious_domains):
            has_suspicious = True
            break

    return {
        "phone_numbers": phone_numbers,
        "urls": urls,
        "accounts": accounts,
        "emails": emails,
        "total_count": total_count,
        "has_suspicious": has_suspicious
    }


# ============================================================
# 고급 추출 (선택적)
# ============================================================

def extract_with_context(message: str) -> Dict[str, Any]:
    """
    문맥 정보와 함께 엔티티 추출

    Args:
        message: 분석할 메시지

    Returns:
        extract_entities() 결과 + 문맥 정보
    """
    result = extract_entities(message)

    # 각 엔티티 주변 문맥 추출
    contexts = []

    for phone in result["phone_numbers"]:
        # 전화번호 주변 10자 추출
        pattern = re.escape(phone.replace('-', r'-?'))
        match = re.search(f'.{{0,10}}{pattern}.{{0,10}}', message)
        if match:
            contexts.append({
                "type": "phone",
                "value": phone,
                "context": match.group()
            })

    for url in result["urls"]:
        match = re.search(f'.{{0,10}}{re.escape(url)}.{{0,10}}', message)
        if match:
            contexts.append({
                "type": "url",
                "value": url,
                "context": match.group()
            })

    result["contexts"] = contexts
    return result
