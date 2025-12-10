"""
MCP Tools - FastMCP 기반 도구 정의
AI가 호출할 수 있는 모든 분석 도구를 제공

Agent A (발신 보호): PII 감지 도구
Agent B (수신 보호): 피싱/사기 위협 감지 도구
"""
from mcp.server.fastmcp import FastMCP
from typing import Dict, List, Any
from ..core.models import RiskLevel, AnalysisResponse

# === MCP 메트릭 (선택적 로드) ===
_kat_metrics = None
try:
    import sys
    from pathlib import Path
    # ops/monitoring/metrics 경로 추가
    _monitoring_path = Path(__file__).parent.parent.parent / "ops" / "monitoring"
    if _monitoring_path.exists():
        sys.path.insert(0, str(_monitoring_path))
        from metrics import kat_metrics as _kat_metrics
        print("[MCP Tools] 메트릭 모듈 로드 성공")
except ImportError:
    print("[MCP Tools] 메트릭 모듈 없음 (무시됨)")

# Agent A (발신 보호) - PII 패턴 매칭
from ..core.pattern_matcher import (
    get_pii_patterns,
    get_document_types,
    get_combination_rules,
    detect_pii,
    detect_document_type,
    calculate_risk,
    get_risk_action
)

# Agent B (수신 보호) - 위협 패턴 매칭
from ..core.threat_matcher import (
    get_threat_categories,
    get_known_scam_scenarios,
    detect_threats,
    detect_urls,
    match_scam_scenario,
    calculate_threat_score,
    analyze_incoming_message,
    get_threat_response
)

# NOTE: Agent와 LLM은 순환 import 방지를 위해 함수 내부에서 lazy import

# MCP 서버 인스턴스
mcp = FastMCP("DualGuard")

# Agent 인스턴스 (매번 새로 생성 - 코드 변경 시 리로드 보장)
def _get_outgoing_agent():
    """OutgoingAgent 인스턴스 생성"""
    from ..agents.outgoing import OutgoingAgent
    return OutgoingAgent()


def _get_incoming_agent():
    """IncomingAgent 인스턴스 생성"""
    from ..agents.incoming import IncomingAgent
    return IncomingAgent()


@mcp.tool()
def analyze_outgoing(text: str, use_ai: bool = True) -> AnalysisResponse:
    """
    Analyze outgoing message for sensitive information.
    발신 메시지의 민감정보(계좌번호, 주민번호 등)를 감지합니다.

    하이브리드 분석:
    - Rule-based 패턴 매칭 (항상 실행)
    - AI 분석 (use_ai=True, 추가 실행)
    - 둘 중 높은 위험도 사용

    Args:
        text: 분석할 메시지 내용
        use_ai: 하이브리드 분석 활성화 (기본: True)

    Returns:
        AnalysisResponse: 위험도, 감지 이유, 권장 조치
    """
    # MCP 메트릭 기록
    if _kat_metrics:
        with _kat_metrics.measure_mcp_call("analyze_outgoing"):
            agent = _get_outgoing_agent()
            return agent.analyze(text, use_ai=use_ai)
    else:
        agent = _get_outgoing_agent()
        return agent.analyze(text, use_ai=use_ai)


@mcp.tool()
def analyze_incoming(
    text: str,
    sender_id: str = None,
    user_id: str = None,
    conversation_history: List[Dict] = None,
    use_ai: bool = False
) -> AnalysisResponse:
    """
    Analyze incoming message for phishing or scams.
    수신 메시지의 피싱/사기 위협을 탐지합니다.

    v2.0: 대화 히스토리 기반 맥락 분석 지원
    - conversation_history: 최근 대화 목록 (시간순)
    - Agent B가 대화 흐름을 분석하여 사기 "가능성"을 판단
    - 단일 메시지가 아닌 전체 대화 맥락을 봄

    Args:
        text: 분석할 메시지 내용
        sender_id: 발신자 ID (선택)
        user_id: 수신자 ID (선택)
        conversation_history: 대화 히스토리 [{sender_id, message, timestamp}]
        use_ai: Kanana Safeguard AI 사용 여부 (기본: False)

    Returns:
        AnalysisResponse: 위험도, 감지 이유, 권장 조치
    """
    # MCP 메트릭 기록
    if _kat_metrics:
        with _kat_metrics.measure_mcp_call("analyze_incoming"):
            agent = _get_incoming_agent()
            return agent.analyze(
                text,
                sender_id=sender_id,
                user_id=user_id,
                conversation_history=conversation_history,
                use_ai=use_ai
            )
    else:
        agent = _get_incoming_agent()
        return agent.analyze(
            text,
            sender_id=sender_id,
            user_id=user_id,
            conversation_history=conversation_history,
            use_ai=use_ai
        )


