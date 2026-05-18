"""
scam_score.py
-------------
Scam Risk Scoring Engine for Job Guard.

Evaluates a job description across five independent risk dimensions and
produces a composite risk score (0–100), a risk level, and a list of
human-readable reasons that explain the score.

Risk Dimensions & Weights
--------------------------
  suspicious_keywords  →  up to +20
  fake_email_domain    →  +25  (binary)
  unrealistic_salary   →  up to +15
  phishing_url         →  up to +30
  missing_company_info →  +20  (binary)
  ─────────────────────────────────
  Maximum raw total    →  110  (capped at 100)

Risk Levels
-----------
   0 – 30  →  LOW
  31 – 60  →  MEDIUM
  61 – 100 →  HIGH

Public API
----------
  score_text(text: str) -> ScamScoreResult
      Main entry point. Returns a ScamScoreResult dataclass.

  ScamScoreResult
      .risk_score  : int          (0–100)
      .risk_level  : str          ("LOW" | "MEDIUM" | "HIGH")
      .reasons     : list[str]    (triggered signal descriptions)
      .breakdown   : dict         (per-dimension scores for debugging)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import NamedTuple


# ============================================================
# Data Structures
# ============================================================

@dataclass
class ScamScoreResult:
    """Returned by score_text(). All fields are populated on every call."""
    risk_score: int
    risk_level: str                    # "LOW" | "MEDIUM" | "HIGH"
    reasons:    list[str]
    breakdown:  dict[str, int]         # dimension → points awarded


class _Signal(NamedTuple):
    """Internal representation of a single matched signal."""
    dimension: str   # which scoring dimension triggered this
    points:    int   # points awarded for this specific match
    reason:    str   # human-readable description shown to the user


# ============================================================
# Dimension 1 — Suspicious Keywords  (max +20)
# ============================================================
# Each keyword group carries a weight. Multiple groups can fire,
# but the dimension total is capped at 20.

_KEYWORD_GROUPS: list[tuple[int, str, list[str]]] = [
    # (points, reason_label, [regex patterns])
    (
        10,
        "Suspicious payment request detected",
        [
            r"registration\s+fee",
            r"joining\s+fee",
            r"training\s+fee",
            r"security\s+(amount|deposit)",
            r"advance\s+payment",
            r"\bdeposit\b",
            r"\bupi\b",
            r"pay\s+now",
            r"refundable",
        ],
    ),
    (
        7,
        "Urgency or pressure language detected",
        [
            r"apply\s+now",
            r"limited\s+seats?",
            r"urgent\s+hir(ing|e)",
            r"last\s+date\s+today",
            r"immediate\s+joiner",
            r"only\s+\d+\s+seats?",
            r"\bhurry\b",
            r"today\s+only",
            r"don['\u2019]?t\s+miss",
            r"offer\s+expires",
        ],
    ),
    (
        5,
        "Vague or unverifiable job claims",
        [
            r"no\s+experience\s+(needed|required)",
            r"no\s+interview",
            r"direct\s+joining",
            r"without\s+interview",
            r"guaranteed\s+(job|selection|income)",
            r"100\s*%\s*(job|placement|guarantee)",
            r"work\s+from\s+home.{0,20}earn",
        ],
    ),
    (
        5,
        "Requests for sensitive personal information",
        [
            r"send\s+(your\s+)?(passport|aadhaar|pan\s+card|bank\s+details|account\s+number)",
            r"share\s+(your\s+)?(aadhaar|pan|bank)",
            r"otp\b",
            r"cvv\b",
            r"pin\s+number",
        ],
    ),
]

_KEYWORD_DIMENSION_CAP = 20


def _score_suspicious_keywords(text: str) -> list[_Signal]:
    """
    Check all keyword groups against the text.
    Returns one _Signal per triggered group, total capped at 20.
    """
    signals: list[_Signal] = []
    total = 0
    text_lower = text.lower()

    for points, reason, patterns in _KEYWORD_GROUPS:
        if total >= _KEYWORD_DIMENSION_CAP:
            break
        combined = "|".join(patterns)
        if re.search(combined, text_lower):
            awarded = min(points, _KEYWORD_DIMENSION_CAP - total)
            signals.append(_Signal("suspicious_keywords", awarded, reason))
            total += awarded

    return signals


# ============================================================
# Dimension 2 — Fake / Free Email Domain  (+25, binary)
# ============================================================

_FREE_DOMAINS = re.compile(
    r"@(gmail|yahoo|hotmail|outlook|rediffmail|ymail|live|msn|icloud)\.com",
    re.IGNORECASE,
)

_RECRUITER_CONTEXT = re.compile(
    r"(contact|email|reach|send|apply|cv|resume|hr).{0,60}@",
    re.IGNORECASE,
)


def _score_fake_email_domain(text: str) -> list[_Signal]:
    """
    Flag personal/free email domains used in a recruiter context.
    A bare mention of gmail.com (e.g. 'do not use gmail') is not flagged
    unless it appears near recruiter-context words.
    """
    signals: list[_Signal] = []

    # Find all email addresses in the text
    emails = re.findall(r"[\w.\-+]+@[\w.\-]+", text, re.IGNORECASE)
    for email in emails:
        if _FREE_DOMAINS.search(email):
            signals.append(_Signal(
                "fake_email_domain",
                25,
                f"Recruiter uses a personal email domain ({email.split('@')[1]}) "
                "instead of a corporate address",
            ))
            break  # one flag is enough; don't double-count

    # Fallback: free domain mentioned near recruiter context even without full email
    if not signals and _FREE_DOMAINS.search(text) and _RECRUITER_CONTEXT.search(text):
        signals.append(_Signal(
            "fake_email_domain",
            25,
            "Free email domain (Gmail/Yahoo/Hotmail) mentioned in recruiter context",
        ))

    return signals


# ============================================================
# Dimension 3 — Unrealistic Salary  (up to +15)
# ============================================================

_SALARY_DIMENSION_CAP = 15


def _extract_monthly_inr(text: str) -> list[float]:
    """
    Extract all monthly salary figures (in INR) mentioned in the text.
    Handles: ₹50,000 / 50k / 50000/month / 5 LPA (converted to monthly).
    """
    amounts: list[float] = []
    t = text.lower()

    # LPA → monthly (÷ 12)
    for m in re.finditer(r"(\d+(?:\.\d+)?)\s*lpa", t):
        amounts.append(float(m.group(1)) * 100_000 / 12)

    # Explicit monthly: 50,000/month | ₹50000 per month | 50k pm
    for m in re.finditer(
        r"(?:₹|rs\.?\s*)?(\d{1,3}(?:,\d{3})*|\d+)\s*"
        r"(?:k\b)?(?:\s*(?:per\s+month|/\s*month|p\.?m\.?))",
        t,
    ):
        raw = m.group(1).replace(",", "")
        val = float(raw)
        # If the number looks like a "k" shorthand (e.g. "50 per month" → 50 ≠ 50k)
        # detect "k" suffix separately
        if re.search(r"\d\s*k\b", m.group(0)):
            val *= 1000
        amounts.append(val)

    # Bare "50k" / "80k" without explicit /month — treat as monthly shorthand
    for m in re.finditer(r"(\d+)\s*k\b", t):
        amounts.append(float(m.group(1)) * 1000)

    return amounts


def _score_unrealistic_salary(text: str) -> list[_Signal]:
    """
    Award points based on how far the salary exceeds realistic fresher ranges.

    Thresholds (monthly INR):
      > 40,000  → +5   (elevated but possible)
      > 80,000  → +10  (very high for fresher)
      > 150,000 → +15  (almost certainly fake)
    """
    signals: list[_Signal] = []
    amounts = _extract_monthly_inr(text)
    if not amounts:
        return signals

    max_salary = max(amounts)

    if max_salary > 150_000:
        signals.append(_Signal(
            "unrealistic_salary",
            15,
            f"Extremely unrealistic salary offer "
            f"(~₹{int(max_salary):,}/month) — far beyond market rate for freshers",
        ))
    elif max_salary > 80_000:
        signals.append(_Signal(
            "unrealistic_salary",
            10,
            f"Unrealistically high salary offer "
            f"(~₹{int(max_salary):,}/month) for an entry-level role",
        ))
    elif max_salary > 40_000:
        signals.append(_Signal(
            "unrealistic_salary",
            5,
            f"Elevated salary claim (~₹{int(max_salary):,}/month) "
            "that warrants verification",
        ))

    return signals


# ============================================================
# Dimension 4 — Phishing URLs  (up to +30)
# ============================================================

# Trusted domains — presence of these reduces suspicion
_TRUSTED_DOMAINS: set[str] = {
    "linkedin.com", "naukri.com", "indeed.com", "shine.com",
    "monster.com", "glassdoor.com", "internshala.com", "foundit.in",
    "timesjobs.com", "freshersworld.com",
    # Major Indian IT companies
    "infosys.com", "tcs.com", "wipro.com", "hcltech.com",
    "cognizant.com", "accenture.com", "capgemini.com", "techmahindra.com",
    "ibm.com", "amazon.com", "google.com", "microsoft.com",
    "flipkart.com", "swiggy.com", "zomato.com",
}

# Patterns that indicate a phishing or suspicious URL
_PHISHING_URL_PATTERNS: list[tuple[int, str, str]] = [
    # (points, reason, regex)
    (
        30,
        "Contains a URL shortener link — commonly used to hide phishing destinations",
        r"https?://(bit\.ly|tinyurl\.com|t\.co|goo\.gl|ow\.ly|rb\.gy|cutt\.ly|short\.io)/",
    ),
    (
        25,
        "Contains a suspicious free-hosting or form-collection URL",
        r"https?://[^\s]*(\.tk|\.ml|\.ga|\.cf|\.gq|forms\.gle|docs\.google\.com/forms)[^\s]*",
    ),
    (
        20,
        "URL contains IP address instead of a domain name — phishing indicator",
        r"https?://\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}",
    ),
    (
        15,
        "URL contains lookalike or misspelled domain (typosquatting)",
        r"https?://[^\s]*(1nfosys|w1pro|tcs-job|amazon-job|hr-amazon|"
        r"naukri-job|linkedin-job|job-offer|free-job)[^\s]*",
    ),
    (
        10,
        "Suspicious Telegram or WhatsApp link used for recruitment",
        r"(t\.me/|wa\.me/|whatsapp\.com/|telegram\.me/)",
    ),
]

_URL_RE = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)


def _is_trusted(url: str) -> bool:
    """Return True if the URL belongs to a known-trusted domain."""
    url_lower = url.lower()
    return any(domain in url_lower for domain in _TRUSTED_DOMAINS)


def _score_phishing_urls(text: str) -> list[_Signal]:
    """
    Scan for phishing URL patterns. Trusted domains are skipped.
    Only the highest-scoring pattern per URL is counted to avoid
    double-penalising the same link.
    """
    signals: list[_Signal] = []
    seen_patterns: set[str] = set()
    total = 0

    for points, reason, pattern in _PHISHING_URL_PATTERNS:
        if total >= 30:
            break
        if pattern in seen_patterns:
            continue
        if re.search(pattern, text, re.IGNORECASE):
            # Skip if the match is inside a trusted domain
            match = re.search(pattern, text, re.IGNORECASE)
            if match and _is_trusted(match.group(0)):
                continue
            awarded = min(points, 30 - total)
            signals.append(_Signal("phishing_url", awarded, reason))
            seen_patterns.add(pattern)
            total += awarded

    # Also flag any raw URL that is not from a trusted domain
    for url_match in _URL_RE.finditer(text):
        url = url_match.group(0)
        if not _is_trusted(url) and total < 30:
            # Only flag if no phishing pattern already caught it
            already_flagged = any(
                re.search(p, url, re.IGNORECASE)
                for _, _, p in _PHISHING_URL_PATTERNS
            )
            if not already_flagged:
                awarded = min(10, 30 - total)
                signals.append(_Signal(
                    "phishing_url",
                    awarded,
                    f"Unrecognised external URL present — verify before clicking: "
                    f"{url[:60]}{'...' if len(url) > 60 else ''}",
                ))
                total += awarded
                break  # one generic URL warning is enough

    return signals


# ============================================================
# Dimension 5 — Missing Company Information  (+20, binary)
# ============================================================

_COMPANY_INDICATORS = re.compile(
    r"(pvt\.?\s*ltd|private\s+limited|llp\b|inc\.|corp\.|"
    r"www\.|\.com\b|\.in\b|\.org\b|\.net\b|\.co\.in\b|"
    r"careers\.|jobs\.|linkedin\.com/company)",
    re.IGNORECASE,
)

_VAGUE_COMPANY_TERMS = re.compile(
    r"\b(top\s+mnc|good\s+company|reputed\s+firm|leading\s+company|"
    r"well[\s-]known\s+company|multinational\s+company|"
    r"a\s+reputed\s+organisation|famous\s+company)\b",
    re.IGNORECASE,
)


def _score_missing_company(text: str) -> list[_Signal]:
    """
    Flag the absence of verifiable company information.
    Deducted only when no real company indicator is found.
    Vague terms add context to the reason message.
    """
    signals: list[_Signal] = []

    has_real_info = bool(_COMPANY_INDICATORS.search(text))
    if has_real_info:
        return signals  # company info present — no penalty

    vague_match = _VAGUE_COMPANY_TERMS.search(text)
    if vague_match:
        reason = (
            f"No verifiable company details found; "
            f"vague term used instead: \"{vague_match.group(0)}\""
        )
    else:
        reason = (
            "No company name, website, or official domain mentioned — "
            "cannot verify the employer's identity"
        )

    signals.append(_Signal("missing_company_info", 20, reason))
    return signals


# ============================================================
# Risk Level Classifier
# ============================================================

def _classify_level(score: int) -> str:
    if score <= 30:
        return "LOW"
    if score <= 60:
        return "MEDIUM"
    return "HIGH"


# ============================================================
# Public Entry Point
# ============================================================

def score_text(text: str) -> ScamScoreResult:
    """
    Run all five risk dimensions against the input text and return
    a ScamScoreResult with the composite score, level, reasons, and
    per-dimension breakdown.

    Parameters
    ----------
    text : str
        Raw job offer / description text (any length).

    Returns
    -------
    ScamScoreResult
        risk_score  — int, 0–100
        risk_level  — "LOW" | "MEDIUM" | "HIGH"
        reasons     — list of human-readable signal descriptions
        breakdown   — dict mapping dimension name → points awarded
    """
    if not isinstance(text, str) or not text.strip():
        return ScamScoreResult(
            risk_score=0,
            risk_level="LOW",
            reasons=["No text provided for analysis."],
            breakdown={},
        )

    # Run all five dimensions
    all_signals: list[_Signal] = []
    all_signals.extend(_score_suspicious_keywords(text))
    all_signals.extend(_score_fake_email_domain(text))
    all_signals.extend(_score_unrealistic_salary(text))
    all_signals.extend(_score_phishing_urls(text))
    all_signals.extend(_score_missing_company(text))

    # Aggregate
    raw_score = sum(s.points for s in all_signals)
    final_score = min(raw_score, 100)

    # Build breakdown dict (dimension → total points from that dimension)
    breakdown: dict[str, int] = {}
    for sig in all_signals:
        breakdown[sig.dimension] = breakdown.get(sig.dimension, 0) + sig.points

    # Deduplicate reasons while preserving order
    seen: set[str] = set()
    reasons: list[str] = []
    for sig in all_signals:
        if sig.reason not in seen:
            reasons.append(sig.reason)
            seen.add(sig.reason)

    if not reasons:
        reasons = ["No suspicious signals detected — job offer appears clean."]

    return ScamScoreResult(
        risk_score=final_score,
        risk_level=_classify_level(final_score),
        reasons=reasons,
        breakdown=breakdown,
    )
