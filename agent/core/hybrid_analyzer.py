"""
Hybrid PII Analyzer - Rule-based + LLM 통합 분석기

연구 기반 설계:
- Nature 2025: Hybrid approach (Precision 94.7%, Recall 89.4%, F1 91.1%)
- SKT AI Fellowship: KoELECTRA 한국어 NER
- 지란지교데이터: 딥러닝 기반 "맥락 인지" 기술

핵심 개선:
1. LLM이 직접 PII를 인식 (문맥 이해)
2. Rule-based는 1차 필터 + 검증용
3. 두 결과를 Union하여 최종 판단
"""
from typing import Dict, Any, List, Optional
import json
import re

from .pattern_matcher import detect_pii, calculate_risk, get_risk_action


# LLM 직접 PII 감지 프롬프트 (Few-shot 기반)
LLM_PII_DETECTION_PROMPT = """당신은 한국어 개인정보(PII) 감지 전문가입니다.
주어진 텍스트에서 개인정보를 찾아 JSON으로 반환하세요.

## 감지 대상 (한국어 특화)

### 1. 신원정보 (CRITICAL)
- 주민등록번호: 900101-1234567, 9001011234567, 900101/1234567
- 외국인등록번호: 900101-5123456
- 여권번호: M12345678

### 2. 금융정보 (HIGH~MEDIUM)
- 신용카드: 1234-5678-1234-5678, 1234567812345678
- 계좌번호: 110-123-456789, 302-1234-5678-91
- CVC/CVV: 3자리 숫자 (카드와 함께)

### 3. 연락처 (MEDIUM~LOW)
- 전화번호: 010-1234-5678, 010.1234.5678, 01012345678
- 이메일: user@domain.com, user [at] domain [dot] com
- 주소: 서울시 강남구 역삼동... (구어체도 인식)

### 4. 인증정보 (HIGH)
- 비밀번호: "비번은 dkagh1234!", "password: P@ssw0rd"
- API키: sk-proj-..., api_key=...
- 토큰: bearer ..., jwt ...

### 5. 개인식별 (MEDIUM~LOW)
- 이름: 문맥에서 사람 이름으로 판단되는 경우
- 생년월일: 1995년 8월 15일, 95년생, 95년 3월생
- 운전면허: 11-12-345678-90
- 차량번호: 12가 3456

### 6. 민감정보 (HIGH)
- 질병/수술: 맹장 수술, 당뇨, 고혈압
- 장애정보: 시각장애 3급
- 투약정보: 약 복용 중

## 문맥 인식 규칙 (중요!)

1. **구어체 인식**: "제가 95년 3월생인데, 강남구 역삼동 산다고요" → 생년월일 + 주소
2. **띄어쓰기 무시**: "비밀번호는dkagh1234!이고아이디는user01입니다" → 비밀번호 + 아이디
3. **회피 표현**: "myname [at] gmail [dot] com" → 이메일
4. **변형 구분자**: "010.1234.5678", "123ㅡ45ㅡ678901" → 전화번호, 계좌번호
5. **마스킹된 정보**: "921010-1******" → 주민번호 (마스킹되어도 감지)

## 출력 형식 (반드시 JSON)

```json
{
  "found_pii": [
    {
      "type": "resident_id",
      "type_ko": "주민등록번호",
      "value": "900101-1234567",
      "risk_level": "CRITICAL",
      "context": "주민번호로 명시됨"
    }
  ],
  "highest_risk": "CRITICAL",
  "reasoning": "주민등록번호가 포함되어 신원 도용 위험"
}
```

PII가 없으면:
```json
{
  "found_pii": [],
  "highest_risk": "LOW",
  "reasoning": "민감정보 없음"
}
```

## 예시

### 예시 1
입력: "아니 제가 95년 3월생인데, 서울시 강남구 역삼동... 산다고요."
출력:
```json
{
  "found_pii": [
    {"type": "birth_date", "type_ko": "생년월일", "value": "95년 3월생", "risk_level": "LOW", "context": "구어체로 언급"},
    {"type": "address", "type_ko": "주소", "value": "서울시 강남구 역삼동", "risk_level": "LOW", "context": "거주지 언급"}
  ],
  "highest_risk": "LOW",
  "reasoning": "생년월일과 거주지가 구어체로 노출됨"
}
```

### 예시 2
입력: "비밀번호는dkagh1234!이고아이디는user01입니다"
출력:
```json
{
  "found_pii": [
    {"type": "password", "type_ko": "비밀번호", "value": "dkagh1234!", "risk_level": "HIGH", "context": "띄어쓰기 없이 비밀번호 노출"},
    {"type": "login_id", "type_ko": "로그인ID", "value": "user01", "risk_level": "MEDIUM", "context": "아이디로 명시"}
  ],
  "highest_risk": "HIGH",
  "reasoning": "인증정보(비밀번호, 아이디) 동시 노출"
}
```

### 예시 3
입력: "성명:최인재, 주민:921010-1******, 주소:수원시 영통구..."
출력:
```json
{
  "found_pii": [
    {"type": "person_name", "type_ko": "이름", "value": "최인재", "risk_level": "LOW", "context": "성명으로 표기"},
    {"type": "resident_id", "type_ko": "주민등록번호", "value": "921010-1******", "risk_level": "CRITICAL", "context": "부분 마스킹된 주민번호"},
    {"type": "address", "type_ko": "주소", "value": "수원시 영통구", "risk_level": "LOW", "context": "주소로 표기"}
  ],
  "highest_risk": "CRITICAL",
  "reasoning": "이름, 주민번호(마스킹), 주소 조합 - 이력서 형태 유출"
}
```

이제 다음 텍스트를 분석하세요:
"""


