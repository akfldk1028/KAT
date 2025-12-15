"""
Incoming Agent - 안심 가드 Agent
수신 메시지의 피싱/사기 위협을 탐지하고 사용자를 보호

v9.0 - AI-Enhanced 3-Stage Pipeline (ver9.0 기획서 기반)

3단계 분석 Flow (AI 참여율 95%):
Stage 1: Rule-based DB 블랙리스트 확인 (<10ms, AI ❌) - 5% 케이스
Stage 2: AI Agent 맥락 분석 (<50ms, AI ✅) - 85% 케이스 ⭐ 핵심
Stage 3: AI Judge 최종 판단 + 설명 (<100ms, AI ✅) - 10% 케이스

핵심 개선 (ver8.0 → ver9.0):
- AI 참여율: 10% → 95%
- Stage 2: Rule-based → AI Agent 맥락 분석
- 맥락 이해: "엄마 생일"(NORMAL) vs "엄마 폰 고장"(A-1) 구분
- 오탐률: 12% → <5%

9개 스미싱 유형 (정부 통계 기반):
A-1: 지인/가족 사칭 (금감원 33.7%)
A-2: 경조사 빙자 (KISA 1.7만건)
A-3: 로맨스 스캠 (경찰청 신종)
B-1: 수사/금융 기관 사칭 (경찰청 78%)
B-2: 공공 행정 알림 (경찰청 19.7배↑)
B-3: 택배/물류 사칭 (KISA 65%)
C-1: 대출 빙자 (금감원 35.2%)
C-2: 투자 리딩방 (국수본 5,340억)
C-3: 몸캠 피싱 (경찰청 공식)
NORMAL: 일상 대화
"""
import json
import time
from typing import Dict, Any, Optional, Tuple

from .base import BaseAgent
from ..core.models import RiskLevel, AnalysisResponse
from ..core.threat_matcher import analyze_incoming_message


