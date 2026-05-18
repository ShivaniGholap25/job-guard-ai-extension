"""routers/url_scan.py — POST /scan-url and POST /scan-urls."""

import logging

from fastapi import APIRouter, HTTPException

from schemas.url_scan import (
    ScanUrlRequest,
    ScanUrlResponse,
    ScanTextRequest,
    ScanTextResponse,
    UrlScanSummary,
)
from services.url_service import run_url_scan, run_text_url_scan

logger = logging.getLogger(__name__)
router = APIRouter(tags=["URL Scanner"])


@router.post(
    "/scan-url",
    response_model=ScanUrlResponse,
    summary="Phishing URL analyser",
    response_description="Phishing risk assessment for a single URL",
)
def scan_url(payload: ScanUrlRequest) -> ScanUrlResponse:
    """
    Analyse a single URL across **9 detection layers**:

    | Layer | Signal |
    |---|---|
    | `http_no_tls` | Plain HTTP — no encryption |
    | `ip_address_host` | Raw IP instead of domain name |
    | `url_shortener` | bit.ly, tinyurl, rb.gy, etc. |
    | `excessive_hyphens` | 3+ hyphens in domain |
    | `suspicious_tld` | .tk .ml .xyz .top etc. |
    | `suspicious_subdomain` | Brand name in subdomain |
    | `typosquatting` | Lookalike domains for major brands |
    | `url_length` | URLs over 200 characters |
    | `suspicious_path` | /login /verify /otp /joining-fee etc. |

    Returns `is_phishing=true` when `risk_level` is MEDIUM or HIGH.
    """
    try:
        result = run_url_scan(payload.url)
        return ScanUrlResponse(**result)
    except Exception as exc:
        logger.exception("Error in /scan-url for url=%s", payload.url[:80])
        raise HTTPException(status_code=500, detail=f"URL scan failed: {exc}")


@router.post(
    "/scan-urls",
    response_model=ScanTextResponse,
    summary="Bulk URL scanner from free text",
    response_description="Phishing analysis for every URL found in the text",
)
def scan_text_urls(payload: ScanTextRequest) -> ScanTextResponse:
    """
    Extract **every URL** from a job description or message and analyse
    each one for phishing indicators in a single call.

    Useful for scanning a full job post without manually extracting URLs.
    Returns a summary count plus per-URL results.
    """
    try:
        data = run_text_url_scan(payload.text)
        summaries = [UrlScanSummary(**r) for r in data["results"]]
        return ScanTextResponse(
            urls_found=data["urls_found"],
            phishing_count=data["phishing_count"],
            results=summaries,
        )
    except Exception as exc:
        logger.exception("Error in /scan-urls")
        raise HTTPException(status_code=500, detail=f"URL scan failed: {exc}")