@mcp.tool()
def analyze_image(image_path: str, use_ai: bool = True) -> AnalysisResponse:
    """
    Analyze text within an image using Kanana Vision Model.
    이미지 내 텍스트를 추출하여 민감정보를 분석합니다.

    순차 처리 (GPU 메모리 효율화):
    1. Kanana Vision (3B) → 이미지에서 텍스트 추출 (OCR)
    2. Vision 언로드 → GPU 메모리 해제
    3. 추출된 텍스트 → 2-Tier 분석 (빠른 필터링 → LLM 정밀 분석)

    Args:
        image_path: 이미지 파일 경로
        use_ai: 텍스트 분석에 Kanana Instruct 사용 여부 (기본: True)
                2-Tier 방식으로 의심 메시지에만 LLM 호출됨

    Returns:
        AnalysisResponse: 위험도, 감지 이유, 권장 조치
    """
    # MCP 메트릭 시작
    if _kat_metrics:
        _kat_metrics.mcp_active.labels(tool_name="analyze_image").inc()

    import time
    start_time = time.time()
    status = "success"

    try:
        # Step 1: Vision 모델로 OCR (lazy import)
        from ..llm.kanana import LLMManager
        print("[analyze_image] Step 1: Loading Vision model for OCR...")
        vision_model = LLMManager.get("vision")
        if not vision_model:
            status = "error"
            return AnalysisResponse(
                risk_level=RiskLevel.LOW,
                reasons=["Vision Model loading failed"],
                recommended_action="시스템 관리자에게 문의하세요",
                is_secret_recommended=False
            )

        # Extract text using Kanana Vision
        extracted_text = vision_model.analyze_image(image_path)
        print(f"[analyze_image] OCR Result: {extracted_text[:200]}..." if len(extracted_text) > 200 else f"[analyze_image] OCR Result: {extracted_text}")

        # Step 2: 텍스트 분석 (2-Tier 방식)
        # - Tier 1: 빠른 필터링 (숫자/키워드 패턴 체크)
        # - Tier 2: 의심 메시지만 LLM 정밀 분석
        # LLMManager.sequential_mode=True이므로 Instruct 로드 시 Vision 자동 언로드
        print(f"[analyze_image] Step 2: Analyzing extracted text (use_ai={use_ai})...")
        return analyze_outgoing(extracted_text, use_ai=use_ai)

    except Exception as e:
        status = "error"
        return AnalysisResponse(
            risk_level=RiskLevel.LOW,
            reasons=[f"이미지 분석 중 오류 발생: {str(e)}"],
            recommended_action="분석 실패",
            is_secret_recommended=False
        )
    finally:
        # MCP 메트릭 기록
        if _kat_metrics:
            _kat_metrics.mcp_active.labels(tool_name="analyze_image").dec()
            duration = time.time() - start_time
            _kat_metrics.mcp_duration.labels(tool_name="analyze_image").observe(duration)
            _kat_metrics.mcp_calls.labels(tool_name="analyze_image", status=status).inc()


# ============================================================
# Pattern Matcher MCP Tools - AI가 직접 호출하는 분석 도구
# ============================================================

@mcp.tool()
def list_pii_patterns() -> Dict[str, Any]:
    """
    List all PII patterns that can be detected.
    감지 가능한 모든 개인정보(PII) 패턴 목록을 반환합니다.

    AI가 어떤 종류의 민감정보를 감지할 수 있는지 파악하는 데 사용합니다.

    Returns:
        카테고리별 PII 패턴 정보 (id, name_ko, risk_level, requires_ai)
    """
    return get_pii_patterns()


@mcp.tool()
def list_document_types() -> List[Dict]:
    """
    List all document types for image detection.
    이미지에서 감지 가능한 문서 유형 목록을 반환합니다.

    Vision OCR로 추출한 텍스트에서 서류 종류를 식별하는 데 사용합니다.
    (예: 주민등록증, 여권, 운전면허증 등)

    Returns:
        문서 유형 목록 (id, name_ko, risk_level, keywords)
    """
    return get_document_types()


@mcp.tool()
def get_risk_rules() -> Dict[str, Any]:
    """
    Get combination rules and auto-escalation rules.
    위험도 조합 규칙과 자동 상향 규칙을 반환합니다.

    여러 민감정보가 함께 있을 때 위험도가 어떻게 상향되는지 파악하는 데 사용합니다.
    (예: 이름+주민번호 조합 → CRITICAL)

    Returns:
        combination_rules: 조합 규칙
        auto_escalation: 자동 상향 규칙 (개수 기반, 카테고리 조합)
    """
    return get_combination_rules()


@mcp.tool()
def scan_pii(text: str) -> Dict[str, Any]:
    """
    Scan text for PII using regex patterns.
    정규식 패턴으로 텍스트에서 개인정보(PII)를 스캔합니다.

    빠른 1차 필터링에 사용합니다. requires_ai=true 항목은 별도 AI 분석 필요.

    Args:
        text: 분석할 텍스트

    Returns:
        found_pii: 감지된 PII 목록 [{id, category, value, risk_level, name_ko}]
        categories_found: 감지된 카테고리 목록
        highest_risk: 가장 높은 위험도
        count: 감지된 PII 개수
    """
    return detect_pii(text)


