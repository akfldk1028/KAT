"""
Outgoing Agent - 안심 전송 Agent
발신 메시지의 민감정보를 감지하고 보호 조치를 제안

v2.0 - pattern_matcher.py + sensitive_patterns.json 기반

기능:
- Rule-based PII 감지 (pattern_matcher 사용)
- 조합 규칙 적용 (이름+주민번호 → CRITICAL 등)
- Kanana LLM + ReAct 패턴 (use_ai=True)
"""
import re
from typing import Dict, Any
from .base import BaseAgent
from ..core.models import RiskLevel, AnalysisResponse
from ..core.pattern_matcher import detect_pii, detect_document_type, calculate_risk, get_risk_action
from ..llm.kanana import LLMManager
from ..prompts.outgoing_agent import get_outgoing_system_prompt


class OutgoingAgent(BaseAgent):
    """안심 전송 Agent - 발신 메시지 민감정보 감지"""

    @property
    def name(self) -> str:
        return "outgoing"

    def analyze(self, text: str, use_ai: bool = True, **kwargs) -> AnalysisResponse:
        """
        발신 메시지 민감정보 분석 (하이브리드 방식)

        1. Rule-based 패턴 매칭 (빠름, 확실한 패턴 감지)
        2. AI 분석 (use_ai=True일 때, 맥락 이해)
        3. 둘 중 높은 위험도 사용

        Args:
            text: 분석할 메시지
            use_ai: LLM 정밀 분석 활성화 (기본: True)

        Returns:
            AnalysisResponse: 분석 결과
        """
        # Step 0: 빠른 필터링 - 의심스러운 패턴이 없으면 바로 통과
        if not self._has_suspicious_pattern(text):
            return AnalysisResponse(
                risk_level=RiskLevel.LOW,
                reasons=[],
                recommended_action="전송",
                is_secret_recommended=False
            )

        # Step 1: Rule-based 분석 (항상 실행 - 확실한 패턴 감지)
        rule_result = self._analyze_rule_based(text)

        # Step 2: AI 분석 (use_ai=True일 때)
        # 최적화 + Tier 3 조합 패턴 감지
        if use_ai:
            risk_order = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}

            # Rule-based가 LOW이면 맥락적 요소 감지 (Option B: AI의 맥락 판단 활용)
            if rule_result.risk_level.value == "LOW":
                # 숫자 존재 여부 (전화번호, 나이, 주소 등)
                has_numbers = bool(re.search(r'\d', text))

                # 한글 이름 패턴 (2-4글자 한글)
                has_korean_name = bool(re.search(r'[가-힣]{2,4}', text))

                # 이메일 패턴
                has_email_hint = '@' in text

                # 확실히 안전한 경우만 AI 스킵 (숫자도 없고, 이름도 없고, 이메일도 없음)
                if not (has_numbers or has_korean_name or has_email_hint):
                    return rule_result

                # 맥락적 요소가 있으면 AI한테 조합/맥락 판단 맡기기

            # MEDIUM 이상 또는 맥락적 요소 존재 시 → AI로 재검증
            ai_result = self._analyze_with_ai(text)

            # Step 3: 하이브리드 - 둘 중 높은 위험도 사용
            if risk_order[rule_result.risk_level.value] >= risk_order[ai_result.risk_level.value]:
                # Rule-based가 더 높거나 같음 → Rule 결과 + AI 이유 병합
                combined_reasons = list(rule_result.reasons)
                for reason in ai_result.reasons:
                    if reason not in combined_reasons:
                        combined_reasons.append(reason)

                return AnalysisResponse(
                    risk_level=rule_result.risk_level,
                    reasons=combined_reasons,
                    recommended_action=rule_result.recommended_action,
                    is_secret_recommended=rule_result.is_secret_recommended
                )
            else:
                # AI가 더 높음 → AI 결과 사용
                return ai_result

        # use_ai=False면 Rule-based만 사용
        return rule_result

    def _has_suspicious_pattern(self, text: str) -> bool:
        """
        빠른 필터링: 민감정보가 의심되는 패턴이 있는지 체크
        - 숫자가 일정 길이 이상 연속되거나
        - "-"로 구분된 숫자 패턴이 있거나
        - 민감정보 관련 키워드가 있으면 True
        - Tier 3 조합 패턴 (이름+생년+성별+주소)도 감지
        - [추가] 한글 숫자 패턴 (의미 기반 정규화 대상)
        - [추가] OCR 공백 제거 후 키워드 매칭
        """
        import re

        # OCR 공백 제거 버전 생성 (띄어쓰기로 인한 키워드 누락 방지)
        text_no_space = re.sub(r'\s+', '', text)

        # 숫자가 6자리 이상 연속 (하이픈 포함) - 공백 제거 버전으로도 체크
        if re.search(r'[\d-]{8,}', text) or re.search(r'[\d-]{8,}', text_no_space):
            return True

        # 연도 패턴 (1990년생, 90년생 등)
        if re.search(r'\d{2,4}년생', text) or re.search(r'\d{2,4}년생', text_no_space):
            return True

        # 마스킹된 패턴 (OCR 결과에서 주민번호 등이 마스킹된 경우)
        # 예: 501041-1******* 또는 ******-******* 형태
        if re.search(r'\d{6}[-/]?[1-4][*X]{5,7}', text):
            return True
        if re.search(r'[*X]{6,}', text):  # 연속된 마스킹 문자
            return True

        # === [추가] 한글 숫자 패턴 감지 (Semantic Normalization 대상) ===
        # "공일공", "구공공일일오", "일이삼사오육칠" 등 변칙 표기 감지
        # 한글 숫자가 3개 이상 연속되면 의심
        korean_num_pattern = r'[공일이삼사오육칠팔구영]{3,}'
        if re.search(korean_num_pattern, text) or re.search(korean_num_pattern, text_no_space):
            return True

        # 한글 숫자가 띄어쓰기/구분자로 나뉘어 있어도 감지
        # 예: "구공공일일오 다시 일이삼사오육칠"
        korean_nums = re.findall(r'[공일이삼사오육칠팔구영]+', text)
        total_korean_digits = sum(len(n) for n in korean_nums)
        if total_korean_digits >= 6:  # 6자리 이상이면 의심 (전화번호, 주민번호 등)
            return True
        # === [추가 끝] ===

        # Tier 1-2 민감정보 관련 키워드 (즉시 True)
        sensitive_keywords = [
            '계좌', '통장', '카드', '번호',
            '주민', '등록', '여권', '면허',
            '외국인', '비밀번호', '인증',
            '송금', '이체', '입금',
            # [추가] 변형 키워드
            '민번',  # 주민번호 줄임말
            '보안카드', '지갑', '복구', '니모닉',  # 금융/암호화폐
            '우울증', '병원', '처방', '약',  # 건강정보
            '지문', '홍채', '생체',  # 생체정보
        ]
        for keyword in sensitive_keywords:
            # 원본 텍스트와 공백 제거 버전 모두 체크 (OCR 대응)
            if keyword in text or keyword in text_no_space:
                return True

        # 민감 문서 유형 키워드 (증명서, 등본 등 - 이미지 OCR에서 감지)
        document_keywords = [
            '가족관계', '증명서', '등본', '초본',
            '주민등록', '주민등록증', '운전면허', '건강보험',
            '의료', '진단서', '처방전',
            '소득', '재직', '졸업',
            '인감', '법인', '사업자',
            '출생', '혼인', '사망',
            '신분증',  # [추가] 주민등록증 별칭
        ]
        for keyword in document_keywords:
            keyword_no_space = re.sub(r'\s+', '', keyword)
            if keyword in text or keyword_no_space in text_no_space:
                return True

        # Tier 3 조합 감지 (2개 이상 매칭 시 True)
        tier3_keywords = ['남자', '여자', '남성', '여성', '시 ', '군 ', '구 ', '동 ', '학교', '회사', '대학']
        tier3_count = sum(1 for kw in tier3_keywords if kw in text)
        if tier3_count >= 2:
            return True

        return False

    def _analyze_rule_based(self, text: str) -> AnalysisResponse:
        """
        Rule-based 분석 (pattern_matcher.py 사용)

        1. detect_pii() - 정규식으로 PII 스캔
        2. detect_document_type() - 문서 유형 감지 (가족관계증명서 등)
        3. calculate_risk() - 조합 규칙 적용하여 최종 위험도 계산
        4. get_risk_action() - 권장 조치 반환
        """
        risk_order = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}

        # 1. PII 스캔
        pii_result = detect_pii(text)

        # 2. 문서 유형 감지 (가족관계증명서, 주민등록증 등)
        doc_result = detect_document_type(text)

        # 3. 위험도 계산 (조합 규칙 적용)
        risk_result = calculate_risk(pii_result["found_pii"])

        # 4. 문서 유형 위험도와 비교하여 더 높은 것 사용
        final_risk = risk_result["final_risk"]
        if doc_result["document_type"] and doc_result["risk_level"]:
            doc_risk = doc_result["risk_level"]
            if risk_order.get(doc_risk, 0) > risk_order.get(final_risk, 0):
                final_risk = doc_risk

        # 5. 권장 조치
        recommended_action = get_risk_action(final_risk)

        # 6. 감지 이유 생성
        reasons = []

        # 문서 유형이 감지된 경우 최우선 이유로 추가
        if doc_result["document_type"]:
            reasons.append(f"민감 문서 감지: {doc_result['name_ko']} (위험도: {doc_result['risk_level']})")

        # PII 감지 이유 추가
        for item in pii_result["found_pii"]:
            reasons.append(f"{item['name_ko']} 패턴이 감지되었습니다.")

        # 조합 규칙으로 상향된 경우 이유 추가
        if risk_result["escalation_reason"]:
            reasons.append(risk_result["escalation_reason"])

        # RiskLevel enum으로 변환
        risk_level = RiskLevel(final_risk)

        # 시크릿 전송 권장 여부
        is_secret_recommended = risk_order[final_risk] >= risk_order["MEDIUM"]

        return AnalysisResponse(
            risk_level=risk_level,
            reasons=reasons,
            recommended_action=recommended_action,
            is_secret_recommended=is_secret_recommended
        )

    def _analyze_with_ai(self, text: str) -> AnalysisResponse:
        """Kanana LLM + MCP 프로토콜로 분석"""
        try:
            # LLM 인스턴스 가져오기
            llm = LLMManager.get("instruct")
            if not llm:
                print("[OutgoingAgent] LLM not available, falling back to rule-based")
                return self._analyze_rule_based(text)

            # 시스템 프롬프트 가져오기 (JSON 데이터 동적 주입됨)
            system_prompt = get_outgoing_system_prompt()

            # MCP 프로토콜을 통해 도구 호출
            # Kanana LLM이 MCP 클라이언트로서 MCP 서버의 도구 사용
            result = llm.analyze_with_mcp(
                user_message=text,
                system_prompt=system_prompt,
                max_iterations=3
            )

            # 결과를 AnalysisResponse로 변환
            risk_level_str = result.get("risk_level", "LOW").upper()
            risk_level = getattr(RiskLevel, risk_level_str, RiskLevel.LOW)

            return AnalysisResponse(
                risk_level=risk_level,
                reasons=result.get("reasons", []),
                recommended_action=result.get("recommended_action", "전송"),
                is_secret_recommended=result.get("is_secret_recommended", False)
            )

        except Exception as e:
            print(f"[OutgoingAgent] AI+MCP analysis error: {e}, falling back to rule-based")
            print(f"[OutgoingAgent] Error type: {type(e).__name__}")
            import traceback
            traceback.print_exc()
            return self._analyze_rule_based(text)

    def _tool_scan_pii(self, text: str) -> Dict[str, Any]:
        """scan_pii 도구 - pattern_matcher.detect_pii 래퍼"""
        return detect_pii(text)

    def _tool_evaluate_risk(self, detected_items: list) -> Dict[str, Any]:
        """evaluate_risk 도구 - pattern_matcher.calculate_risk 래퍼"""
        return calculate_risk(detected_items)

    def _tool_analyze_full(self, text: str) -> Dict[str, Any]:
        """analyze_full 도구 - 전체 분석 파이프라인"""
        # 1. PII 스캔
        pii_result = detect_pii(text)

        # 2. 위험도 평가
        risk_result = calculate_risk(pii_result["found_pii"])

        # 3. 권장 조치
        action = get_risk_action(risk_result["final_risk"])

        # 4. 요약
        if pii_result["count"] == 0:
            summary = "민감정보가 감지되지 않았습니다."
        else:
            detected_names = list(set(item["name_ko"] for item in pii_result["found_pii"]))
            summary = f"{len(detected_names)}종의 민감정보 감지: {', '.join(detected_names)}. {action}"

        return {
            "pii_scan": pii_result,
            "risk_evaluation": risk_result,
            "recommended_action": action,
            "summary.md": summary
        }
