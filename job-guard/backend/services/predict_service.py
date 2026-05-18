"""
services/predict_service.py
----------------------------
Thin service wrapper around the NLP predictor singleton.

Keeps the router free of ML concerns and makes the predictor
easy to swap or mock in tests.
"""

import logging

from api.predict import predictor

logger = logging.getLogger(__name__)


def run_prediction(job_description: str) -> dict:
    """
    Run the TF-IDF + Logistic Regression classifier.

    Parameters
    ----------
    job_description : str
        Raw job offer text.

    Returns
    -------
    dict
        Keys: prediction, confidence, reason

    Raises
    ------
    FileNotFoundError
        If trained model .pkl files are missing.
    RuntimeError
        On any unexpected prediction failure.
    """
    logger.info("Running NLP prediction (%d chars)", len(job_description))
    try:
        result = predictor.predict(job_description)
        logger.info(
            "Prediction complete — label=%s confidence=%.1f%%",
            result.prediction, result.confidence,
        )
        return {
            "prediction": result.prediction,
            "confidence": result.confidence,
            "reason":     result.reason,
        }
    except FileNotFoundError:
        raise
    except Exception as exc:
        logger.error("Prediction failed: %s", exc)
        raise RuntimeError(f"Prediction failed: {exc}") from exc