@mcp.tool()
def identify_document(ocr_text: str) -> Dict[str, Any]:
    """
    Identify document type from OCR text.
    OCR로 추출한 텍스트에서 문서 유형을 식별합니다.

    Vision 모델이 추출한 텍스트를 입력받아 어떤 종류의 서류인지 판별합니다.

    Args:
        ocr_text: OCR로 추출한 텍스트

    Returns:
        document_type: 문서 유형 ID (예: "resident_card")
        name_ko: 문서 유형 한글명 (예: "주민등록증")
        risk_level: 해당 문서의 기본 위험도
        confidence: 매칭 신뢰도 (high/medium/low/none)
        matched_keywords: 매칭된 키워드 수
    """
    return detect_document_type(ocr_text)


@mcp.tool()
def evaluate_risk(detected_items: List[Dict]) -> Dict[str, Any]:
    """
    Evaluate final risk level based on detected items.
    감지된 항목들의 최종 위험도를 평가합니다.

    조합 규칙(combination_rules)과 자동 상향 규칙(auto_escalation)을 적용하여
    개별 항목보다 높은 위험도가 적용될 수 있습니다.

    Args:
        detected_items: scan_pii()에서 반환된 found_pii 목록

    Returns:
        final_risk: 최종 위험도 (조합 규칙 적용 후)
        base_risk: 기본 위험도 (가장 높은 개별 항목)
        escalation_reason: 위험도 상향 이유 (해당 시)
        is_secret_recommended: 시크릿 전송 권장 여부
        matched_rules: 매칭된 조합 규칙 ID 목록
        detected_count: 감지된 항목 수
    """
    return calculate_risk(detected_items)


@mcp.tool()
def get_action_for_risk(risk_level: str) -> str:
    """
    Get recommended action for a given risk level.
    위험도에 따른 권장 조치를 반환합니다.

    Args:
        risk_level: 위험도 (LOW, MEDIUM, HIGH, CRITICAL)

    Returns:
        권장 조치 문자열 (예: "시크릿 전송 필수")
    """
    return get_risk_action(risk_level)


@mcp.tool()
def analyze_full(text: str) -> Dict[str, Any]:
    """
    Full analysis pipeline: scan PII + evaluate risk + get action.
    전체 분석 파이프라인: PII 스캔 → 위험도 평가 → 권장 조치.

    단일 호출로 전체 분석을 수행합니다.

    Args:
        text: 분석할 텍스트

    Returns:
        pii_scan: PII 스캔 결과
        risk_evaluation: 위험도 평가 결과
        recommended_action: 권장 조치
        summary: 분석 요약 (한글)
    """
    # 1. PII 스캔
    pii_result = detect_pii(text)

    # 2. 위험도 평가
    risk_result = calculate_risk(pii_result["found_pii"])

    # 3. 권장 조치
    action = get_risk_action(risk_result["final_risk"])

    # 4. 요약 생성
    if pii_result["count"] == 0:
        summary = "민감정보가 감지되지 않았습니다."
    else:
        detected_names = [item["name_ko"] for item in pii_result["found_pii"]]
        unique_names = list(set(detected_names))
        summary = f"{len(unique_names)}종의 민감정보 감지: {', '.join(unique_names)}. {action}"

    return {
        "pii_scan": pii_result,
        "risk_evaluation": risk_result,
        "recommended_action": action,
        "summary": summary
    }


# ============================================================
# Threat Matcher MCP Tools - Agent B (수신 보호) 분석 도구
# 피싱/스미싱/보이스피싱 위협 감지
# ============================================================

@mcp.tool()
def list_threat_categories() -> Dict[str, Any]:
    """
    List all threat categories and patterns.
    감지 가능한 모든 위협 카테고리와 패턴 목록을 반환합니다.

    AI가 어떤 종류의 피싱/사기 위협을 감지할 수 있는지 파악하는 데 사용합니다.

    Returns:
        카테고리별 위협 패턴 정보
        - financial_scam: 금융사기 (긴급송금, 대출유도, 투자사기)
        - impersonation: 사칭 (가족, 기관, 배송, 회사)
        - link_phishing: 링크 피싱 (단축URL, 의심도메인, APK유도)
        - info_extraction: 정보탈취 (인증정보, 신분증, 계좌정보 요청)
        - pressure_tactics: 심리적 압박 (시간압박, 공포유발, 혜택과장)
    """
    return get_threat_categories()


@mcp.tool()
def list_scam_scenarios() -> List[Dict]:
    """
    List known scam scenarios.
    알려진 사기 시나리오 목록을 반환합니다.

    전형적인 보이스피싱/스미싱 패턴을 파악하는 데 사용합니다.
    (예: 검찰 사칭 수사, 가족 긴급상황, 환불 함정)

    Returns:
        시나리오 목록 (id, name_ko, pattern_sequence, typical_phrases)
    """
    return get_known_scam_scenarios()


