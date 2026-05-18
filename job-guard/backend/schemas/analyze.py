"""schemas/analyze.py — Rule-based analysis + Groq AI explanation models."""

from pydantic import BaseModel, Field, field_validator


class AnalyzeRequest(BaseModel):
    text: str = Field(
        ...,
        min_length=10,
        max_length=5000,
        description="Raw job offer message to analyse",
        examples=["Earn 80k/month from home. Pay registration fee via UPI. Apply now!"],
    )

    @field_validator("text")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        return v.strip()


class AnalyzeResponse(BaseModel):
    score:       int       = Field(..., ge=0, le=100, description="Risk score 0–100")
    label:       str       = Field(..., description="Low Risk | Medium Risk | High Risk")
    reasons:     list[str] = Field(..., description="Triggered signal descriptions")
    explanation: str       = Field(..., description="AI-generated plain-English explanation")
