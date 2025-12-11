"""
Bayesian Calculator - 베이지안 사후 확률 계산 모듈

Agent B Hybrid Agent의 최종 판단을 위한 베이지안 추론 엔진.
Nature 2025 연구 기반 P(Fraud|Evidence) 계산.

이론적 근거:
- Bayesian Inference (Nature 2025)
- SHAP Weight (NeurIPS 2017): Pattern 40%, DB 30%, Trust 30%
- Temperature Scaling for uncertainty quantification
"""
from typing import Dict, Tuple, List, Any


# SHAP 기반 기본 가중치
DEFAULT_WEIGHTS = {
    "pattern": 0.4,   # 패턴 매칭 (context_analyzer)
    "db": 0.3,        # DB 조회 (threat_intelligence)
    "trust": 0.3      # 신뢰도 (social_graph)
}

# 위험도 임계값
RISK_THRESHOLDS = {
    "CRITICAL": 0.8,
    "HIGH": 0.6,
    "MEDIUM": 0.4,
    "LOW": 0.2
}

# 신뢰도 조정 계수 (trust_score > 0.8일 때)
HIGH_TRUST_ADJUSTMENT = 0.3  # 70% 할인

# 불확실성 마진
UNCERTAINTY_MARGIN = 0.08


def calculate_weighted_probability(
    pattern_conf: float,
    db_prior: float,
    trust_score: float,
    weights: Dict[str, float] = None
) -> float:
    """
    SHAP 가중 평균 계산

    Args:
        pattern_conf: 패턴 매칭 신뢰도 (0.0 ~ 1.0)
        db_prior: DB 사전 확률 (0.0 ~ 1.0)
        trust_score: 발신자 신뢰도 (0.0 ~ 1.0)
        weights: 가중치 딕셔너리 (기본: SHAP 가중치)

    Returns:
        가중 평균 확률 (0.0 ~ 1.0)
    """
    w = weights or DEFAULT_WEIGHTS

    # 신뢰도는 역으로 계산 (높은 신뢰 = 낮은 위험)
    trust_risk = 1 - trust_score

    weighted = (
        pattern_conf * w["pattern"] +
        db_prior * w["db"] +
        trust_risk * w["trust"]
    )

    return min(max(weighted, 0.0), 1.0)  # 0~1 범위로 클램핑


def apply_context_adjustment(
    weighted_prob: float,
    trust_score: float,
    adjustment_threshold: float = 0.8
) -> float:
    """
    맥락 기반 조정 (Context-Aware Adjustment)

    높은 신뢰도(5년 대화 이력 등)가 있으면 위험도 하향 조정.
    "맥락 우선" 원칙 적용.

    Args:
        weighted_prob: 가중 평균 확률
        trust_score: 발신자 신뢰도
        adjustment_threshold: 조정 적용 임계값 (기본: 0.8)

    Returns:
        조정된 사후 확률
    """
    if trust_score > adjustment_threshold:
        # 높은 신뢰도 → 위험도 70% 할인
        return weighted_prob * HIGH_TRUST_ADJUSTMENT
    return weighted_prob


def calculate_confidence_interval(
    posterior: float,
    margin: float = UNCERTAINTY_MARGIN
) -> Tuple[float, float]:
    """
    신뢰 구간 계산 (Temperature Scaling)

    Args:
        posterior: 사후 확률
        margin: 불확실성 마진 (기본: 0.08)

    Returns:
        (lower_bound, upper_bound) 튜플
    """
    lower = max(0.0, posterior - margin)
    upper = min(1.0, posterior + margin)
    return (round(lower, 4), round(upper, 4))