@mcp.tool()
def scan_threats(text: str) -> Dict[str, Any]:
    """
    Scan incoming message for threat patterns.
    수신 메시지에서 위협 패턴을 스캔합니다.

    키워드 + 정규식 기반으로 피싱/사기 패턴을 감지합니다.

    Args:
        text: 분석할 수신 메시지

    Returns:
        found_threats: 감지된 위협 목록 [{id, category, name_ko, risk_level, matched_keywords}]
        categories_found: 감지된 카테고리 목록
        highest_risk: 가장 높은 위험도 (LOW/MEDIUM/HIGH/CRITICAL)
        matched_keywords: 매칭된 키워드 목록
        count: 감지된 위협 개수
    """
    return detect_threats(text)


@mcp.tool()
def scan_urls(text: str) -> Dict[str, Any]:
    """
    Scan message for URLs and analyze safety.
    메시지에서 URL을 감지하고 안전성을 분석합니다.

    단축 URL, 의심 도메인, IP 주소 URL 등을 탐지합니다.

    Args:
        text: 분석할 텍스트

    Returns:
        urls_found: 발견된 모든 URL
        suspicious_urls: 의심스러운 URL (화이트리스트 제외)
        safe_urls: 안전한 URL (화이트리스트 도메인)
        risk_level: URL 관련 위험도
        has_shortened_url: 단축 URL 포함 여부
    """
    return detect_urls(text)


@mcp.tool()
def check_scam_scenario(found_threats: List[Dict]) -> Dict[str, Any]:
    """
    Check if detected threats match known scam scenarios.
    감지된 위협이 알려진 사기 시나리오와 매칭되는지 확인합니다.

    Args:
        found_threats: scan_threats()에서 반환된 found_threats 목록

    Returns:
        matched_scenario: 매칭된 시나리오 정보 (있는 경우)
        confidence: 매칭 신뢰도 (high/medium/low/none)
        pattern_coverage: 패턴 커버리지 (0.0~1.0)
    """
    return match_scam_scenario(found_threats)


@mcp.tool()
def evaluate_threat(
    found_threats: List[Dict],
    url_analysis: Dict = None,
    scenario_match: Dict = None
) -> Dict[str, Any]:
    """
    Evaluate final threat score based on all detections.
    모든 감지 결과를 종합하여 최종 위협 점수를 계산합니다.

    Args:
        found_threats: scan_threats()에서 반환된 found_threats
        url_analysis: scan_urls()에서 반환된 결과 (옵션)
        scenario_match: check_scam_scenario()에서 반환된 결과 (옵션)

    Returns:
        threat_score: 최종 위협 점수 (0~200+)
        threat_level: 위협 레벨 (SAFE/SUSPICIOUS/DANGEROUS/CRITICAL)
        is_likely_scam: 사기 메시지 가능성 여부
        warning_message: 사용자에게 보여줄 경고 메시지
        recommended_action: 권장 조치 (none/warn/block_recommended/block_and_report)
    """
    return calculate_threat_score(found_threats, url_analysis, scenario_match)


@mcp.tool()
def analyze_threat_full(text: str) -> Dict[str, Any]:
    """
    Full threat analysis pipeline for incoming messages.
    수신 메시지 전체 위협 분석 파이프라인.

    단일 호출로 전체 분석을 수행합니다:
    1. 위협 패턴 감지
    2. URL 분석
    3. 시나리오 매칭
    4. 최종 점수 계산

    Args:
        text: 분석할 수신 메시지

    Returns:
        threat_detection: 위협 감지 결과
        url_analysis: URL 분석 결과
        scenario_match: 시나리오 매칭 결과
        final_assessment: 최종 평가 (점수, 레벨, 경고, 권장조치)
        summary: 분석 요약
    """
    result = analyze_incoming_message(text)

    # 요약 추가 (새 MECE 카테고리 기반)
    risk_level = result["final_assessment"]["risk_level"]
    scam_probability = result["final_assessment"]["scam_probability"]
    category = result["summary"]["category"]  # A-1, B-2 등
    pattern_name = result["summary"]["pattern"]

    if risk_level == "safe":
        summary = "안전한 메시지입니다. 위협 요소가 감지되지 않았습니다."
    elif risk_level == "low":
        summary = f"낮은 위험. 사기확률 {scam_probability}%. 발신자를 확인하세요."
    elif risk_level == "medium":
        summary = f"주의! [{category}] {pattern_name} 패턴 감지. 사기확률 {scam_probability}%."
    elif risk_level == "high":
        summary = f"위험! [{category}] {pattern_name}. 사기확률 {scam_probability}%. 링크 클릭/정보 제공 금지."
    else:  # critical
        summary = f"피싱/사기 의심! [{category}] {pattern_name}. 사기확률 {scam_probability}%. 절대 응답하지 마세요."

    result["mcp_summary"] = summary
    return result


