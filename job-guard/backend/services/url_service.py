"""
services/url_service.py
------------------------
Thin service wrapper around the Phishing URL Detection Engine.
"""

import logging

from security.phishing_detector import analyze_url, analyze_text_for_urls

logger = logging.getLogger(__name__)


def run_url_scan(url: str) -> dict:
    """
    Analyse a single URL for phishing indicators.

    Returns
    -------
    dict
        Keys: url, is_phishing, risk_level, risk_score, reasons, breakdown
    """
    logger.info("Scanning URL: %s", url[:80])
    result = analyze_url(url)
    logger.info(
        "URL scan complete — level=%s score=%d phishing=%s",
        result.risk_level, result.risk_score, result.is_phishing,
    )
    return {
        "url":         result.url,
        "is_phishing": result.is_phishing,
        "risk_level":  result.risk_level,
        "risk_score":  result.risk_score,
        "reasons":     result.reasons,
        "breakdown":   result.breakdown,
    }


def run_text_url_scan(text: str) -> dict:
    """
    Extract and analyse every URL found in a block of text.

    Returns
    -------
    dict
        Keys: urls_found, phishing_count, results (list of per-URL dicts)
    """
    logger.info("Scanning text for URLs (%d chars)", len(text))
    results = analyze_text_for_urls(text)
    phishing_count = sum(1 for r in results if r.is_phishing)
    logger.info(
        "Text URL scan complete — found=%d phishing=%d",
        len(results), phishing_count,
    )
    return {
        "urls_found":     len(results),
        "phishing_count": phishing_count,
        "results": [
            {
                "url":         r.url,
                "is_phishing": r.is_phishing,
                "risk_level":  r.risk_level,
                "risk_score":  r.risk_score,
                "reasons":     r.reasons,
            }
            for r in results
        ],
    }
