"""
predict.py
----------
Prediction module for Job Guard NLP classifier.

Loads the trained TF-IDF vectorizer + Logistic Regression model and
returns a structured prediction for any job description text.

Output schema:
  {
    "prediction": "Fake" | "Suspicious" | "Genuine",
    "confidence": 91.5,          # percentage, 0–100
    "reason": "..."              # human-readable explanation
  }
"""

import os
import pickle
import re
import sys
from dataclasses import dataclass

# Allow imports from backend root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from preprocessing.preprocessing import preprocess

# ── Model artifact paths ─────────────────────────────────────
_BASE          = os.path.join(os.path.dirname(__file__), "..", "models")
VECTORIZER_PATH = os.path.join(_BASE, "tfidf_vectorizer.pkl")
CLASSIFIER_PATH = os.path.join(_BASE, "job_classifier.pkl")
ENCODER_PATH    = os.path.join(_BASE, "label_encoder.pkl")

# ── Reason templates keyed by predicted label ────────────────
_REASON_TEMPLATES: dict[str, str] = {
    "Fake": (
        "Contains strong indicators of a fraudulent job offer such as "
        "upfront payment requests, unrealistic salary promises, or "
        "requests for personal documents via unofficial channels."
    ),
    "Suspicious": (
        "Contains several warning signs including vague company details, "
        "unusually high salary for freshers, or contact through personal "
        "email/WhatsApp instead of official channels."
    ),
    "Genuine": (
        "Appears to be a legitimate job posting with verifiable company "
        "information, realistic salary expectations, and official "
        "application channels."
    ),
}

# ── Keyword-based reason enrichment ─────────────────────────
_SIGNAL_PHRASES: list[tuple[str, str]] = [
    (r"registr\w*\s+fee|joining\s+fee|training\s+fee",
     "Asks for registration or joining fee — a hallmark of job scams."),
    (r"\bupi\b|pay\s+now|advance\s+payment|security\s+amount|deposit",
     "Requests upfront payment via UPI or cash deposit."),
    (r"send\s+(passport|aadhaar|pan|bank\s+details)",
     "Asks for sensitive personal documents — high identity theft risk."),
    (r"salary.{0,20}(lakh|lac|1\s*lakh|2\s*lakh)",
     "Promises unrealistically high salary (lakh/month) for a fresher role."),
    (r"no\s+interview|direct\s+joining|without\s+interview",
     "Claims direct joining without any interview process."),
    (r"@(gmail|yahoo|hotmail|outlook)\.com",
     "Recruiter contact is a personal email, not a corporate domain."),
    (r"whatsapp\s+only|telegram\s+only|contact\s+on\s+whatsapp",
     "Communication restricted to WhatsApp/Telegram — avoids official records."),
    (r"limited\s+seats?|only\s+\d+\s+seats?|last\s+date\s+today|today\s+only|hurry",
     "Uses artificial urgency to pressure immediate action."),
    (r"work\s+from\s+home.{0,30}(earn|salary).{0,20}(50000|60000|80000|1\s*lakh)",
     "Promises extremely high work-from-home earnings with no experience required."),
    (r"refundable|refund\s+after",
     "Claims fees are refundable — a common false reassurance in scams."),
]


@dataclass
class PredictionResult:
    prediction: str
    confidence: float
    reason: str


class JobGuardPredictor:
    """
    Loads trained model artifacts once and exposes a predict() method.
    Designed to be instantiated once at app startup (singleton pattern).
    """

    def __init__(self) -> None:
        self._vectorizer = None
        self._model      = None
        self._encoder    = None
        self._loaded     = False

    def _load(self) -> None:
        """Lazy-load model artifacts from disk."""
        if self._loaded:
            return

        missing = [
            p for p in (VECTORIZER_PATH, CLASSIFIER_PATH, ENCODER_PATH)
            if not os.path.exists(p)
        ]
        if missing:
            raise FileNotFoundError(
                "Trained model files not found. "
                "Run: python -m training.train_model\n"
                f"Missing: {missing}"
            )

        with open(VECTORIZER_PATH, "rb") as f:
            self._vectorizer = pickle.load(f)
        with open(CLASSIFIER_PATH, "rb") as f:
            self._model = pickle.load(f)
        with open(ENCODER_PATH, "rb") as f:
            self._encoder = pickle.load(f)

        self._loaded = True

    def _build_reason(self, label: str, text: str) -> str:
        """
        Build a specific reason string by checking which signal phrases
        are present in the raw text, then falling back to the template.
        """
        text_lower = text.lower()
        for pattern, explanation in _SIGNAL_PHRASES:
            if re.search(pattern, text_lower):
                return explanation
        return _REASON_TEMPLATES.get(label, "No specific reason identified.")

    def predict(self, job_description: str) -> PredictionResult:
        """
        Run the full prediction pipeline on a raw job description.

        Parameters
        ----------
        job_description : str
            Raw text of the job offer / message.

        Returns
        -------
        PredictionResult
            Dataclass with prediction, confidence (%), and reason.
        """
        self._load()

        # Preprocess
        cleaned = preprocess(job_description)
        if not cleaned:
            return PredictionResult(
                prediction="Genuine",
                confidence=50.0,
                reason="Input text was empty or could not be processed.",
            )

        # Vectorize
        X = self._vectorizer.transform([cleaned])

        # Predict class + probability
        class_idx   = self._model.predict(X)[0]
        proba       = self._model.predict_proba(X)[0]
        confidence  = round(float(proba[class_idx]) * 100, 2)
        label       = self._encoder.inverse_transform([class_idx])[0]

        # Build reason
        reason = self._build_reason(label, job_description)

        return PredictionResult(
            prediction=label,
            confidence=confidence,
            reason=reason,
        )


# ── Module-level singleton — imported by FastAPI routes ──────
predictor = JobGuardPredictor()