class IncomingAgent(BaseAgent):
    """
    안심 가드 Agent - 수신 메시지 위협 탐지

    v9.0 - AI-Enhanced 3-Stage Pipeline
    - Stage 1: Rule-based DB 블랙리스트 확인 (5%, <10ms, AI ❌)
    - Stage 2: AI Agent 맥락 분석 (85%, <50ms, AI ✅) ⭐
    - Stage 3: AI Judge 최종 판단 (10%, <100ms, AI ✅)

    AI 참여율: 95% (Stage 2: 85% + Stage 3: 10%)
    """

    @property
    def name(self) -> str:
        return "incoming"

    def analyze(
        self,
        text: str,
        sender_id: int = None,
        user_id: int = None,
        conversation_history: list = None,
        use_ai: bool = True,
        **kwargs
    ) -> AnalysisResponse:
        """
        수신 메시지 위협 분석 (ver9.0 3-Stage Pipeline)

        3-Stage Pipeline (AI 참여율 95%):
        - Stage 1: DB 블랙리스트 확인 → HIT면 즉시 CRITICAL
        - Stage 2: AI Agent 맥락 분석 → 9개 유형 분류 ⭐
        - Stage 3: AI Judge 최종 판단 → 설명 생성

        Args:
            text: 분석할 메시지
            sender_id: 발신자 ID (Stage 3용)
            user_id: 수신자 ID (Stage 3용)
            conversation_history: 대화 히스토리 (Stage 3용)
            use_ai: AI 분석 활성화 (기본: True) - True면 3-Stage, False면 Rule-only

        Returns:
            AnalysisResponse: 분석 결과
        """
        history_count = len(conversation_history) if conversation_history else 0
        print(f"[IncomingAgent] ver9.0 3-Stage 분석 시작: text={text[:50]}... (use_ai={use_ai})")

        # ver9.0 3-Stage Pipeline (use_ai=True 기본)
        if use_ai:
            result = self._analyze_3_stages_v9(
                text=text,
                user_id=user_id,
                sender_id=sender_id,
                conversation_history=conversation_history
            )
            return self._convert_v9_result_to_response(result)
        else:
            # use_ai=False면 기존 4-Stage (하위 호환)
            result = self._analyze_4_stages(text, user_id, sender_id, conversation_history, use_ai=False)
            return self._convert_full_result_to_response(result)

    # =========================================================================
    # ver9.0 3-Stage Pipeline
    # =========================================================================

    def _analyze_3_stages_v9(
        self,
        text: str,
        user_id: int = None,
        sender_id: int = None,
        conversation_history: list = None
    ) -> dict:
        """
        ver9.0 AI-Enhanced 3-Stage Pipeline

        Stage 1: Rule-based DB 블랙리스트 (<10ms)
        Stage 2: AI Agent 맥락 분석 (<50ms) ⭐
        Stage 3: AI Judge 최종 판단 (<100ms)

        Returns:
            dict: {
                stage1: {...},
                stage2: {...},
                stage3: {...},
                final_risk_level: str,
                terminated_at: int  # 종료된 Stage 번호
            }
        """
        start_time = time.time()

        # ========== Stage 1: DB 블랙리스트 확인 ==========
        stage1_start = time.time()
        stage1 = self._stage1_db_blacklist(text)
        stage1["time_ms"] = int((time.time() - stage1_start) * 1000)
        print(f"[Stage 1] DB 블랙리스트: {stage1.get('decision', 'CONTINUE')} ({stage1['time_ms']}ms)")

        # Stage 1에서 CRITICAL이면 즉시 종료
        if stage1.get("terminate"):
            return {
                "stage1": stage1,
                "stage2": None,
                "stage3": None,
                "final_risk_level": "CRITICAL",
                "terminated_at": 1,
                "total_time_ms": int((time.time() - start_time) * 1000)
            }

        # ========== Stage 2: AI Agent 맥락 분석 ==========
        stage2_start = time.time()
        stage2 = self._stage2_ai_agent_categorization(text, conversation_history, sender_id)
        stage2["time_ms"] = int((time.time() - stage2_start) * 1000)
        print(f"[Stage 2] AI Agent 분류: {stage2.get('category')} (신뢰도: {stage2.get('confidence', 0):.2f}, {stage2['time_ms']}ms)")

        # Stage 2에서 NORMAL이면 SAFE로 종료 (85% 케이스)
        # 단, 피싱 의심 키워드가 있으면 Stage 3로 진행
        if stage2.get("category") == "NORMAL" and stage2.get("confidence", 0) >= 0.8:
            # 피싱 의심 키워드 확인
            matched_patterns = stage2.get("matched_patterns", [])

            if len(matched_patterns) > 0:
                # 키워드가 있으면 Stage 3로 진행
                print(f"[Stage 2] NORMAL이지만 의심 키워드 발견 ({len(matched_patterns)}개) → Stage 3 진행")
            else:
                # 키워드도 없고 NORMAL → SAFE 종료
                print(f"[Stage 2] NORMAL + 키워드 없음 → SAFE 종료")
                return {
                    "stage1": stage1,
                    "stage2": stage2,
                    "stage3": None,
                    "final_risk_level": "SAFE",
                    "terminated_at": 2,
                    "total_time_ms": int((time.time() - start_time) * 1000)
                }

        # ========== Stage 3: AI Judge 최종 판단 ==========
        stage3_start = time.time()
        stage3 = self._stage3_ai_judge(
            text=text,
            stage1=stage1,
            stage2=stage2,
            user_id=user_id,
            sender_id=sender_id,
            conversation_history=conversation_history
        )
        stage3["time_ms"] = int((time.time() - stage3_start) * 1000)
        print(f"[Stage 3] AI Judge 판정: {stage3.get('risk_level')} ({stage3['time_ms']}ms)")

        return {
            "stage1": stage1,
            "stage2": stage2,
            "stage3": stage3,
            "final_risk_level": stage3.get("risk_level", "SUSPICIOUS"),
            "terminated_at": 3,
            "total_time_ms": int((time.time() - start_time) * 1000)
        }

    def _stage1_db_blacklist(self, text: str) -> dict:
        """
        Stage 1: Rule-based DB 블랙리스트 확인

        - 계좌번호, URL, 전화번호 추출 (entity_extractor)
        - threat_intelligence MCP 통해 신고 DB 조회
        - HIT → 즉시 CRITICAL + 종료

        AI 참여: ❌ (팩트 기반 즉시 판단)

        DB 소스 (기획서 4.1.1 참조):
        - TheCheat API: 전화번호, 계좌번호
        - KISA 피싱사이트: URL (27,582개)
        - VirusTotal: URL 악성 여부
        """
        from ..core.entity_extractor import extract_entities
        from ..core.threat_intelligence import check_identifier

        # 엔티티 추출 (entity_extractor_mcp 동일 로직)
        extracted = extract_entities(text)
        entities = {
            "accounts": extracted.get("accounts", []),
            "phones": extracted.get("phone_numbers", []),
            "urls": extracted.get("urls", [])
        }

        # threat_intelligence MCP 통해 신고 DB 조회
        reported_accounts = []
        reported_phones = []
        reported_urls = []
        max_risk_score = 0
        sources_used = []

        # 계좌번호 조회 (TheCheat API)
        for account in entities["accounts"]:
            result = check_identifier(account, "account")
            if result.get("has_reported"):
                reported_accounts.append({
                    "account": account,
                    "source": result.get("source"),
                    "prior_probability": result.get("prior_probability", 0),
                    "details": result.get("details", {})
                })
                max_risk_score = max(max_risk_score, 95)
                if result.get("source") not in sources_used:
                    sources_used.append(result.get("source"))

        # 전화번호 조회 (TheCheat API)
        for phone in entities["phones"]:
            result = check_identifier(phone, "phone")
            if result.get("has_reported"):
                reported_phones.append({
                    "phone": phone,
                    "source": result.get("source"),
                    "prior_probability": result.get("prior_probability", 0),
                    "details": result.get("details", {})
                })
                max_risk_score = max(max_risk_score, 95)
                if result.get("source") not in sources_used:
                    sources_used.append(result.get("source"))

        # URL 조회 (KISA 캐시 → VirusTotal)
        for url in entities["urls"]:
            result = check_identifier(url, "url")
            if result.get("has_reported"):
                reported_urls.append({
                    "url": url,
                    "source": result.get("source"),
                    "threat_type": result.get("threat_type", "unknown"),
                    "prior_probability": result.get("prior_probability", 0),
                    "details": result.get("details", {})
                })
                max_risk_score = max(max_risk_score, 95)
                if result.get("source") not in sources_used:
                    sources_used.append(result.get("source"))

        # 블랙리스트 HIT 확인
        has_reported = (
            len(reported_accounts) > 0 or
            len(reported_phones) > 0 or
            len(reported_urls) > 0
        )

        if has_reported:
            return {
                "stage": 1,
                "decision": "CRITICAL",
                "entities": entities,
                "db_hit": True,
                "reported_accounts": reported_accounts,
                "reported_phones": reported_phones,
                "reported_urls": reported_urls,
                "report_count": len(reported_accounts) + len(reported_phones) + len(reported_urls),
                "max_risk_score": max_risk_score,
                "sources": sources_used,
                "terminate": True  # 즉시 종료
            }

        # 블랙리스트 MISS → Stage 2로
        return {
            "stage": 1,
            "decision": None,
            "entities": entities,
            "db_hit": False,
            "sources": sources_used,
            "terminate": False  # Stage 2로 진행
        }

    def _stage2_ai_agent_categorization(self, text: str, conversation_history: list = None, current_sender_id: int = None) -> dict:
        """
        Stage 2: AI Agent 맥락 분석 (ver9.0 핵심)

        - 키워드 힌트 생성 (Rule-based, 참고용)
        - Kanana Agent가 대화 맥락 파악하여 9개 유형 분류
        - NORMAL → SAFE 판정 + 종료 (85% 케이스)

        AI 참여: ✅ (Kanana Agent 맥락 분류)

        v9.0.1: conversation_history 추가 - 멀티메시지 사기 패턴 감지 지원
        v9.0.2: current_sender_id 추가 - [상대방]/[나] 구분으로 정확한 맥락 분석
        """
        from ..llm.kanana import LLMManager
        from ..prompts.incoming_agent import get_stage2_agent_prompt_with_context, format_keyword_hints

        # Step 1: 키워드 힌트 생성 (Rule-based, 참고용)
        # 현재 메시지 + 대화 히스토리 전체에서 키워드 추출
        all_text = text
        if conversation_history:
            history_text = " ".join([msg.get("message", "") for msg in conversation_history[-10:]])
            all_text = f"{history_text} {text}"

        keyword_hints = self._generate_keyword_hints(all_text)
        hints_text = format_keyword_hints(keyword_hints)

        # Step 2: 대화 맥락 포맷팅 (발신자 구분)
        # current_sender_id = 현재 메시지 발신자 = 상대방 (사기 의심자)
        # 히스토리에서 동일 sender_id = [상대방], 다른 sender_id = [나]
        context_text = ""
        if conversation_history and len(conversation_history) > 0:
            context_lines = []
            for msg in conversation_history[-10:]:  # 최근 10개 메시지
                message = msg.get("message", "")
                msg_sender_id = msg.get("sender_id")

                # 메시지가 있으면 추가 (빈 메시지 제외)
                if message and message.strip():
                    # 발신자 구분: current_sender_id와 같으면 [상대방], 다르면 [나]
                    if current_sender_id and msg_sender_id:
                        sender_label = "[상대방]" if str(msg_sender_id) == str(current_sender_id) else "[나]"
                    else:
                        sender_label = "[상대방]"  # ID 정보 없으면 기본값
                    context_lines.append(f"  {sender_label} {message}")
            context_text = "\n".join(context_lines)

        # Step 3: Kanana Agent 호출
        try:
            llm = LLMManager.get("instruct")
            if not llm:
                print("[Stage 2] LLM not available, fallback to rule-based")
                return self._stage2_rule_fallback(text, keyword_hints)

            prompt = get_stage2_agent_prompt_with_context(text, hints_text, context_text)
            response = llm.analyze(prompt)

            # JSON 파싱
            result = self._parse_llm_json_response(response)

            return {
                "stage": 2,
                "category": result.get("category", "NORMAL"),
                "confidence": result.get("confidence", 0.5),
                "reasoning": result.get("reasoning", ""),
                "matched_patterns": result.get("matched_patterns", []),
                "government_source": result.get("government_source", ""),
                "keyword_hints": keyword_hints,
                "context_used": len(conversation_history) if conversation_history else 0,
                "llm_used": True
            }

        except Exception as e:
            print(f"[Stage 2] AI Agent error: {e}, fallback to rule-based")
            return self._stage2_rule_fallback(text, keyword_hints)

    def _stage2_rule_fallback(self, text: str, keyword_hints: dict) -> dict:
        """Stage 2 AI 실패 시 Rule-based 폴백"""
        # 키워드 힌트에서 가장 높은 점수의 카테고리 선택
        if not keyword_hints:
            return {
                "stage": 2,
                "category": "NORMAL",
                "confidence": 0.5,
                "reasoning": "키워드 힌트 없음 → NORMAL 판정",
                "matched_patterns": [],
                "government_source": "",
                "llm_used": False
            }

        best_category = max(keyword_hints.items(), key=lambda x: x[1].get("score", 0))
        category = best_category[0]
        score = best_category[1].get("score", 0)

        return {
            "stage": 2,
            "category": category if score >= 0.5 else "NORMAL",
            "confidence": score,
            "reasoning": f"Rule-based 폴백: {category} (점수: {score:.2f})",
            "matched_patterns": best_category[1].get("keywords", []),
            "government_source": best_category[1].get("source", ""),
            "llm_used": False
        }

    def _stage3_ai_judge(
        self,
        text: str,
        stage1: dict,
        stage2: dict,
        user_id: int = None,
        sender_id: int = None,
        conversation_history: list = None
    ) -> dict:
        """
        Stage 3: AI Judge 최종 판단 + 설명 생성

        - Stage 1/2 결과 종합
        - 대화 이력 분석 (금감원 통계 인용)
        - 유사 사례 검색 (RAG)
        - 최종 위험도 + 상세 설명

        AI 참여: ✅ (Kanana Judge 종합 판단)
        """
        from ..llm.kanana import LLMManager
        from ..prompts.incoming_agent import get_stage3_judge_prompt
        from ..core.conversation_analyzer import analyze_sender_risk

        # 대화 이력 분석
        history_days = 0
        history_count = 0
        is_saved_contact = False

        if user_id and sender_id:
            sender_analysis = analyze_sender_risk(user_id, sender_id, text)
            history_days = sender_analysis.get("sender_trust", {}).get("relationship_days", 0)
            history_count = sender_analysis.get("sender_trust", {}).get("message_count", 0)
            is_saved_contact = sender_analysis.get("sender_trust", {}).get("is_saved_contact", False)
        elif conversation_history:
            history_count = len(conversation_history)

        # 유사 사례 검색 (간단한 구현)
        similar_cases = self._search_similar_cases(text, stage2.get("category"))

        # Stage 3 프롬프트 생성
        stage1_result = f"DB 조회: {'HIT' if stage1.get('db_hit') else 'MISS'}"
        if stage1.get("db_hit"):
            stage1_result += f" (신고 {stage1.get('report_count', 0)}건)"

        try:
            llm = LLMManager.get("instruct")
            if not llm:
                print("[Stage 3] LLM not available, using rule-based judgment")
                return self._stage3_rule_fallback(stage1, stage2, history_days, is_saved_contact)

            prompt = get_stage3_judge_prompt(
                message=text,
                stage1_result=stage1_result,
                stage2_category=stage2.get("category", "NORMAL"),
                stage2_source=stage2.get("government_source", ""),
                stage2_patterns=", ".join(stage2.get("matched_patterns", [])),
                stage2_reasoning=stage2.get("reasoning", ""),
                stage2_confidence=stage2.get("confidence", 0),
                history_days=history_days,
                history_count=history_count,
                is_saved_contact=is_saved_contact,
                similar_cases=similar_cases
            )

            response = llm.analyze(prompt)
            result = self._parse_llm_json_response(response)

            return {
                "stage": 3,
                "risk_level": result.get("risk_level", "SUSPICIOUS"),
                "confidence": result.get("confidence", 0.5),
                "summary.md": result.get("summary.md", ""),
                "stage1_analysis": result.get("stage1_analysis", ""),
                "stage2_analysis": result.get("stage2_analysis", ""),
                "history_analysis": result.get("history_analysis", ""),
                "similar_cases_analysis": result.get("similar_cases_analysis", ""),
                "final_reasoning": result.get("final_reasoning", ""),
                "recommended_action": result.get("recommended_action", {}),
                "llm_used": True
            }

        except Exception as e:
            print(f"[Stage 3] AI Judge error: {e}, using rule-based judgment")
            return self._stage3_rule_fallback(stage1, stage2, history_days, is_saved_contact)

    def _stage3_rule_fallback(
        self,
        stage1: dict,
        stage2: dict,
        history_days: int,
        is_saved_contact: bool
    ) -> dict:
        """Stage 3 AI 실패 시 Rule-based 폴백"""
        category = stage2.get("category", "NORMAL")
        confidence = stage2.get("confidence", 0.5)

        # 위험도 결정 로직 (ver9.0 기준)
        # 1. DB HIT → CRITICAL
        # 2. NORMAL → SAFE
        # 3. 스미싱 유형 (A/B/C) + 고신뢰도 → DANGEROUS
        # 4. 스미싱 유형 + 저신뢰도 → SUSPICIOUS
        # 5. 기타 → SAFE
        if stage1.get("db_hit"):
            risk_level = "CRITICAL"
        elif category == "NORMAL":
            risk_level = "SAFE"
        elif category in ["A-1", "A-2", "A-3", "B-1", "B-2", "B-3", "C-1", "C-2", "C-3"]:
            # 모든 스미싱 유형: 고신뢰도(0.7 이상)면 DANGEROUS
            # 신뢰도 + 대화 이력 고려
            if confidence >= 0.7:
                # 초면(7일 미만) 또는 연락처 미저장 → DANGEROUS
                if history_days < 7 or not is_saved_contact:
                    risk_level = "DANGEROUS"
                else:
                    # 장기 관계(7일 이상) + 연락처 저장 → SUSPICIOUS
                    risk_level = "SUSPICIOUS"
            else:
                # 저신뢰도 → SUSPICIOUS
                risk_level = "SUSPICIOUS"
        else:
            risk_level = "SUSPICIOUS" if confidence >= 0.5 else "SAFE"

        return {
            "stage": 3,
            "risk_level": risk_level,
            "confidence": confidence,
            "summary.md": f"Rule-based 판정: {category} → {risk_level}",
            "final_reasoning": f"Stage 2 분류 결과({category}, 신뢰도 {confidence:.2f})와 대화 이력({history_days}일)을 기반으로 판정",
            "llm_used": False
        }

    def _generate_keyword_hints(self, text: str) -> dict:
        """
        키워드 힌트 생성 (Rule-based)

        9개 유형별 키워드 매칭하여 힌트 생성
        AI Agent가 참고용으로만 사용
        """
        # 9개 유형별 키워드 (정부 통계 기반)
        category_keywords = {
            "A-1": {
                "keywords": ["엄마", "아빠", "아들", "딸", "폰 고장", "액정", "급해", "계좌", "송금", "인증번호", "앱 설치", "비밀로", "초기화", "번호가 날아", "계정 새로", "부탁드릴", "대리", "과장", "부장", "팀장"],
                "source": "금감원 2023: 가족사칭 33.7%"
            },
            "A-2": {
                "keywords": ["청첩장", "부고", "결혼", "장례", "식장"],
                "source": "KISA 2023: 경조사 1.7만건"
            },
            "A-3": {
                "keywords": ["사귀자", "좋아해", "보고싶어", "돈 빌려", "통관비", "항공료", "번호 잘못", "잘못 저장", "친구로 지내", "친구가 없", "한국에 친구", "일본에서", "해외에서", "프로필이 좋", "인상이 좋"],
                "source": "경찰청 2023: 로맨스 스캠"
            },
            "B-1": {
                "keywords": ["검찰", "경찰", "금감원", "범죄", "수사", "압수", "동결"],
                "source": "경찰청 2022: 기관사칭 78%"
            },
            "B-2": {
                "keywords": ["건강검진", "국민연금", "과태료", "미납", "세금"],
                "source": "경찰청 2023: 공공알림 19.7배↑"
            },
            "B-3": {
                "keywords": ["택배", "배송", "주소", "반송", "운송장", "CJ대한통운", "우체국", "당근", "당근마켓", "중고나라", "번개장터", "안전결제", "안전거래", "링크 보내", "택배 거래"],
                "source": "KISA: 택배 65%"
            },
            "C-1": {
                "keywords": ["대출", "저금리", "정부지원", "승인", "한도"],
                "source": "금감원 2023: 대출 35.2%"
            },
            "C-2": {
                "keywords": ["리딩방", "투자", "수익", "코인", "주식", "세력"],
                "source": "국수본: 투자 5,340억"
            },
            "C-3": {
                "keywords": ["영상통화", "화질", "앱 깔아", "유포", "협박"],
                "source": "경찰청: 몸캠피싱"
            }
        }

        hints = {}
        text_lower = text.lower()

        for category, data in category_keywords.items():
            matched = [kw for kw in data["keywords"] if kw in text_lower or kw in text]
            if matched:
                score = min(len(matched) / 3, 1.0)  # 3개 이상이면 1.0
                hints[category] = {
                    "keywords": matched,
                    "score": score,
                    "source": data["source"]
                }

        return hints

    # =========================================================================
    # RAG 유사 사례 검색 (ver9.0)
    # =========================================================================

    _case_store = None  # 싱글톤 패턴으로 한 번만 로드

    @classmethod
    def _load_case_store(cls) -> list:
        """
        threat_patterns.json에서 sample_messages 로드

        Returns:
            list: [{category, name_ko, message, keywords}, ...]
        """
        if cls._case_store is not None:
            return cls._case_store

        import os
        patterns_path = os.path.join(
            os.path.dirname(__file__),
            "..", "data", "threat_patterns.json"
        )

        try:
            with open(patterns_path, "r", encoding="utf-8") as f:
                patterns = json.load(f)

            cls._case_store = []

            # categories에서 sample_messages 추출
            for cat_key, cat_data in patterns.get("categories", {}).items():
                for pattern_key, pattern_data in cat_data.get("patterns", {}).items():
                    sample_messages = pattern_data.get("sample_messages", [])
                    keywords = pattern_data.get("keywords", []) + pattern_data.get("context_keywords", [])

                    for msg in sample_messages:
                        cls._case_store.append({
                            "category": pattern_key,
                            "name_ko": pattern_data.get("name_ko", ""),
                            "message": msg,
                            "keywords": keywords,
                            "risk_score": pattern_data.get("risk_score", 50)
                        })

            print(f"[RAG] Case store loaded: {len(cls._case_store)} cases")
            return cls._case_store

        except Exception as e:
            print(f"[RAG] Failed to load case store: {e}")
            cls._case_store = []
            return cls._case_store

    def _tokenize(self, text: str) -> set:
        """
        한국어 텍스트 토큰화 (공백 + 2-gram)

        Args:
            text: 입력 텍스트

        Returns:
            set: 토큰 집합
        """
        import re
        # 특수문자 제거, 소문자 변환
        cleaned = re.sub(r'[^\w\s가-힣]', ' ', text.lower())
        words = cleaned.split()

        tokens = set(words)

        # 2-gram 추가 (연속된 두 단어)
        for i in range(len(words) - 1):
            tokens.add(f"{words[i]} {words[i+1]}")

        return tokens

    def _calculate_similarity(self, text1: str, text2: str, keywords: list = None) -> float:
        """
        Jaccard 유사도 계산 + 키워드 부스트

        Args:
            text1: 입력 텍스트
            text2: 비교 대상 텍스트
            keywords: 카테고리 키워드 (부스트용)

        Returns:
            float: 유사도 (0.0 ~ 1.0)
        """
        tokens1 = self._tokenize(text1)
        tokens2 = self._tokenize(text2)

        # Jaccard 유사도
        intersection = tokens1 & tokens2
        union = tokens1 | tokens2

        if not union:
            return 0.0

        base_similarity = len(intersection) / len(union)

        # 키워드 부스트: 입력 텍스트에 키워드가 있으면 유사도 증가
        keyword_boost = 0.0
        if keywords:
            matched_keywords = sum(1 for kw in keywords if kw in text1)
            if matched_keywords > 0:
                keyword_boost = min(0.3, matched_keywords * 0.05)  # 최대 0.3 부스트

        return min(1.0, base_similarity + keyword_boost)

    def _search_similar_cases(self, text: str, category: str) -> str:
        """
        RAG 기반 유사 사례 검색

        Args:
            text: 분석할 메시지
            category: Stage 2에서 판단한 카테고리 (우선순위 부스트용)

        Returns:
            str: 유사 사례 정보 (Stage 3 프롬프트에 포함)
        """
        if not text or not text.strip():
            return "유사 사례 없음"

        # Case store 로드
        case_store = self._load_case_store()
        if not case_store:
            return "유사 사례 DB 로드 실패"

        # 유사도 계산
        similarities = []
        for case in case_store:
            sim = self._calculate_similarity(text, case["message"], case["keywords"])

            # 카테고리 일치 시 부스트 (+0.2)
            if category and case["category"] == category:
                sim = min(1.0, sim + 0.2)

            similarities.append({
                "category": case["category"],
                "name_ko": case["name_ko"],
                "message": case["message"][:50] + "..." if len(case["message"]) > 50 else case["message"],
                "similarity": sim,
                "risk_score": case["risk_score"]
            })

        # 유사도 상위 3개 정렬
        top_cases = sorted(similarities, key=lambda x: x["similarity"], reverse=True)[:3]

        # 유사도 임계값 (0.15 이상만 반환)
        relevant_cases = [c for c in top_cases if c["similarity"] >= 0.15]

        if not relevant_cases:
            return "최근 유사 사례 없음"

        # 결과 포맷팅
        result_lines = [f"유사 사례 발견 ({len(relevant_cases)}건):"]
        for i, case in enumerate(relevant_cases, 1):
            sim_pct = int(case["similarity"] * 100)
            result_lines.append(
                f"{i}. [{case['category']} {case['name_ko']}] \"{case['message']}\" "
                f"(유사도: {sim_pct}%, 위험도: {case['risk_score']})"
            )

        return "\n".join(result_lines)

    def _parse_llm_json_response(self, response: str) -> dict:
        """LLM 응답에서 JSON 파싱"""
        try:
            # JSON 블록 추출
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0].strip()
            elif "{" in response:
                # { } 사이의 내용 추출
                start = response.find("{")
                end = response.rfind("}") + 1
                json_str = response[start:end]
            else:
                json_str = response

            return json.loads(json_str)
        except json.JSONDecodeError as e:
            print(f"[IncomingAgent] JSON parse error: {e}")
            return {}

    def _convert_v9_result_to_response(self, result: dict) -> AnalysisResponse:
        """ver9.0 3-Stage 결과를 AnalysisResponse로 변환"""
        stage2 = result.get("stage2") or {}
        stage3 = result.get("stage3") or {}

        final_level = result.get("final_risk_level", "SAFE")

        # RiskLevel 변환
        level_map = {
            "SAFE": RiskLevel.LOW,
            "SUSPICIOUS": RiskLevel.MEDIUM,
            "DANGEROUS": RiskLevel.HIGH,
            "CRITICAL": RiskLevel.CRITICAL
        }
        risk_level = level_map.get(final_level, RiskLevel.LOW)

        # 카테고리 정보
        category = stage2.get("category")
        category_name = self._get_category_name(category)

        # 사기 확률 계산
        confidence = stage2.get("confidence", 0) if stage2 else 0
        scam_probability = int(confidence * 100) if category != "NORMAL" else 0

        # 이유 목록 생성
        reasons = []

        # Stage 2 분류 근거
        if stage2.get("reasoning"):
            reasons.append(stage2["reasoning"])

        # Stage 3 요약
        if stage3.get("summary.md"):
            reasons.append(stage3["summary.md"])

        # Stage 1 DB HIT
        stage1 = result.get("stage1") or {}
        if stage1.get("db_hit"):
            reasons.insert(0, f"신고된 계좌/전화번호가 포함되어 있습니다! (신고 {stage1.get('report_count', 0)}건)")

        # 기본 메시지
        if not reasons:
            if final_level == "SAFE":
                reasons.append("안전한 메시지입니다.")
            else:
                reasons.append("위험 요소가 감지되었습니다.")

        # 권장 조치
        action_map = {
            "SAFE": "표시",
            "SUSPICIOUS": "주의 표시",
            "DANGEROUS": "강력 경고",
            "CRITICAL": "차단 및 신고"
        }
        recommended_action = action_map.get(final_level, "표시")

        return AnalysisResponse(
            risk_level=risk_level,
            reasons=reasons,
            recommended_action=recommended_action,
            is_secret_recommended=False,
            category=category,
            category_name=category_name,
            scam_probability=scam_probability
        )

    def _get_category_name(self, category: str) -> str:
        """카테고리 코드를 한글명으로 변환"""
        names = {
            "A-1": "지인/가족 사칭",
            "A-2": "경조사 빙자",
            "A-3": "로맨스 스캠",
            "B-1": "수사/금융 기관 사칭",
            "B-2": "공공 행정 알림 사칭",
            "B-3": "택배/물류 사칭",
            "C-1": "대출 빙자",
            "C-2": "투자 리딩방",
            "C-3": "몸캠 피싱",
            "NORMAL": "일상 대화"
        }
        return names.get(category, "알 수 없음")

    # =========================================================================
    # Legacy 4-Stage Pipeline (하위 호환)
    # =========================================================================

    def _analyze_4_stages(
        self,
        text: str,
        user_id: int = None,
        sender_id: int = None,
        conversation_history: list = None,
        use_ai: bool = True
    ) -> dict:
        """
        4단계 완전 분석 파이프라인

        v2.0: 대화 히스토리 기반 맥락 분석 지원

        Stage 1: 텍스트 패턴 분석 + 대화 흐름 분석
        Stage 2: 사기 신고 DB 조회
        Stage 3: 발신자 신뢰도 분석
        Stage 4: 정책 기반 최종 판정
        """
        from ..core.scam_checker import check_scam_in_message
        from ..core.conversation_analyzer import analyze_sender_risk
        from ..core.action_policy import get_combined_policy, format_warning_for_ui

        # ========== Stage 1: 텍스트 패턴 분석 + AI 분석 + 대화 흐름 분석 ==========
        print(f"[IncomingAgent] Stage 1: 텍스트 패턴 분석 (use_ai={use_ai})...")

        # use_ai=True면 Hybrid Analyzer (Rule + LLM) 사용
        if use_ai:
            from ..core.hybrid_threat_analyzer import HybridThreatAnalyzer
            hybrid = HybridThreatAnalyzer()
            # 대화 맥락을 Hybrid Analyzer에 전달 (SE-OmniGuard 연구 기반)
            hybrid_result = hybrid.analyze(
                text,
                use_llm=True,
                conversation_history=conversation_history  # 대화 맥락 전달!
            )
            print(f"[IncomingAgent] Hybrid 분석 결과: llm_used={hybrid_result.get('llm_used')}, context_analyzed={hybrid_result.get('context_analyzed', False)}")

            # Hybrid 결과를 stage1 형식으로 변환
            stage1 = self._convert_hybrid_to_stage1(hybrid_result, text)
        else:
            # Rule-based만 분석 (단일 메시지)
            stage1 = analyze_incoming_message(text)

        # 대화 흐름 분석 (히스토리가 있는 경우)
        flow_analysis = None
        if conversation_history and len(conversation_history) > 1:
            from ..core.threat_matcher import analyze_conversation_flow
            flow_analysis = analyze_conversation_flow(conversation_history, sender_id)
            print(f"[IncomingAgent] 대화 흐름 분석 결과: {flow_analysis}")

            # 대화 흐름에서 사기 패턴이 감지되면 확률 조정
            if flow_analysis and flow_analysis.get("flow_matched"):
                flow_multiplier = flow_analysis.get("probability_multiplier", 1.0)
                original_prob = stage1.get("final_assessment", {}).get("scam_probability", 0)
                adjusted_prob = min(int(original_prob * flow_multiplier), 100)

                # 흐름 분석으로 확률이 상승한 경우
                if adjusted_prob > original_prob:
                    stage1["final_assessment"]["scam_probability"] = adjusted_prob
                    stage1["final_assessment"]["flow_boost"] = True
                    stage1["final_assessment"]["flow_pattern"] = flow_analysis.get("matched_flow")
                    print(f"[IncomingAgent] 대화 흐름으로 확률 조정: {original_prob}% → {adjusted_prob}%")
        # analyze_incoming_message는 risk_level을 반환 (safe/low/medium/high/critical)
        risk_level_raw = stage1.get("final_assessment", {}).get("risk_level", "safe")
        # 소문자 → 대문자 변환 (SAFE → safe 호환)
        level_to_threat = {
            "safe": "SAFE",
            "low": "SAFE",
            "medium": "SUSPICIOUS",
            "high": "DANGEROUS",
            "critical": "CRITICAL"
        }
        threat_level = level_to_threat.get(risk_level_raw.lower(), "SAFE") if isinstance(risk_level_raw, str) else "SAFE"
        print(f"[IncomingAgent] Stage 1 Rule-based: risk_level={risk_level_raw} → threat_level={threat_level}")
        print(f"[IncomingAgent] Stage 1 결과: threat_level={threat_level}")

        # ========== Stage 2: 사기 신고 DB 조회 ==========
        print("[IncomingAgent] Stage 2: 사기 신고 DB 조회...")
        stage2 = check_scam_in_message(text)
        print(f"[IncomingAgent] Stage 2 결과: has_reported={stage2.get('has_reported_identifier')}")

        # ========== Stage 3: 발신자 신뢰도 분석 ==========
        stage3 = None
        if user_id and sender_id:
            print(f"[IncomingAgent] Stage 3: 발신자 신뢰도 분석 (user={user_id}, sender={sender_id})...")
            stage3 = analyze_sender_risk(user_id, sender_id, text)
            print(f"[IncomingAgent] Stage 3 결과: trust_level={stage3.get('sender_trust', {}).get('trust_level')}")
        else:
            print("[IncomingAgent] Stage 3: 스킵 (user_id/sender_id 없음)")

        # ========== Stage 4: 정책 기반 최종 판정 ==========
        print("[IncomingAgent] Stage 4: 정책 기반 최종 판정...")

        # 시나리오 매칭 확인
        scenario_match = None
        if stage1.get("scenario_match", {}).get("matched_scenario"):
            scenario_match = stage1["scenario_match"]["matched_scenario"].get("id")

        # threat_level → risk_level 변환 (action_policy가 기대하는 형식)
        level_convert = {
            "SAFE": "LOW",
            "SUSPICIOUS": "MEDIUM",
            "DANGEROUS": "HIGH",
            "CRITICAL": "CRITICAL"
        }
        risk_level_for_policy = level_convert.get(threat_level, "LOW")

        stage4 = get_combined_policy(
            text_risk=risk_level_for_policy,
            scam_check_result=stage2,
            sender_analysis=stage3,
            scenario_match=scenario_match
        )

        final_level = stage4["final_risk_level"]
        print(f"[IncomingAgent] Stage 4 결과: final_risk_level={final_level}, score={stage4.get('total_risk_score')}")

        # 결과 통합
        return {
            "stage1_threat_detection": stage1,
            "stage2_scam_check": stage2,
            "stage3_sender_trust": stage3,
            "stage4_final_policy": stage4,
            "final_risk_level": final_level,
            "ui_warning": format_warning_for_ui(stage4["policy"])
        }

    def _convert_full_result_to_response(self, result: dict) -> AnalysisResponse:
        """4단계 분석 결과를 AnalysisResponse로 변환"""
        stage1 = result.get("stage1_threat_detection", {})
        stage2 = result.get("stage2_scam_check", {})
        stage3 = result.get("stage3_sender_trust")
        stage4 = result.get("stage4_final_policy", {})

        final_level = result.get("final_risk_level", "LOW")

        # RiskLevel 변환
        level_map = {
            "LOW": RiskLevel.LOW,
            "MEDIUM": RiskLevel.MEDIUM,
            "HIGH": RiskLevel.HIGH,
            "CRITICAL": RiskLevel.CRITICAL
        }
        risk_level = level_map.get(final_level, RiskLevel.LOW)

        # MECE 카테고리 정보 추출
        summary = stage1.get("summary.md", {})
        category = summary.get("category")  # A-1, B-2 등
        category_name = summary.get("pattern")  # 가족 사칭 (액정 파손) 등

        # 사기 확률 추출
        final_assessment = stage1.get("final_assessment", {})
        scam_probability = final_assessment.get("scam_probability", 0)

        # 이유 목록 생성
        reasons = []

        # Stage 1: 위협 감지 이유
        threat_detection = stage1.get("threat_detection", {})
        for threat in threat_detection.get("found_threats", [])[:2]:
            reasons.append(f"{threat.get('name_ko', '위협')} 패턴 감지")

        # 시나리오 매칭
        scenario = stage1.get("scenario_match", {})
        if scenario.get("matched_scenario"):
            reasons.append(f"'{scenario['matched_scenario'].get('name_ko', '')}' 시나리오와 일치")

        # Stage 2: 신고 DB 결과
        if stage2.get("has_reported_identifier"):
            if stage2.get("reported_accounts"):
                reasons.append("신고된 계좌번호가 포함되어 있습니다!")
            if stage2.get("reported_phones"):
                reasons.append("신고된 전화번호가 포함되어 있습니다!")

        # Stage 3: 발신자 신뢰도
        if stage3:
            warning = stage3.get("warning_message")
            if warning:
                reasons.append(warning)

        # 경고 메시지 추가
        assessment = stage1.get("final_assessment", {})
        warning_msg = assessment.get("warning_message", "")
        if warning_msg and warning_msg not in reasons:
            reasons.insert(0, warning_msg)

        # 이유가 없으면 기본 메시지
        if not reasons:
            if final_level == "LOW":
                reasons.append("안전한 메시지입니다.")
            else:
                reasons.append("위험 요소가 감지되었습니다.")

        # 권장 조치
        policy = stage4.get("policy", {})
        action_type = policy.get("action_type", "none")
        action_map = {
            "none": "표시",
            "info": "정보 표시",
            "warn": "주의 표시",
            "strong_warn": "강력 경고",
            "block_recommend": "차단 권장",
            "block_and_report": "차단 및 신고"
        }
        recommended_action = action_map.get(str(action_type), str(action_type))

        return AnalysisResponse(
            risk_level=risk_level,
            reasons=reasons,
            recommended_action=recommended_action,
            is_secret_recommended=False,
            category=category,
            category_name=category_name,
            scam_probability=scam_probability
        )

    def _convert_hybrid_to_stage1(self, hybrid_result: dict, text: str) -> dict:
        """
        HybridThreatAnalyzer 결과를 stage1 형식으로 변환

        Hybrid 결과 형식:
        - threat_level: SAFE/SUSPICIOUS/DANGEROUS/CRITICAL
        - threat_score: int
        - is_likely_scam: bool
        - detected_threats: list
        - llm_used: bool

        Stage1 형식 (analyze_incoming_message 호환):
        - final_assessment: {scam_probability, risk_level, ...}
        - threat_detection: {found_threats, ...}
        """
        threat_level = hybrid_result.get("threat_level", "SAFE")
        threat_score = hybrid_result.get("threat_score", 0)

        # threat_level → risk_level 변환
        level_map = {
            "SAFE": "safe",
            "SUSPICIOUS": "medium",
            "DANGEROUS": "high",
            "CRITICAL": "critical"
        }
        risk_level = level_map.get(threat_level, "safe")

        # threat_score → scam_probability (0-100)
        scam_probability = min(threat_score, 100) if threat_score else 0

        # LLM이 위험으로 판단하면 최소 확률 보장
        if hybrid_result.get("llm_used") and hybrid_result.get("is_likely_scam"):
            scam_probability = max(scam_probability, 60)

        # detected_threats에서 카테고리 추출
        detected_threats = hybrid_result.get("detected_threats", [])
        matched_category = None
        matched_pattern = None
        pattern_name = None

        if detected_threats:
            first_threat = detected_threats[0]
            matched_pattern = first_threat.get("id", "")
            matched_category = matched_pattern.split("-")[0] if "-" in str(matched_pattern) else None
            pattern_name = first_threat.get("name_ko", "")

        # 응답 템플릿
        response_templates = {
            "safe": {"message": "안전한 메시지입니다.", "action": "none", "color": "green"},
            "medium": {"message": "주의가 필요한 메시지입니다.", "action": "warn", "color": "yellow"},
            "high": {"message": "위험한 메시지입니다!", "action": "strong_warn", "color": "orange"},
            "critical": {"message": "피싱/사기 메시지로 강력히 의심됩니다!", "action": "block_recommend", "color": "red"}
        }
        template = response_templates.get(risk_level, response_templates["safe"])

        return {
            "text": text[:100] + "..." if len(text) > 100 else text,
            "threat_detection": {
                "found_threats": detected_threats,
                "matched_patterns": detected_threats
            },
            "url_analysis": hybrid_result.get("url_analysis", {}),
            "scenario_match": hybrid_result.get("scenario_match", {}),
            "final_assessment": {
                "scam_probability": scam_probability,
                "risk_level": risk_level,
                "matched_category": matched_category,
                "matched_pattern": matched_pattern,
                "pattern_name": pattern_name or "안전",
                "warning_message": template["message"],
                "recommended_action": template["action"],
                "display_color": template["color"],
                "llm_used": hybrid_result.get("llm_used", False),
                "analysis_time_ms": hybrid_result.get("analysis_time_ms", 0)
            },
            "summary.md": {
                "probability": f"{scam_probability}%",
                "category": matched_pattern,
                "category_main": matched_category,
                "pattern": pattern_name or "안전",
                "warning": template["message"]
            }
        }

    # Legacy 메서드 (호환성 유지)
    def _analyze_rule_based(self, text: str) -> AnalysisResponse:
        """Rule-based 분석 (legacy)"""
        result = analyze_incoming_message(text)
        return self._convert_to_response(result)

    def _analyze_with_hybrid(self, text: str) -> AnalysisResponse:
        """Hybrid 분석 (legacy)"""
        try:
            from ..core.hybrid_threat_analyzer import hybrid_threat_analyze
            result = hybrid_threat_analyze(text, use_llm=True)
            return self._convert_to_response(result)
        except Exception as e:
            print(f"[IncomingAgent] Hybrid analysis error: {e}")
            return self._analyze_rule_based(text)

    def _convert_to_response(self, result: dict) -> AnalysisResponse:
        """Legacy 변환 메서드"""
        assessment = result.get("final_assessment", result)
        threat_level = assessment.get("threat_level", "SAFE")

        level_map = {
            "SAFE": RiskLevel.LOW,
            "SUSPICIOUS": RiskLevel.MEDIUM,
            "DANGEROUS": RiskLevel.HIGH,
            "CRITICAL": RiskLevel.CRITICAL
        }
        risk_level = level_map.get(threat_level, RiskLevel.LOW)

        reasons = []
        threat_detection = result.get("threat_detection", {})
        for threat in threat_detection.get("found_threats", [])[:3]:
            reasons.append(f"{threat.get('name_ko', '위협')} 패턴 감지")

        warning = assessment.get("warning_message", "")
        if warning:
            reasons.insert(0, warning)

        action = assessment.get("recommended_action", "none")
        action_map = {
            "none": "표시",
            "warn": "주의 표시",
            "block_recommended": "차단 권장",
            "block_and_report": "차단 및 신고"
        }

        return AnalysisResponse(
            risk_level=risk_level,
            reasons=reasons,
            recommended_action=action_map.get(action, action),
            is_secret_recommended=False
        )
