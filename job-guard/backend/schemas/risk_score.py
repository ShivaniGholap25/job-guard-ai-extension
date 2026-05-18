"""schemas/risk_score.py — Scam risk scoring engine models."""

from pydantic import BaseModel, Field, field_validator


class RiskAnalysisRequest(BaseModel):
    text: str = Field(
        ...,
        min_length=10,
        max_length=5000,
        description="Job offer text to score across 5 risk dimensions",
        examples=["Urgent! Pay Rs.999 via UPI. Earn 1 lakh/month. Contact hr@gmail.com"],
    )

    @field_validator("text")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        return v.strip()


class RiskAnalysisResponse(BaseModel):
    risk_score: int            = Field(..., ge=0, le=100, description="Composite risk score 0–100")
    risk_level: str            = Field(..., description="LOW | MEDIUM | HIGH")
    reasons:    list[str]      = Field(..., description="Triggered signal descriptions")
    breakdown:  dict[str, int] = Field(..., description="Per-dimension points awarded")
