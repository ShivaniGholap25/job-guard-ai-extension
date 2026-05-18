"""routers/analyze.py — POST /analyze (rule-based + Groq AI explanation)."""

import logging

from fastapi import APIRouter, HTTPException

from schemas.analyze import AnalyzeRequest, AnalyzeResponse
from services.analyze_service import run_analysis

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Analyze"])


@router.post(
    "/analyze",
    response_model=AnalyzeResponse,
    summary="Rule-based analysis with AI explanation",
    response_description="Risk score, label, signals, and Groq AI explanation",
)
def analyze_job_offer(payload: AnalyzeRequest) -> AnalyzeResponse:
    """
    Run 5 rule-based signal detectors on the job text and generate
    a plain-English explanation using **Groq Llama 3.3-70b**.

    **Detectors:**
    - Unrealistically high salary
    - Free/personal email domain
    - Payment or fee request
    - Urgency / pressure tactics
    - Missing company information

    **Returns:**
    - `score` — 0–100 risk score
    - `label` — Low Risk / Medium Risk / High Risk
    - `reasons` — list of triggered signals
    - `explanation` — AI-generated explanation with a verification tip
    """
    try:
        result = run_analysis(payload.text)
        return AnalyzeResponse(**result)
    except Exception as exc:
        logger.exception("Error in /analyze")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {exc}")
