"""schemas/predict.py — NLP classifier request/response models."""

from pydantic import BaseModel, Field, field_validator


class PredictRequest(BaseModel):
    job_description: str = Field(
        ...,
        min_length=10,
        max_length=5000,
        description="Raw job offer text to classify (Genuine / Suspicious / Fake)",
        examples=["Urgent hiring! Pay registration fee via UPI. Contact jobs@gmail.com"],
    )

    @field_validator("job_description")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        return v.strip()


class PredictResponse(BaseModel):
    prediction: str = Field(..., description="Genuine | Suspicious | Fake")
    confidence: float = Field(..., ge=0.0, le=100.0, description="Model confidence 0–100%")
    reason:     str   = Field(..., description="Human-readable explanation of the prediction")
