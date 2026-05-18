"""schemas/url_scan.py — Phishing URL detection request/response models."""

from pydantic import BaseModel, Field, field_validator


class ScanUrlRequest(BaseModel):
    url: str = Field(
        ...,
        min_length=4,
        max_length=2048,
        description="Single URL to analyse for phishing indicators",
        examples=["https://secure-amazon-jobs-apply.tk/login"],
    )

    @field_validator("url")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        return v.strip()


class ScanUrlResponse(BaseModel):
    url:         str            = Field(..., description="The analysed URL")
    is_phishing: bool           = Field(..., description="True when risk_level is MEDIUM or HIGH")
    risk_level:  str            = Field(..., description="LOW | MEDIUM | HIGH")
    risk_score:  int            = Field(..., ge=0, le=100)
    reasons:     list[str]      = Field(..., description="Triggered detection signals")
    breakdown:   dict[str, int] = Field(..., description="Per-check points awarded")


# ── Bulk text scan ────────────────────────────────────────────

class ScanTextRequest(BaseModel):
    text: str = Field(
        ...,
        min_length=10,
        max_length=10000,
        description="Free text — every URL found inside will be analysed",
        examples=["Apply here: https://bit.ly/job2024 or visit http://192.168.1.1/register"],
    )

    @field_validator("text")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        return v.strip()


class UrlScanSummary(BaseModel):
    url:         str       = Field(..., description="The analysed URL")
    is_phishing: bool
    risk_level:  str
    risk_score:  int       = Field(..., ge=0, le=100)
    reasons:     list[str]


class ScanTextResponse(BaseModel):
    urls_found:     int               = Field(..., description="Total URLs extracted from text")
    phishing_count: int               = Field(..., description="Number flagged as phishing")
    results:        list[UrlScanSummary]
