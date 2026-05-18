"""
phishing_detector.py
--------------------
Phishing and malicious URL detection engine for Job Guard.

Analyses a single URL across eight detection layers and returns a
structured result with a risk level and specific reasons.

Detection Layers & Weights
---------------------------
  1. URL validation              — rejects malformed input early
  2. HTTP (no TLS)               → +20
  3. IP-address host             → +35
  4. URL shortener               → +30
  5. Excessive hyphens           → +20
  6. Suspicious TLD              → +25
  7. Suspicious subdomain        → +20
  8. Lookalike / typosquat domain→ +30
  9. Excessive URL length        → +10
 10. Suspicious path keywords    → +15
  ──────────────────────────────────
  Maximum raw total              → 205  (capped at 100)

Risk Levels
-----------
   0 – 30  →  LOW
  31 – 60  →  MEDIUM
  61 – 100 →  HIGH

Public API
----------
  analyze_url(url: str) -> PhishingResult
      Main entry point. Accepts a raw URL string.

  extract_urls(text: str) -> list[str]
      Helper — pull all URLs out of a block of text.

  analyze_text_for_urls(text: str) -> list[PhishingResult]
      Convenience wrapper — analyze every URL found in a text block.
"""

from __future__ import annotations

import ipaddress
import re
from dataclasses import dataclass, field
from urllib.parse import urlparse, unquote

import tldextract
import validators


# ============================================================
# Data Structures
# ============================================================

@dataclass
class PhishingResult:
    """Returned by analyze_url(). All fields are always populated."""
    url:        str
    is_phishing: bool          # True when risk_level is MEDIUM or HIGH
    risk_level: str            # "LOW" | "MEDIUM" | "HIGH"
    risk_score: int            # 0–100
    reasons:    list[str]      # human-readable triggered signals
    breakdown:  dict[str, int] # check_name → points awarded


# ============================================================
# Reference Data
# ============================================================

# Well-known URL shortening services
_SHORTENER_HOSTS: frozenset[str] = frozenset({
    "bit.ly", "tinyurl.com", "t.co", "goo.gl", "ow.ly", "rb.gy",
    "cutt.ly", "short.io", "is.gd", "buff.ly", "adf.ly", "tiny.cc",
    "lnkd.in", "shorte.st", "clck.ru", "qr.ae", "v.gd", "x.co",
    "shorturl.at", "snip.ly", "bl.ink", "rebrand.ly",
})

# TLDs heavily abused in phishing campaigns
_SUSPICIOUS_TLDS: frozenset[str] = frozenset({
    "tk", "ml", "ga", "cf", "gq",   # free Freenom TLDs
    "xyz", "top", "club", "online",  # cheap, high-abuse TLDs
    "work", "click", "link", "live",
    "pw", "cc", "ws", "biz",
})

# Legitimate job-related domains — presence lowers suspicion
_TRUSTED_DOMAINS: frozenset[str] = frozenset({
    "linkedin.com", "naukri.com", "indeed.com", "shine.com",
    "monster.com", "glassdoor.com", "internshala.com", "foundit.in",
    "timesjobs.com", "freshersworld.com", "apna.co", "hirist.com",
    # Major Indian IT / product companies
    "infosys.com", "tcs.com", "wipro.com", "hcltech.com",
    "cognizant.com", "accenture.com", "capgemini.com",
    "techmahindra.com", "ibm.com", "amazon.com", "amazon.in",
    "google.com", "microsoft.com", "flipkart.com",
    "swiggy.com", "zomato.com", "paytm.com", "phonepe.com",
    # Government / official
    "gov.in", "nic.in", "ssc.nic.in", "upsc.gov.in",
})