@mcp.tool()
def get_threat_action(threat_level: str) -> Dict[str, str]:
    """
    Get response template for a given threat level.
    위협 레벨에 따른 응답 템플릿을 반환합니다.

    Args:
        threat_level: 위협 레벨 (SAFE/SUSPICIOUS/DANGEROUS/CRITICAL)

    Returns:
        message: 사용자에게 보여줄 메시지
        action: 권장 조치
    """
    return get_threat_response(threat_level)


# ============================================================
# Hybrid Analysis Tools - Rule + LLM 통합 분석
# ============================================================

@mcp.tool()
def hybrid_analyze_outgoing(text: str, use_llm: bool = True) -> Dict[str, Any]:
    """
    Hybrid analysis for outgoing messages (Rule + LLM).
    발신 메시지 하이브리드 분석 (Rule-based + LLM).

    Args:
        text: 분석할 발신 메시지
        use_llm: LLM 분석 사용 여부 (기본: True)

    Returns:
        method: 분석 방법 (rule_based/hybrid)
        found_pii: 감지된 PII 목록
        risk_level: 최종 위험도
        is_secret_recommended: 시크릿 전송 권장 여부
        llm_reasoning: LLM 분석 근거 (use_llm=True인 경우)
    """
    from ..core.hybrid_analyzer import hybrid_analyze
    return hybrid_analyze(text, use_llm=use_llm)


@mcp.tool()
def hybrid_analyze_incoming(text: str, use_llm: bool = True) -> Dict[str, Any]:
    """
    Hybrid analysis for incoming messages (Rule + LLM).
    수신 메시지 하이브리드 분석 (Rule-based + LLM).

    Args:
        text: 분석할 수신 메시지
        use_llm: LLM 분석 사용 여부 (기본: True)

    Returns:
        method: 분석 방법 (rule_based/hybrid)
        threat_level: 위협 레벨
        threat_score: 위협 점수
        is_likely_scam: 사기 메시지 가능성
        detected_threats: 감지된 위협 목록
        warning_message: 경고 메시지
        llm_reasoning: LLM 분석 근거 (use_llm=True인 경우)
    """
    from ..core.hybrid_threat_analyzer import hybrid_threat_analyze
    return hybrid_threat_analyze(text, use_llm=use_llm)


# ============================================================
# Agent B 추가 MCP Tools - 4단계 분석용
# ============================================================

@mcp.tool()
def check_reported_scam(text: str) -> Dict[str, Any]:
    """
    Check if message contains reported scam accounts or phone numbers.
    메시지 내 계좌번호/전화번호의 사기 신고 이력을 조회합니다.

    경찰청/금감원 신고 DB에서 조회합니다 (현재는 Mock DB).

    Args:
        text: 분석할 메시지

    Returns:
        has_reported_identifier: 신고된 식별자 포함 여부
        reported_accounts: 신고된 계좌 정보 목록
        reported_phones: 신고된 전화번호 정보 목록
        max_risk_score: 최대 위험 점수 (0-100)
        recommended_action: 권장 조치 (none/warn/block_and_report)
    """
    from ..core.scam_checker import check_scam_in_message
    return check_scam_in_message(text)


@mcp.tool()
def get_sender_trust(user_id: int, sender_id: int, current_message: str = "") -> Dict[str, Any]:
    """
    Get sender trust level based on conversation history.
    대화 이력을 기반으로 발신자 신뢰도를 조회합니다.

    Args:
        user_id: 수신자 (현재 사용자) ID
        sender_id: 발신자 ID
        current_message: 현재 수신 메시지 (선택, 추가 분석용)

    Returns:
        sender_trust: 발신자 신뢰 정보
            - has_history: 이전 대화 이력 존재 여부
            - is_first_message: 첫 메시지 여부
            - trust_score: 신뢰도 점수 (0-100)
            - trust_level: 신뢰 레벨 (unknown/low/medium/high)
        risk_factors: 위험 요소 목록
        risk_adjustment: 위험도 조정값
        warning_message: 경고 메시지 (있는 경우)
    """
    from ..core.conversation_analyzer import analyze_sender_risk
    return analyze_sender_risk(user_id, sender_id, current_message)


