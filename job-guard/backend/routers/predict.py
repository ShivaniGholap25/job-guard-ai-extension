"""routers/predict.py — POST /predict (NLP classifier)."""

import logging

from fastapi import APIRouter, HTTPException

from schemas.predict import PredictRequest, PredictResponse
from services.predict_service import run_prediction

logger = logging.getLogger(__name__)
router = APIRouter(tags=["NLP Classifier"])


@router.post(
    "/predict",
    response_model=PredictResponse,
    summary="NLP-based fake job classifier",
    response_description="Prediction label, confidence score, and reason",
)
def predict_job(payload: PredictRequest) -> PredictResponse:
    """
    Classify a job description as **Genuine**, **Suspicious**, or **Fake**
    using a trained TF-IDF + Logistic Regression model.

    **Pipeline:**
    1. Preprocess text (lowercase, stopword removal, lemmatization)
    2. Transform with TF-IDF vectorizer
    3. Predict class + probability with Logistic Regression
    4. Return label, confidence %, and a signal-based reason

    **Requires** trained model files in `backend/models/`.
    Run `python -m training.train_model` if models are missing.
    """
    try:
        result = run_prediction(payload.job_description)
        return PredictResponse(**result)

    except FileNotFoundError as exc:
        logger.error("Model files missing: %s", exc)
        raise HTTPException(
            status_code=503,
            detail=(
                "ML model files not found. "
                "Run: python -m training.train_model"
            ),
        )
    except RuntimeError as exc:
        logger.error("Prediction runtime error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))
    except Exception as exc:
        logger.exception("Unexpected error in /predict")
        raise HTTPException(status_code=500, detail="Internal server error")
