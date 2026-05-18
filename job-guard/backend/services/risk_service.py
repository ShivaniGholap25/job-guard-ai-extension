"""
services/risk_service.py
-------------------------
Thin service wrapper around the Scam Risk Scoring Engine.
"""

import logging

from security.scam_score import score_text

logger = logging.getLogger(__name__)


def run_risk_analysis(text: str) -> dict:
    """
    Run the 5-dimension scam risk scoring engine.

    Parameters
    ----------
    text : str
        Raw job offer text.

    Returns
    -------
    dict
        Keys: risk_score, risk_level, reasons, breakdown
    """
    logger.info("Running risk analysis (%d chars)", len(text))
    result = score_text(text)
    logger.info(
        "Risk analysis complete — level=%s score=%d",
        result.risk_level, result.risk_score,
    )
    return {
        "risk_score": result.risk_score,
        "risk_level": result.risk_level,
        "reasons":    result.reasons,
        "breakdown":  result.breakdown,
    }