@mcp.tool()
def get_action_policy_for_risk(
    risk_level: str,
    scenario: str = None,
    scam_check_result: Dict = None,
    sender_analysis: Dict = None
) -> Dict[str, Any]:
    """
    Get detailed action policy for given risk level.
    위험도에 따른 상세 액션 정책을 조회합니다.

    Args:
        risk_level: 위험 레벨 (LOW/MEDIUM/HIGH/CRITICAL)
        scenario: 매칭된 시나리오 ID (선택)
        scam_check_result: check_reported_scam() 결과 (선택)
        sender_analysis: get_sender_trust() 결과 (선택)

    Returns:
        final_risk_level: 최종 위험 레벨 (종합 분석 시)
        policy: 적용할 정책
            - action_type: 액션 타입
            - ui_config: UI 설정 (경고 색상, 버튼 표시 등)
            - user_message: 사용자에게 보여줄 메시지
            - recommended_steps: 권장 조치 목록
        risk_factors: 위험 요소 목록
        total_risk_score: 종합 위험 점수
    """
    from ..core.action_policy import get_combined_policy, get_action_policy

    if scam_check_result or sender_analysis:
        # 종합 분석
        return get_combined_policy(
            text_risk=risk_level,
            scam_check_result=scam_check_result,
            sender_analysis=sender_analysis,
            scenario_match=scenario
        )
    else:
        # 단순 정책 조회
        policy = get_action_policy(risk_level, scenario)
        return {
            "final_risk_level": risk_level,
            "policy": policy,
            "risk_factors": [],
            "total_risk_score": {"LOW": 10, "MEDIUM": 40, "HIGH": 70, "CRITICAL": 100}.get(risk_level, 10)
        }


@mcp.tool()
def analyze_incoming_full(
    text: str,
    user_id: int = None,
    sender_id: int = None,
    use_ai: bool = True
) -> Dict[str, Any]:
    """
    Full 4-stage analysis for incoming messages.
    수신 메시지 완전한 4단계 분석 파이프라인.

    Stage 1: 텍스트 패턴 분석 (위협 감지)
    Stage 2: URL + 신고 DB 조회
    Stage 3: 발신자 신뢰도 분석
    Stage 4: 정책 기반 최종 판정

    Args:
        text: 분석할 수신 메시지
        user_id: 수신자 ID (선택)
        sender_id: 발신자 ID (선택)
        use_ai: LLM 분석 사용 여부

    Returns:
        stage1_threat_detection: 1단계 위협 감지 결과
        stage2_scam_check: 2단계 신고 DB 조회 결과
        stage3_sender_trust: 3단계 발신자 분석 결과
        stage4_final_policy: 4단계 최종 정책
        summary: 분석 요약
        risk_level: 최종 위험 레벨
        recommended_action: 권장 조치
    """
    from ..core.threat_matcher import analyze_incoming_message
    from ..core.scam_checker import check_scam_in_message
    from ..core.conversation_analyzer import analyze_sender_risk
    from ..core.action_policy import get_combined_policy, format_warning_for_ui

    # Stage 1: 텍스트 패턴 분석
    stage1 = analyze_incoming_message(text)
    # threat_matcher는 소문자(safe/low/medium/high/critical) 반환
    # action_policy는 대문자(LOW/MEDIUM/HIGH/CRITICAL) 사용
    level_map = {"safe": "LOW", "low": "LOW", "medium": "MEDIUM", "high": "HIGH", "critical": "CRITICAL"}
    raw_level = stage1.get("final_assessment", {}).get("risk_level", "safe")
    threat_level = level_map.get(raw_level, "LOW")

    # Stage 2: 신고 DB 조회
    stage2 = check_scam_in_message(text)

    # Stage 3: 발신자 신뢰도 (user_id, sender_id 있는 경우)
    stage3 = None
    if user_id and sender_id:
        stage3 = analyze_sender_risk(user_id, sender_id, text)

    # Stage 4: 종합 정책 결정
    scenario_match = None
    if stage1.get("scenario_match", {}).get("matched_scenario"):
        scenario_match = stage1["scenario_match"]["matched_scenario"].get("id")

    stage4 = get_combined_policy(
        text_risk=threat_level,
        scam_check_result=stage2,
        sender_analysis=stage3,
        scenario_match=scenario_match
    )

    # 요약 생성 (새 MECE 카테고리 기반)
    final_level = stage4["final_risk_level"]  # 대문자 (LOW/MEDIUM/HIGH/CRITICAL)
    category = stage1.get("summary", {}).get("category")  # A-1, B-2 등
    pattern_name = stage1.get("summary", {}).get("pattern", "")
    scam_prob = stage1.get("final_assessment", {}).get("scam_probability", 0)

    summary_messages = {
        "LOW": "안전한 메시지입니다.",
        "MEDIUM": f"주의! [{category}] {pattern_name}. 사기확률 {scam_prob}%.",
        "HIGH": f"위험! [{category}] {pattern_name}. 사기확률 {scam_prob}%. 링크/정보 제공 금지.",
        "CRITICAL": f"피싱/사기 의심! [{category}] {pattern_name}. 사기확률 {scam_prob}%. 절대 응답 금지."
    }

    return {
        "stage1_threat_detection": stage1,
        "stage2_scam_check": stage2,
        "stage3_sender_trust": stage3,
        "stage4_final_policy": stage4,
        "summary": summary_messages.get(final_level, "분석 완료"),
        "risk_level": final_level,
        "recommended_action": stage4["policy"].get("action_type", "none"),
        "ui_warning": format_warning_for_ui(stage4["policy"])
    }