# Brands commonly impersonated in job scams
_IMPERSONATION_TARGETS: list[tuple[str, str]] = [
    # (legitimate_domain, regex_that_matches_fakes)
    ("amazon.com",    r"amaz[o0]n[^.]*\.(com|in|net|org|tk|xyz)"),
    ("google.com",    r"go+gle[^.]*\.(com|in|net|org|tk|xyz)"),
    ("infosys.com",   r"inf[o0]sys[^.]*\.(com|in|net|org|tk|xyz)"),
    ("tcs.com",       r"tcs[\-_]?(job|hire|career|recruit)[^.]*\."),
    ("wipro.com",     r"w[i1]pro[^.]*\.(com|in|net|org|tk|xyz)"),
    ("linkedin.com",  r"l[i1]nked[i1]n[^.]*\.(com|in|net|org|tk|xyz)"),
    ("naukri.com",    r"naukr[i1][^.]*\.(com|in|net|org|tk|xyz)"),
    ("microsoft.com", r"micr[o0]s[o0]ft[^.]*\.(com|in|net|org|tk|xyz)"),
    ("flipkart.com",  r"fl[i1]pkart[^.]*\.(com|in|net|org|tk|xyz)"),
]

# Keywords in URL path that indicate phishing / scam pages
_SUSPICIOUS_PATH_KEYWORDS: list[str] = [
    "login", "signin", "verify", "account", "secure", "update",
    "confirm", "banking", "payment", "wallet", "otp", "reset",
    "free-job", "job-offer", "apply-now", "registration-fee",
    "joining-fee", "work-from-home-earn",
]

# Regex to extract URLs from free text
_URL_EXTRACT_RE = re.compile(
    r"(?:https?://|www\.)\S+",
    re.IGNORECASE,
)


# ============================================================
# Internal helpers
# ============================================================

def _normalize_url(raw: str) -> str:
    """Ensure the URL has a scheme so urlparse works correctly."""
    raw = raw.strip()
    if not re.match(r"^https?://", raw, re.IGNORECASE):
        raw = "http://" + raw
    return raw


def _is_ip_host(hostname: str) -> bool:
    """Return True if the hostname is a raw IPv4 or IPv6 address."""
    try:
        ipaddress.ip_address(hostname)
        return True
    except ValueError:
        return False


def _registered_domain(extracted: tldextract.tldextract.ExtractResult) -> str:
    """Return 'domain.tld' from a tldextract result."""
    return f"{extracted.domain}.{extracted.suffix}" if extracted.suffix else extracted.domain


# ============================================================
# Detection Checks
# ============================================================

def _check_http(parsed: "ParseResult") -> tuple[int, str] | None:
    """Flag plain HTTP — no TLS encryption."""
    if parsed.scheme.lower() == "http":
        return 20, "Uses HTTP instead of HTTPS — data is transmitted unencrypted"
    return None


def _check_ip_address(hostname: str) -> tuple[int, str] | None:
    """Flag IP-address-based URLs — legitimate sites use domain names."""
    if _is_ip_host(hostname):
        return 35, f"Host is a raw IP address ({hostname}) — legitimate companies use domain names"
    return None


def _check_shortener(hostname: str) -> tuple[int, str] | None:
    """Flag known URL shorteners — used to hide the real destination."""
    clean = hostname.lstrip("www.")
    if clean in _SHORTENER_HOSTS:
        return 30, f"URL shortener detected ({clean}) — real destination is hidden"
    return None


def _check_excessive_hyphens(
    hostname: str,
    extracted: "tldextract.tldextract.ExtractResult",
) -> tuple[int, str] | None:
    """
    Flag domains with 3+ hyphens in the registered domain.
    Phishing domains often look like: secure-amazon-jobs-apply.tk
    """
    domain_part = extracted.domain
    hyphen_count = domain_part.count("-")
    if hyphen_count >= 3:
        return 20, (
            f"Domain contains {hyphen_count} hyphens ({domain_part}) — "
            "a common pattern in phishing domains"
        )
    if hyphen_count == 2:
        return 10, (
            f"Domain contains multiple hyphens ({domain_part}) — "
            "verify this is a legitimate employer site"
        )
    return None