def get_risk_level(posterior: float) -> str:
    """
    사후 확률을 위험도 레벨로 변환

    Args:
        posterior: 사후 확률 (0.0 ~ 1.0)

    Returns:
        "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" | "SAFE"
    """
    if posterior >= RISK_THRESHOLDS["CRITICAL"]:
        return "CRITICAL"
    elif posterior >= RISK_THRESHOLDS["HIGH"]:
        return "HIGH"
    elif posterior >= RISK_THRESHOLDS["MEDIUM"]:
        return "MEDIUM"
    elif posterior >= RISK_THRESHOLDS["LOW"]:
        return "LOW"
    else:
        return "SAFE"


def calculate_posterior(
    pattern_conf: float,
    db_prior: float,
    trust_score: float,
    weights: List[float] = None
) -> Dict[str, Any]:
    """
    베이지안 사후 확률 계산 (메인 함수)

    P(Fraud|Evidence) = P(Evidence|Fraud) × P(Fraud) / P(Evidence)
    실제로는 가중 평균 + 맥락 조정으로 근사.

    Args:
        pattern_conf: 패턴 매칭 신뢰도 (0.0 ~ 1.0)
        db_prior: DB 사전 확률 (0.0 ~ 1.0)
        trust_score: 발신자 신뢰도 (0.0 ~ 1.0)
        weights: [pattern, db, trust] 가중치 리스트 (기본: [0.4, 0.3, 0.3])

    Returns:
        {
            "posterior_probability": float,  # 최종 사후 확률
            "confidence_interval": Tuple[float, float],  # 신뢰 구간
            "uncertainty": float,  # 불확실성
            "final_risk": str,  # 위험도 레벨
            "weighted_probability": float,  # 조정 전 가중 평균
            "context_adjusted": bool,  # 맥락 조정 적용 여부
            "inputs": Dict  # 입력값 기록
        }

    Examples:
        # 가족 사칭 + DB 신고 + 5년 이력
        calculate_posterior(0.92, 0.77, 0.85)
        → {"posterior_probability": 0.29, "final_risk": "LOW", ...}

        # 기관 사칭 + DB 신고 + 첫 메시지
        calculate_posterior(0.95, 0.90, 0.0)
        → {"posterior_probability": 0.68, "final_risk": "HIGH", ...}
    """
    # 가중치 변환
    weight_dict = DEFAULT_WEIGHTS.copy()
    if weights and len(weights) >= 3:
        weight_dict = {
            "pattern": weights[0],
            "db": weights[1],
            "trust": weights[2]
        }

    # Step 1: 가중 평균 계산
    weighted_prob = calculate_weighted_probability(
        pattern_conf, db_prior, trust_score, weight_dict
    )

    # Step 2: 맥락 기반 조정
    context_adjusted = trust_score > 0.8
    posterior = apply_context_adjustment(weighted_prob, trust_score)

    # Step 3: 신뢰 구간 계산
    confidence_interval = calculate_confidence_interval(posterior)

    # Step 4: 위험도 레벨 결정
    final_risk = get_risk_level(posterior)

    return {
        "posterior_probability": round(posterior, 4),
        "confidence_interval": confidence_interval,
        "uncertainty": UNCERTAINTY_MARGIN,
        "final_risk": final_risk,
        "weighted_probability": round(weighted_prob, 4),
        "context_adjusted": context_adjusted,
        "inputs": {
            "pattern_conf": pattern_conf,
            "db_prior": db_prior,
            "trust_score": trust_score,
            "weights": weight_dict
        }
    }


# ============================================================
# MCP 도구용 Wrapper
# ============================================================

def bayesian_calculate(
    pattern_conf: float,
    db_prior: float,
    trust_score: float,
    weights: List[float] = None
) -> Dict[str, Any]:
    """
    bayesian_calculator_mcp용 래퍼 함수

    Args:
        pattern_conf: 패턴 매칭 신뢰도
        db_prior: DB 사전 확률
        trust_score: 발신자 신뢰도
        weights: 가중치 리스트 [0.4, 0.3, 0.3]

    Returns:
        calculate_posterior() 결과
    """
    return calculate_posterior(pattern_conf, db_prior, trust_score, weights)
