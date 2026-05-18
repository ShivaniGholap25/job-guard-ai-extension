# ============================================================
# job-guard: Fake Job Offer Detector — FastAPI Backend
# ============================================================

import os
import re

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from groq import Groq
from pydantic import BaseModel

# Load environment variables from .env file
load_dotenv()

# ── NLP predictor (lazy-loads model on first request) ────────
from api.predict import predictor

# ── Scam Risk Scoring Engine ─────────────────────────────────
from security.scam_score import score_text

# ── Phishing / URL Detection Engine ──────────────────────────
from security.phishing_detector import analyze_url, analyze_text_for_urls

# ── App initialization ───────────────────────────────────────
app = FastAPI(
    title="Job Guard API",
    description="Fake Job Offer Detector backend",
    version="0.3.0",
)

# ── CORS middleware ──────────────────────────────────────────
# Allow all origins so the Chrome extension can reach this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Request / Response schemas ───────────────────────────────
class AnalyzeRequest(BaseModel):
    text: str  # the raw job offer message to analyze

class AnalyzeResponse(BaseModel):
    score: int           # 0–100 risk score (higher = more suspicious)
    label: str           # "Low Risk" | "Medium Risk" | "High Risk"
    reasons: list[str]   # human-readable signals that influenced the score
    explanation: str     # AI-generated plain-English explanation

class PredictRequest(BaseModel):
    job_description: str  # raw job description text for NLP classification

class PredictResponse(BaseModel):
    prediction: str    # "Genuine" | "Suspicious" | "Fake"
    confidence: float  # 0.0–100.0 percentage
    reason: str        # human-readable explanation of the prediction

class RiskScoreRequest(BaseModel):
    text: str          # raw job offer text to score

class RiskScoreResponse(BaseModel):
    risk_score: int            # 0–100 composite scam risk score
    risk_level: str            # "LOW" | "MEDIUM" | "HIGH"
    reasons:    list[str]      # triggered signal descriptions
    breakdown:  dict[str, int] # per-dimension points for transparency

class CheckUrlRequest(BaseModel):
    url: str           # single URL to analyse for phishing indicators

class CheckUrlResponse(BaseModel):
    url:         str
    is_phishing: bool
    risk_level:  str            # "LOW" | "MEDIUM" | "HIGH"
    risk_score:  int            # 0–100
    reasons:     list[str]
    breakdown:   dict[str, int]

class ScanTextUrlsRequest(BaseModel):
    text: str          # free text — all URLs inside will be analysed

class UrlScanSummary(BaseModel):
    url:         str
    is_phishing: bool
    risk_level:  str
    risk_score:  int
    reasons:     list[str]

class ScanTextUrlsResponse(BaseModel):
    urls_found:      int
    phishing_count:  int
    results:         list[UrlScanSummary]


# ============================================================
# Signal Detector Functions
# ============================================================

# ── Signal 1: Unrealistically high salary ───────────────────
# Flags monthly salaries above ₹40,000 or annual packages above 4 LPA,
# which are unusually high offers typically used to lure freshers.
def check_salary(text: str) -> bool:
    text_lower = text.lower()

    # Match LPA patterns like "5 LPA", "6lpa", "10 LPA", "4.5 LPA"
    lpa_pattern = re.findall(r'(\d+(?:\.\d+)?)\s*lpa', text_lower)
    for val in lpa_pattern:
        if float(val) > 4:
            return True

    # Match monthly salary patterns like ₹50,000 / 50,000 / 50000
    monthly_pattern = re.findall(
        r'(?:₹|rs\.?\s*)?(\d{1,3}(?:,\d{3})*|\d+)\s*(?:k\b|per\s+month|/\s*month|pm\b)',
        text_lower
    )
    for val in monthly_pattern:
        clean = val.replace(',', '')
        if int(clean) > 40000:
            return True

    # Catch bare "50k", "60k" shorthand
    k_pattern = re.findall(r'(\d+)\s*k\b', text_lower)
    for val in k_pattern:
        if int(val) > 40:
            return True

    return False


# ── Signal 2: Free/personal email domain used by recruiter ──
# Legitimate companies use corporate email domains.
# Recruiters using Gmail, Yahoo, Outlook, or Hotmail are a red flag.
def check_email_domain(text: str) -> bool:
    free_domains = r'@(gmail|yahoo|outlook|hotmail)\.com'
    return bool(re.search(free_domains, text, re.IGNORECASE))