# ============================================================
# Threat Intelligence MCP Tool - 통합 위협 정보 조회
# ============================================================

@mcp.tool()
def threat_intelligence_mcp(identifier: str, type: str) -> Dict[str, Any]:
    """
    Threat intelligence lookup for phone, URL, or account.
    전화번호, URL, 계좌번호의 위협 정보를 통합 조회합니다.

    통합 소스:
    - TheCheat API: 전화번호/계좌번호 사기 신고 조회
    - KISA Phishing API: 피싱 사이트 URL 조회
    - lrl.kr API: 안전한링크 URL 검증
    - VirusTotal API: URL 악성코드 검사

    Args:
        identifier: 조회할 식별자 (전화번호, URL, 계좌번호)
        type: 식별자 타입 ("phone" | "url" | "account")

    Returns:
        has_reported: 신고/위협 여부 (bool)
        source: 조회된 소스 (예: "TheCheat", "KISA", "lrl.kr", "VirusTotal")
        report_count: 신고 건수 (int)
        prior_probability: 사전 확률 (float, 0.0~1.0)
                          계산식: report_count / (report_count + 100)
        threat_type: 위협 유형 (URL인 경우: "phishing" | "malware" | "safe" | "suspicious")
        details: 상세 정보 (Dict)

    Examples:
        전화번호 조회:
        threat_intelligence_mcp("010-1234-5678", "phone")
        → {has_reported: true, source: "TheCheat", report_count: 1, prior_probability: 0.0099}

        URL 조회:
        threat_intelligence_mcp("http://phishing-site.com", "url")
        → {has_reported: true, source: "KISA", threat_type: "phishing", prior_probability: 0.0099}

        계좌번호 조회:
        threat_intelligence_mcp("123-456-789012", "account")
        → {has_reported: false, source: null, report_count: 0, prior_probability: 0.0}
    """
    from ..core.threat_intelligence import check_identifier

    try:
        result = check_identifier(identifier, type)
        return result
    except ValueError as e:
        return {
            "has_reported": False,
            "source": None,
            "report_count": 0,
            "prior_probability": 0.0,
            "error": str(e),
            "details": {}
        }


# ============================================================
# Bayesian Calculator MCP Tool - 베이지안 사후 확률 계산
# ============================================================

@mcp.tool()
def bayesian_calculator_mcp(
    pattern_conf: float,
    db_prior: float,
    trust_score: float,
    weights: List[float] = None
) -> Dict[str, Any]:
    """
    Calculate Bayesian posterior probability for fraud detection.
    베이지안 사후 확률을 계산하여 최종 사기 위험도를 판정합니다.

    이론적 근거:
    - Bayesian Inference (Nature 2025)
    - SHAP Weight (NeurIPS 2017): Pattern 40%, DB 30%, Trust 30%

    Args:
        pattern_conf: 패턴 매칭 신뢰도 (0.0 ~ 1.0)
                     context_analyzer_mcp 결과의 confidence
        db_prior: DB 사전 확률 (0.0 ~ 1.0)
                 threat_intelligence_mcp 결과의 prior_probability
        trust_score: 발신자 신뢰도 (0.0 ~ 1.0)
                    social_graph_mcp 결과의 trust_score
        weights: 가중치 [pattern, db, trust] (기본: [0.4, 0.3, 0.3])

    Returns:
        posterior_probability: 최종 사후 확률 (0.0 ~ 1.0)
        confidence_interval: 신뢰 구간 (lower, upper)
        uncertainty: 불확실성 (0.08)
        final_risk: 위험도 레벨 ("CRITICAL" | "HIGH" | "MEDIUM" | "LOW" | "SAFE")
        weighted_probability: 조정 전 가중 평균
        context_adjusted: 맥락 조정 적용 여부

    Examples:
        # 가족 사칭 + DB 신고 + 5년 이력
        bayesian_calculator_mcp(0.92, 0.77, 0.85)
        → {"posterior_probability": 0.29, "final_risk": "LOW"}

        # 기관 사칭 + DB 신고 + 첫 메시지
        bayesian_calculator_mcp(0.95, 0.90, 0.0)
        → {"posterior_probability": 0.68, "final_risk": "HIGH"}
    """
    from ..core.bayesian_calculator import bayesian_calculate
    return bayesian_calculate(pattern_conf, db_prior, trust_score, weights)


# ============================================================
# Entity Extractor MCP Tool - 식별자 추출
# ============================================================

