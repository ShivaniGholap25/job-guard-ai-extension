"""routers/risk_analysis.py — POST /risk-analysis (scam scoring engine)."""

import logging

from fastapi import APIRouter, HTTPException

from schemas.risk_score import RiskAnalysisRequest, RiskAnalysisResponse
from services.risk_service import run_risk_analysis

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Risk Analysis"])


@router.post(
    "/risk-analysis",
    response_model=RiskAnalysisResponse,
    summary="Dynamic scam risk scoring engine",
    response_description="Composite risk score with per-dimension breakdown",
)
def risk_analysis(payload: RiskAnalysisRequest) -> RiskAnalysisResponse:
    """
    Evaluate a job description across **5 independent risk dimensions**
    and return a composite risk score (0–100).

    | Dimension | Max Points |
    |---|---|
    | `suspicious_keywords` | +20 |
    | `fake_email_domain` | +25 |
    | `unrealistic_salary` | +15 |
    | `phishing_url` | +30 |
    | `missing_company_info` | +20 |

    **Risk Levels:**
    - 0–30 → LOW
    - 31–60 → MEDIUM
    - 61–100 → HIGH

    The `breakdown` field shows exactly how many points each dimension
    contributed, making the score fully transparent and auditable.
    """
    try:
        result = run_risk_analysis(payload.text)
        return RiskAnalysisResponse(**result)
    except Exception as exc:
        logger.exception("Error in /risk-analysis")
        raise HTTPException(status_code=500, detail=f"Risk analysis failed: {exc}")