# ── Signal 3: Payment or fee request ────────────────────────
# Any job that asks the candidate to pay money upfront is almost
# certainly a scam. Catches registration fees, deposits, UPI requests, etc.
def check_payment_request(text: str) -> bool:
    keywords = [
        r'registration\s+fee',
        r'deposit',
        r'\bupi\b',
        r'pay\s+now',
        r'advance\s+payment',
        r'security\s+amount',
        r'training\s+fee',
        r'joining\s+fee',
        r'refundable',
    ]
    return bool(re.search('|'.join(keywords), text, re.IGNORECASE))


# ── Signal 4: Urgency / pressure tactics ────────────────────
# Scammers create artificial urgency to prevent candidates from
# doing due diligence. Flags phrases that pressure immediate action.
def check_urgency(text: str) -> bool:
    keywords = [
        r'apply\s+now',
        r'limited\s+seats?',
        r'urgent\s+hir(ing|e)',
        r'last\s+date\s+today',
        r'immediate\s+joiner',
        r'only\s+\d+\s+seats?',
        r'\bhurry\b',
        r'today\s+only',
    ]
    return bool(re.search('|'.join(keywords), text, re.IGNORECASE))


# ── Signal 5: Missing or vague company information ──────────
# Real companies mention their website, domain, or registered name.
# Vague terms like "top MNC" or "reputed firm" with no verifiable
# details are a strong indicator of a fake offer.
def check_missing_company(text: str) -> bool:
    text_lower = text.lower()

    has_website = bool(re.search(r'www\.', text_lower))
    has_domain  = bool(re.search(r'\.(com|in|org|net|co\.in)\b', text_lower))
    has_pvt_ltd = bool(re.search(r'pvt\.?\s*ltd|private\s+limited', text_lower))

    # If any real company indicator is present, not suspicious
    if has_website or has_domain or has_pvt_ltd:
        return False

    return True


# ============================================================
# Score Aggregator
# ============================================================

# Maps each detector to its weight and a human-readable reason string
SIGNALS = [
    (check_salary,          20, "Unusually high salary offer for a fresher"),
    (check_email_domain,    25, "Uses Gmail instead of company email"),
    (check_payment_request, 40, "Asks for registration/joining fee"),
    (check_urgency,         15, "Uses urgency/pressure tactics"),
    (check_missing_company, 20, "No company website or official domain found"),
]