def _check_suspicious_tld(
    extracted: "tldextract.tldextract.ExtractResult",
) -> tuple[int, str] | None:
    """Flag TLDs that are disproportionately used in phishing campaigns."""
    tld = extracted.suffix.lower() if extracted.suffix else ""
    # Handle multi-part TLDs like co.uk — check the rightmost part
    rightmost = tld.split(".")[-1]
    if rightmost in _SUSPICIOUS_TLDS:
        return 25, (
            f"Suspicious top-level domain (.{rightmost}) — "
            "frequently used in phishing and scam sites"
        )
    return None


def _check_suspicious_subdomain(
    extracted: "tldextract.tldextract.ExtractResult",
) -> tuple[int, str] | None:
    """
    Flag subdomains that impersonate trusted brands or use
    deceptive keywords (secure-, login-, verify-, jobs-).
    """
    subdomain = extracted.subdomain.lower()
    if not subdomain or subdomain == "www":
        return None

    # Subdomain contains a trusted brand name (e.g. amazon.fake-jobs.tk)
    for trusted in _TRUSTED_DOMAINS:
        brand = trusted.split(".")[0]  # e.g. "amazon" from "amazon.com"
        if brand in subdomain and brand not in extracted.domain:
            return 20, (
                f"Subdomain impersonates '{brand}' brand "
                f"(subdomain: {subdomain}) — classic phishing technique"
            )

    # Subdomain contains deceptive keywords
    deceptive_sub_keywords = [
        "secure", "login", "verify", "account", "jobs",
        "career", "apply", "hr", "recruit", "offer",
    ]
    for kw in deceptive_sub_keywords:
        if kw in subdomain:
            return 20, (
                f"Subdomain contains deceptive keyword '{kw}' "
                f"({subdomain}.{extracted.domain}.{extracted.suffix})"
            )

    return None


def _check_typosquat(
    extracted: "tldextract.tldextract.ExtractResult",
    full_host: str,
) -> tuple[int, str] | None:
    """
    Detect lookalike / typosquatting domains that impersonate
    well-known brands using character substitution or extra words.
    """
    reg_domain = _registered_domain(extracted)

    # Skip if it IS the trusted domain
    if reg_domain in _TRUSTED_DOMAINS:
        return None

    for legitimate, pattern in _IMPERSONATION_TARGETS:
        if re.search(pattern, full_host, re.IGNORECASE):
            brand = legitimate.split(".")[0]
            return 30, (
                f"Domain appears to impersonate '{brand}' "
                f"({reg_domain}) — possible typosquatting attack"
            )

    return None


def _check_url_length(url: str) -> tuple[int, str] | None:
    """Flag excessively long URLs — often used to bury the real domain."""
    if len(url) > 200:
        return 10, (
            f"Unusually long URL ({len(url)} characters) — "
            "may be designed to obscure the real destination"
        )
    return None


def _check_path_keywords(parsed: "ParseResult") -> tuple[int, str] | None:
    """Flag suspicious keywords in the URL path or query string."""
    path_and_query = unquote(
        (parsed.path + "?" + parsed.query).lower()
    )
    for kw in _SUSPICIOUS_PATH_KEYWORDS:
        if kw in path_and_query:
            return 15, (
                f"URL path contains suspicious keyword '{kw}' — "
                "commonly seen in phishing and credential-harvesting pages"
            )
    return None


# ============================================================
# Risk Classifier
# ============================================================

def _classify(score: int) -> str:
    if score <= 30:
        return "LOW"
    if score <= 60:
        return "MEDIUM"
    return "HIGH"


# ============================================================
# Public API
# ============================================================