class HybridAnalyzer:
    """
    Hybrid PII 분석기

    1단계: Rule-based (빠른 정규식 스캔)
    2단계: LLM 직접 분석 (문맥 이해)
    3단계: 결과 병합 (Union)
    """

    def __init__(self):
        self.llm = None
        self._llm_initialized = False

    def _get_llm(self):
        """LLM 인스턴스 가져오기 (Lazy Loading)"""
        if not self._llm_initialized:
            try:
                from ..llm.kanana import LLMManager
                self.llm = LLMManager.get("instruct")
                self._llm_initialized = True
            except Exception as e:
                print(f"[HybridAnalyzer] LLM 로드 실패: {e}")
                self._llm_initialized = True  # 재시도 방지
        return self.llm

    def analyze(self, text: str, use_llm: bool = True) -> Dict[str, Any]:
        """
        Hybrid 분석 수행

        Args:
            text: 분석할 텍스트
            use_llm: LLM 분석 사용 여부 (기본: True)

        Returns:
            통합 분석 결과
        """
        # 1단계: Rule-based 분석 (항상 수행)
        rule_result = self._rule_based_analyze(text)

        # LLM 사용 안함 또는 LLM 없음
        if not use_llm:
            return rule_result

        llm = self._get_llm()
        if not llm:
            return rule_result

        # 2단계: LLM 분석
        llm_result = self._llm_analyze(text)

        # 3단계: 결과 병합
        merged = self._merge_results(rule_result, llm_result)

        return merged

    def _rule_based_analyze(self, text: str) -> Dict[str, Any]:
        """Rule-based 정규식 분석"""
        pii_result = detect_pii(text)
        risk_result = calculate_risk(pii_result["found_pii"])
        action = get_risk_action(risk_result["final_risk"])

        return {
            "method": "rule_based",
            "pii_scan": pii_result,
            "risk_evaluation": risk_result,
            "recommended_action": action,
            "found_pii": pii_result["found_pii"],
            "risk_level": risk_result["final_risk"],
            "is_secret_recommended": risk_result["is_secret_recommended"]
        }

    def _llm_analyze(self, text: str) -> Optional[Dict[str, Any]]:
        """LLM 직접 PII 분석"""
        llm = self._get_llm()
        if not llm:
            return None

        try:
            # LLM에게 직접 PII 감지 요청
            prompt = LLM_PII_DETECTION_PROMPT + f"\n입력: \"{text}\"\n출력:"

            response = llm.analyze(text=prompt, system_prompt="")

            # JSON 파싱
            result = self._parse_llm_response(response)

            if result:
                result["method"] = "llm"
                return result

            return None

        except Exception as e:
            print(f"[HybridAnalyzer] LLM 분석 오류: {e}")
            return None

    def _parse_llm_response(self, response: str) -> Optional[Dict[str, Any]]:
        """LLM 응답에서 JSON 파싱"""
        # JSON 블록 찾기
        patterns = [
            r'```json\s*(.*?)\s*```',
            r'```\s*(.*?)\s*```',
            r'\{[\s\S]*"found_pii"[\s\S]*\}',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, response, re.DOTALL)
            for match in matches:
                try:
                    # 중괄호로 시작하지 않으면 감싸기
                    if not match.strip().startswith('{'):
                        continue
                    result = json.loads(match)
                    if "found_pii" in result:
                        return result
                except json.JSONDecodeError:
                    continue

        # 직접 전체 응답 파싱 시도
        try:
            result = json.loads(response)
            if "found_pii" in result:
                return result
        except json.JSONDecodeError:
            pass

        return None

    def _merge_results(
        self,
        rule_result: Dict[str, Any],
        llm_result: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Rule-based와 LLM 결과 병합 (Union)

        병합 규칙:
        1. PII는 Union (둘 중 하나라도 감지하면 포함)
        2. 위험도는 Max (더 높은 위험도 선택)
        3. LLM이 찾은 추가 정보는 별도 표시
        """
        if not llm_result:
            return rule_result

        # 1. PII 목록 병합
        rule_pii = rule_result.get("found_pii", [])
        llm_pii = llm_result.get("found_pii", [])

        # LLM 결과를 Rule 형식으로 변환
        llm_pii_normalized = []
        for pii in llm_pii:
            llm_pii_normalized.append({
                "id": pii.get("type", "unknown"),
                "category": self._infer_category(pii.get("type", "")),
                "name_ko": pii.get("type_ko", pii.get("type", "알수없음")),
                "value": pii.get("value", ""),
                "risk_level": pii.get("risk_level", "LOW"),
                "source": "llm",
                "context": pii.get("context", "")
            })

        # 중복 제거하면서 병합 (value 기준)
        merged_pii = list(rule_pii)  # Rule 결과 복사
        existing_values = {p.get("value", "") for p in rule_pii}

        for pii in llm_pii_normalized:
            if pii.get("value", "") not in existing_values:
                merged_pii.append(pii)
                existing_values.add(pii.get("value", ""))

        # 2. 위험도 결정 (최대값)
        risk_order = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}

        rule_risk = rule_result.get("risk_level", "LOW")
        llm_risk = llm_result.get("highest_risk", "LOW")

        final_risk = rule_risk if risk_order.get(rule_risk, 0) >= risk_order.get(llm_risk, 0) else llm_risk

        # 3. 조합 규칙 재적용 (병합된 PII로)
        if len(merged_pii) > len(rule_pii):
            # LLM이 추가 PII를 찾았으면 위험도 재계산
            new_risk_result = calculate_risk(merged_pii)
            if risk_order.get(new_risk_result["final_risk"], 0) > risk_order.get(final_risk, 0):
                final_risk = new_risk_result["final_risk"]

        # 4. 결과 조합
        is_secret = final_risk in ["MEDIUM", "HIGH", "CRITICAL"]
        action = get_risk_action(final_risk)

        return {
            "method": "hybrid",
            "found_pii": merged_pii,
            "risk_level": final_risk,
            "is_secret_recommended": is_secret,
            "recommended_action": action,
            "rule_pii_count": len(rule_pii),
            "llm_pii_count": len(llm_pii),
            "total_pii_count": len(merged_pii),
            "llm_reasoning": llm_result.get("reasoning", ""),
            "pii_scan": rule_result.get("pii_scan"),
            "risk_evaluation": {
                "final_risk": final_risk,
                "base_risk": rule_result.get("risk_evaluation", {}).get("base_risk", "LOW"),
                "is_secret_recommended": is_secret,
            }
        }

    def _infer_category(self, pii_type: str) -> str:
        """PII 타입에서 카테고리 추론"""
        category_map = {
            "resident_id": "government_id",
            "passport": "government_id",
            "driver_license": "government_id",
            "foreigner_id": "government_id",
            "credit_card": "financial",
            "bank_account": "financial",
            "account": "financial",
            "cvc": "financial",
            "phone": "contact",
            "email": "contact",
            "address": "contact",
            "password": "authentication",
            "login_id": "authentication",
            "api_key": "authentication",
            "token": "authentication",
            "person_name": "personal",
            "birth_date": "personal",
            "vehicle_number": "personal",
            "disease": "health",
            "disability": "health",
            "medication": "health",
        }
        return category_map.get(pii_type, "other")


# 싱글톤 인스턴스
_analyzer_instance: Optional[HybridAnalyzer] = None


def get_hybrid_analyzer() -> HybridAnalyzer:
    """Hybrid 분석기 싱글톤 인스턴스 반환"""
    global _analyzer_instance
    if _analyzer_instance is None:
        _analyzer_instance = HybridAnalyzer()
    return _analyzer_instance


def hybrid_analyze(text: str, use_llm: bool = True) -> Dict[str, Any]:
    """
    Hybrid 분석 수행 (편의 함수)

    Args:
        text: 분석할 텍스트
        use_llm: LLM 분석 사용 여부

    Returns:
        분석 결과
    """
    analyzer = get_hybrid_analyzer()
    return analyzer.analyze(text, use_llm=use_llm)
