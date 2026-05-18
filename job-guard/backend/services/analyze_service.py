"""
services/analyze_service.py
----------------------------
Rule-based signal detection + Groq AI explanation service.

Extracted from the original monolithic main.py.
All business logic lives here; the router only calls run_analysis().
"""

import logging
import os
import re

from groq import Groq

from core.config import get_settings

logger = logging.getLogger(__name__)

# ============================================================
# Signal Detector Functions
# ============================================================

def _check_salary(text: str) -> bool:
    """Flag unrealistically high salary offers targeting freshers."""
    t = text.lower()

    for val in re.findall(r'(\d+(?:\.\d+)?)\s*lpa', t):
        if float(val) > 4:
            return True

    for val in re.findall(
        r'(?:₹|rs\.?\s*)?(\d{1,3}(?:,\d{3})*|\d+)\s*(?:k\b|per\s+month|/\s*month|pm\b)', t
    ):
        if int(val.replace(',', '')) > 40000:
            return True

    for val in re.findall(r'(\d+)\s*k\b', t):
        if int(val) > 40:
            return True

    return False


def _check_email_domain(text: str) -> bool:
    """Flag personal/free email domains used by recruiters."""
    return bool(re.search(r'@(gmail|yahoo|outlook|hotmail)\.com', text, re.IGNORECASE))


def _check_payment_request(text: str) -> bool:
    """Flag any request for upfront payment or fees."""
    keywords = [
        r'registration\s+fee', r'deposit', r'\bupi\b', r'pay\s+now',
        r'advance\s+payment', r'security\s+amount', r'training\s+fee',
        r'joining\s+fee', r'refundable',
    ]
    return bool(re.search('|'.join(keywords), text, re.IGNORECASE))


def _check_urgency(text: str) -> bool:
    """Flag artificial urgency / pressure tactics."""
    keywords = [
        r'apply\s+now', r'limited\s+seats?', r'urgent\s+hir(ing|e)',
        r'last\s+date\s+today', r'immediate\s+joiner',
        r'only\s+\d+\s+seats?', r'\bhurry\b', r'today\s+only',
    ]
    return bool(re.search('|'.join(keywords), text, re.IGNORECASE))


def _check_missing_company(text: str) -> bool:
    """Flag absence of verifiable company information."""
    t = text.lower()
    has_website = bool(re.search(r'www\.', t))
    has_domain  = bool(re.search(r'\.(com|in|org|net|co\.in)\b', t))
    has_pvt_ltd = bool(re.search(r'pvt\.?\s*ltd|private\s+limited', t))
    return not (has_website or has_domain or has_pvt_ltd)


# Weight table: (detector, weight, reason_label)
_SIGNALS = [
    (_check_salary,          20, "Unusually high salary offer for a fresher"),
    (_check_email_domain,    25, "Uses Gmail instead of company email"),
    (_check_payment_request, 40, "Asks for registration/joining fee"),
    (_check_urgency,         15, "Uses urgency/pressure tactics"),
    (_check_missing_company, 20, "No company website or official domain found"),
]


def compute_risk(text: str) -> tuple[int, str, list[str]]:
    """
    Run all signal detectors and return (score, label, reasons).

    Returns
    -------
    tuple[int, str, list[str]]
        score  — 0–100
        label  — "Low Risk" | "Medium Risk" | "High Risk"
        reasons — list of triggered signal descriptions
    """
    score   = 0
    reasons: list[str] = []

    for detector, weight, reason in _SIGNALS:
        if detector(text):
            score += weight
            reasons.append(reason)

    score = min(score, 100)

    if score <= 30:
        label = "Low Risk"
    elif score <= 60:
        label = "Medium Risk"
    else:
        label = "High Risk"

    if not reasons:
        reasons = ["No suspicious signals detected"]

    return score, label, reasons


# ============================================================
# Groq AI Explanation
# ============================================================

def generate_explanation(text: str, reasons: list[str], label: str) -> str:
    """
    Call Groq LLM to produce a plain-English explanation of the risk.
    Falls back to a static message if the API key is missing or the call fails.
    """
    settings  = get_settings()
    api_key   = settings.groq_api_key

    if not api_key or api_key == "your_key_here":
        logger.warning("GROQ_API_KEY not set — returning static fallback explanation")
        return (
            f"This message was flagged as {label}. "
            f"Suspicious signals: {', '.join(reasons)}. "
            "Always verify the company on LinkedIn or their official website "
            "before applying or sharing any personal details."
        )

    try:
        client = Groq(api_key=api_key)
        numbered = "\n".join(f"{i+1}. {r}" for i, r in enumerate(reasons))

        completion = client.chat.completions.create(
            model=settings.groq_model,
            max_tokens=settings.groq_max_tokens,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a helpful fraud detection assistant for job seekers in India. "
                        "Explain why a job offer looks suspicious in simple, clear English. "
                        "Be helpful and calm, not scary. Keep it under 4 sentences."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"This job message was flagged as: {label}\n\n"
                        f"Suspicious signals:\n{numbered}\n\n"
                        f"Original message:\n{text}\n\n"
                        "Explain why this looks suspicious and give one practical "
                        "tip to verify if this job is real."
                    ),
                },
            ],
        )
        return completion.choices[0].message.content

    except Exception as exc:
        logger.error("Groq API call failed: %s", exc)
        return (
            f"This message was flagged as {label}. "
            f"Suspicious signals: {', '.join(reasons)}. "
            "Always verify the company on LinkedIn or their official website "
            "before applying or sharing any personal details."
        )


# ============================================================
# Public entry point
# ============================================================

def run_analysis(text: str) -> dict:
    """
    Run rule-based detection + Groq explanation and return a dict
    matching AnalyzeResponse schema.
    """
    logger.info("Running rule-based analysis on text (%d chars)", len(text))
    score, label, reasons = compute_risk(text)
    explanation = generate_explanation(text, reasons, label)
    logger.info("Analysis complete — label=%s score=%d", label, score)
    return {
        "score":       score,
        "label":       label,
        "reasons":     reasons,
        "explanation": explanation,
    }