def analyze_url(url: str) -> PhishingResult:
    """
    Analyse a single URL for phishing and malicious indicators.

    Parameters
    ----------
    url : str
        Raw URL string (with or without scheme).

    Returns
    -------
    PhishingResult
        is_phishing — True when risk_level is MEDIUM or HIGH
        risk_level  — "LOW" | "MEDIUM" | "HIGH"
        risk_score  — int 0–100
        reasons     — list of human-readable triggered signals
        breakdown   — dict of check_name → points awarded
    """
    # ── 1. Normalise & validate ──────────────────────────────
    normalised = _normalize_url(url)

    if not validators.url(normalised):
        return PhishingResult(
            url=url,
            is_phishing=False,
            risk_level="LOW",
            risk_score=0,
            reasons=["Invalid or malformed URL — could not be analysed."],
            breakdown={},
        )

    parsed   = urlparse(normalised)
    hostname = parsed.hostname or ""
    extracted = tldextract.extract(normalised)
    reg_domain = _registered_domain(extracted)

    # ── 2. Trusted domain fast-path ──────────────────────────
    # If the registered domain is in our trusted list, skip all checks
    # (still flag HTTP even for trusted domains)
    if reg_domain in _TRUSTED_DOMAINS:
        http_hit = _check_http(parsed)
        if http_hit:
            return PhishingResult(
                url=url,
                is_phishing=False,
                risk_level="LOW",
                risk_score=http_hit[0],
                reasons=[http_hit[1]],
                breakdown={"http_no_tls": http_hit[0]},
            )
        return PhishingResult(
            url=url,
            is_phishing=False,
            risk_level="LOW",
            risk_score=0,
            reasons=["URL belongs to a trusted, verified domain."],
            breakdown={},
        )

    # ── 3. Run all checks ────────────────────────────────────
    checks: list[tuple[str, tuple[int, str] | None]] = [
        ("http_no_tls",          _check_http(parsed)),
        ("ip_address_host",      _check_ip_address(hostname)),
        ("url_shortener",        _check_shortener(hostname)),
        ("excessive_hyphens",    _check_excessive_hyphens(hostname, extracted)),
        ("suspicious_tld",       _check_suspicious_tld(extracted)),
        ("suspicious_subdomain", _check_suspicious_subdomain(extracted)),
        ("typosquatting",        _check_typosquat(extracted, hostname)),
        ("url_length",           _check_url_length(normalised)),
        ("suspicious_path",      _check_path_keywords(parsed)),
    ]

    raw_score = 0
    reasons:   list[str]      = []
    breakdown: dict[str, int] = {}

    for check_name, result in checks:
        if result is not None:
            points, reason = result
            raw_score          += points
            breakdown[check_name] = points
            reasons.append(reason)

    final_score = min(raw_score, 100)
    level       = _classify(final_score)

    if not reasons:
        reasons = ["No phishing indicators detected — URL appears clean."]

    return PhishingResult(
        url=url,
        is_phishing=(level in ("MEDIUM", "HIGH")),
        risk_level=level,
        risk_score=final_score,
        reasons=reasons,
        breakdown=breakdown,
    )


def extract_urls(text: str) -> list[str]:
    """
    Extract all URLs from a block of free text.

    Parameters
    ----------
    text : str
        Any text that may contain URLs.

    Returns
    -------
    list[str]
        Deduplicated list of URL strings found in the text.
    """
    found = _URL_EXTRACT_RE.findall(text)
    # Deduplicate while preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for url in found:
        # Strip trailing punctuation that isn't part of the URL
        url = url.rstrip(".,;:!?)\"'")
        if url not in seen:
            seen.add(url)
            unique.append(url)
    return unique


def analyze_text_for_urls(text: str) -> list[PhishingResult]:
    """
    Extract every URL from a text block and analyse each one.

    Parameters
    ----------
    text : str
        Raw job offer / message text.

    Returns
    -------
    list[PhishingResult]
        One PhishingResult per unique URL found.
        Returns an empty list if no URLs are present.
    """
    urls = extract_urls(text)
    return [analyze_url(u) for u in urls]