def compute_risk(text: str) -> tuple[int, str, list[str]]:
    """Run all signal detectors and return (score, label, reasons)."""
    score = 0
    reasons = []

    for detector, weight, reason in SIGNALS:
        if detector(text):
            score += weight
            reasons.append(reason)

    score = min(score, 100)  # cap at 100

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
    Calls the Groq LLM to generate a plain-English explanation of why
    the job offer looks suspicious, along with one practical verification tip.

    Falls back to a static message if the API key is missing or the call fails.
    """
    api_key = os.getenv("GROQ_API_KEY")

    # Fallback: no API key configured or key is still the placeholder
    if not api_key or api_key == "your_key_here":
        reasons_text = ", ".join(reasons)
        return (
            f"This message was flagged as {label}. "
            f"Suspicious signals found: {reasons_text}. "
            "Always verify the company on LinkedIn or their official website "
            "before applying or sharing any personal details."
        )

    try:
        client = Groq(api_key=api_key)

        # Build a numbered list of reasons for the prompt
        numbered_reasons = "\n".join(
            f"{i + 1}. {r}" for i, r in enumerate(reasons)
        )

        chat_completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            max_tokens=300,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a helpful fraud detection assistant for job seekers in India. "
                        "Your job is to explain why a job offer looks suspicious in simple, "
                        "clear English. Be helpful and calm, not scary. Keep it under 4 sentences."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"This job message was analyzed and flagged as: {label}\n\n"
                        f"Suspicious signals found:\n{numbered_reasons}\n\n"
                        f"Original job message:\n{text}\n\n"
                        "Explain to the user why this looks suspicious and give one "
                        "practical tip to verify if this job is real."
                    ),
                },
            ],
        )

        return chat_completion.choices[0].message.content

    except Exception as e:
        # Any API error — return a safe fallback
        reasons_text = ", ".join(reasons)
        return (
            f"This message was flagged as {label}. "
            f"Suspicious signals found: {reasons_text}. "
            "Always verify the company on LinkedIn or their official website "
            "before applying or sharing any personal details."
        )


# ============================================================
# Endpoints
# ============================================================

# ── Health check ─────────────────────────────────────────────
@app.get("/health")
def health_check():
    """Simple liveness probe — returns ok when the server is up."""
    return {"status": "ok"}


# ── Main analysis endpoint ───────────────────────────────────
@app.post("/analyze", response_model=AnalyzeResponse)
def analyze_job_offer(payload: AnalyzeRequest):
    """
    Accepts a raw job offer message and returns a fraud risk assessment.

    1. Runs 5 rule-based signal detectors to compute score, label, reasons
    2. Calls Groq LLM to generate a plain-English explanation
    3. Returns all four fields in the response
    """
    score, label, reasons = compute_risk(payload.text)
    explanation = generate_explanation(payload.text, reasons, label)

    return AnalyzeResponse(
        score=score,
        label=label,
        reasons=reasons,
        explanation=explanation,
    )


# ── NLP prediction endpoint ──────────────────────────────────
@app.post("/predict", response_model=PredictResponse)
def predict_job(payload: PredictRequest):
    """
    NLP-based fake job classifier using TF-IDF + Logistic Regression.

    Runs the trained ML model on the job description and returns:
    - prediction  : Genuine / Suspicious / Fake
    - confidence  : model confidence as a percentage (0–100)
    - reason      : specific signal or template explanation

    Requires trained model files in backend/models/.
    Run `python -m training.train_model` first if models are missing.
    """
    try:
        result = predictor.predict(payload.job_description)
        return PredictResponse(
            prediction=result.prediction,
            confidence=result.confidence,
            reason=result.reason,
        )
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=503,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Prediction failed: {str(e)}",
        )


# ── Scam Risk Scoring endpoint ───────────────────────────────
@app.post("/risk-score", response_model=RiskScoreResponse)
def risk_score(payload: RiskScoreRequest):
    """
    Dynamic Scam Risk Scoring Engine.

    Evaluates the job text across five independent risk dimensions:
      1. suspicious_keywords  — payment requests, urgency, vague claims  (+20 max)
      2. fake_email_domain    — personal/free email domains               (+25)
      3. unrealistic_salary   — salary far above fresher market rate      (+15 max)
      4. phishing_url         — URL shorteners, IP links, typosquatting   (+30 max)
      5. missing_company_info — no verifiable employer details            (+20)

    Returns composite risk_score (0–100), risk_level (LOW/MEDIUM/HIGH),
    human-readable reasons, and a per-dimension breakdown.
    """
    result = score_text(payload.text)
    return RiskScoreResponse(
        risk_score=result.risk_score,
        risk_level=result.risk_level,
        reasons=result.reasons,
        breakdown=result.breakdown,
    )


# ── Single URL phishing check ────────────────────────────────
@app.post("/check-url", response_model=CheckUrlResponse)
def check_url(payload: CheckUrlRequest):
    """
    Analyse a single URL for phishing and malicious indicators.

    Detection layers:
      - HTTP (no TLS)
      - IP-address-based host
      - URL shortener services
      - Excessive hyphens in domain
      - Suspicious / high-abuse TLDs (.tk .ml .xyz etc.)
      - Deceptive subdomains (brand impersonation)
      - Typosquatting / lookalike domains
      - Excessive URL length
      - Suspicious path keywords (login, verify, otp, joining-fee…)

    Returns risk_score (0–100), risk_level (LOW/MEDIUM/HIGH),
    is_phishing flag, reasons, and per-check breakdown.
    """
    result = analyze_url(payload.url)
    return CheckUrlResponse(
        url=result.url,
        is_phishing=result.is_phishing,
        risk_level=result.risk_level,
        risk_score=result.risk_score,
        reasons=result.reasons,
        breakdown=result.breakdown,
    )


# ── Bulk URL scan from free text ─────────────────────────────
@app.post("/scan-urls", response_model=ScanTextUrlsResponse)
def scan_text_urls(payload: ScanTextUrlsRequest):
    """
    Extract every URL from a job description / message and analyse
    each one for phishing indicators in a single call.

    Useful for scanning a full job post without manually extracting URLs.
    Returns a summary count plus per-URL results.
    """
    results = analyze_text_for_urls(payload.text)
    summaries = [
        UrlScanSummary(
            url=r.url,
            is_phishing=r.is_phishing,
            risk_level=r.risk_level,
            risk_score=r.risk_score,
            reasons=r.reasons,
        )
        for r in results
    ]
    return ScanTextUrlsResponse(
        urls_found=len(results),
        phishing_count=sum(1 for r in results if r.is_phishing),
        results=summaries,
    )