@mcp.tool()
def entity_extractor_mcp(message: str) -> Dict[str, Any]:
    """
    Extract identifiers (phone, URL, account, email) from message.
    메시지에서 전화번호, URL, 계좌번호, 이메일을 추출합니다.

    threat_intelligence_mcp 호출 전에 사용하여 조회할 식별자를 추출.

    Args:
        message: 분석할 메시지

    Returns:
        phone_numbers: 추출된 전화번호 리스트
        urls: 추출된 URL 리스트
        accounts: 추출된 계좌번호 리스트
        emails: 추출된 이메일 리스트
        total_count: 총 추출 수
        has_suspicious: 의심 요소 포함 여부 (단축 URL 등)

    Examples:
        entity_extractor_mcp("전화 010-1234-5678, 입금 110-123-456789")
        → {"phone_numbers": ["010-1234-5678"], "accounts": ["110-123-456789"], ...}

        entity_extractor_mcp("자세한 내용: bit.ly/scam123")
        → {"urls": ["bit.ly/scam123"], "has_suspicious": true, ...}
    """
    from ..core.entity_extractor import extract_entities
    return extract_entities(message)


# ============================================================
# Context Analyzer MCP Tool - MECE 카테고리 + Cialdini 분류
# ============================================================

# Cialdini 6원리 매핑
CIALDINI_MAPPING = {
    "A-1": ["Urgency", "Liking"],           # 가족 사칭
    "A-2": ["Authority", "Urgency"],        # 지인/상사 사칭
    "A-3": ["Liking", "Reciprocity"],       # 상품권 대리구매
    "B-1": ["Urgency", "Fear"],             # 택배/경조사
    "B-2": ["Authority", "Fear"],           # 기관 사칭
    "B-3": ["Urgency", "Fear"],             # 결제 승인
    "C-1": ["Scarcity", "Social Proof"],    # 투자 권유
    "C-2": ["Liking", "Reciprocity"],       # 로맨스 스캠
    "C-3": ["Fear", "Urgency"],             # 몸캠 피싱
    "NORMAL": []
}

@mcp.tool()
def context_analyzer_mcp(message: str, context: List[str] = None) -> Dict[str, Any]:
    """
    Analyze message context and classify into MECE categories with Cialdini mapping.
    메시지를 MECE 9-카테고리로 분류하고 Cialdini 심리 원리를 매핑합니다.

    MECE 카테고리:
    - A-1: 가족 사칭 (액정 파손)
    - A-2: 지인/상사 사칭 (급전)
    - A-3: 상품권 대리 구매
    - B-1: 생활 밀착형 (택배/경조사)
    - B-2: 기관 사칭 (검찰/경찰)
    - B-3: 결제 승인 (낚시성)
    - C-1: 투자 권유 (리딩방)
    - C-2: 로맨스 스캠
    - C-3: 몸캠 피싱
    - NORMAL: 정상 메시지

    Cialdini 6원리:
    - Authority (권위)
    - Urgency (긴급성)
    - Liking (호감)
    - Scarcity (희소성)
    - Reciprocity (상호성)
    - Social Proof (사회적 증거)
    - Fear (공포)

    Args:
        message: 분석할 메시지
        context: 최근 대화 히스토리 (선택)

    Returns:
        category: MECE 카테고리 코드 ("A-1" ~ "C-3" | "NORMAL")
        category_name: 카테고리 한글명
        confidence: 분류 신뢰도 (0.0 ~ 1.0)
        cialdini_principles: Cialdini 원리 리스트
        reasoning: 분류 근거 설명
        scam_probability: 사기 확률 (%)

    Examples:
        context_analyzer_mcp("엄마, 나 폰 고장나서 번호 바뀌었어")
        → {"category": "A-1", "cialdini_principles": ["Urgency", "Liking"], ...}
    """
    from ..core.threat_matcher import analyze_incoming_message

    # 기존 분석기 호출
    result = analyze_incoming_message(message)

    # 카테고리 및 기본 정보 추출
    summary = result.get("summary", {})
    category = summary.get("category", "NORMAL")
    pattern_name = summary.get("pattern", "정상 메시지")

    final_assessment = result.get("final_assessment", {})
    scam_probability = final_assessment.get("scam_probability", 0)

    # confidence 계산 (scam_probability 기반)
    confidence = scam_probability / 100.0 if scam_probability else 0.0

    # Cialdini 매핑
    cialdini_principles = CIALDINI_MAPPING.get(category, [])

    # 위험도 → confidence 조정
    risk_level = final_assessment.get("risk_level", "safe")
    if risk_level == "critical":
        confidence = max(confidence, 0.9)
    elif risk_level == "high":
        confidence = max(confidence, 0.7)
    elif risk_level == "medium":
        confidence = max(confidence, 0.5)

    # reasoning 생성
    detected_threats = result.get("threat_detection", {}).get("found_threats", [])
    threat_names = [t.get("name_ko", "") for t in detected_threats[:3]]
    reasoning = f"{pattern_name} 패턴. 감지: {', '.join(threat_names) if threat_names else '없음'}"

    return {
        "category": category,
        "category_name": pattern_name,
        "confidence": round(confidence, 2),
        "cialdini_principles": cialdini_principles,
        "reasoning": reasoning,
        "scam_probability": scam_probability,
        "raw_result": result  # 원본 결과 포함 (디버깅용)
    }
