"""
preprocessing.py
----------------
NLP preprocessing pipeline for Job Guard.

Steps applied in order:
  1. Lowercase conversion
  2. URL / email removal
  3. Punctuation removal
  4. Digit removal
  5. Tokenization
  6. Stopword removal
  7. Lemmatization (falls back to Porter stemming if WordNet unavailable)
"""

import re
import string

import nltk
from nltk.corpus import stopwords
from nltk.stem import PorterStemmer, WordNetLemmatizer
from nltk.tokenize import word_tokenize

# ── Download required NLTK data (safe to call multiple times) ──
for _pkg in ("punkt", "punkt_tab", "stopwords", "wordnet", "omw-1.4"):
    nltk.download(_pkg, quiet=True)

# ── Module-level singletons (instantiate once, reuse everywhere) ──
_STOP_WORDS  = set(stopwords.words("english"))
_LEMMATIZER  = WordNetLemmatizer()
_STEMMER     = PorterStemmer()

# Regex patterns compiled once for performance
_URL_RE      = re.compile(r"https?://\S+|www\.\S+")
_EMAIL_RE    = re.compile(r"\S+@\S+")
_DIGIT_RE    = re.compile(r"\d+")
_WHITESPACE  = re.compile(r"\s+")


def remove_urls(text: str) -> str:
    """Strip http/https URLs and bare www. links."""
    return _URL_RE.sub(" ", text)


def remove_emails(text: str) -> str:
    """Strip email addresses."""
    return _EMAIL_RE.sub(" ", text)


def remove_punctuation(text: str) -> str:
    """Remove all punctuation characters."""
    return text.translate(str.maketrans("", "", string.punctuation))


def remove_digits(text: str) -> str:
    """Remove standalone digit sequences."""
    return _DIGIT_RE.sub(" ", text)


def tokenize(text: str) -> list[str]:
    """Split text into word tokens using NLTK's word_tokenize."""
    return word_tokenize(text)


def remove_stopwords(tokens: list[str]) -> list[str]:
    """Drop common English stopwords from token list."""
    return [t for t in tokens if t not in _STOP_WORDS]


def lemmatize(tokens: list[str]) -> list[str]:
    """
    Lemmatize each token (noun form).
    Falls back to Porter stemming if WordNet lookup fails.
    """
    result = []
    for token in tokens:
        try:
            result.append(_LEMMATIZER.lemmatize(token))
        except Exception:
            result.append(_STEMMER.stem(token))
    return result


def preprocess(text: str) -> str:
    """
    Full preprocessing pipeline.

    Parameters
    ----------
    text : str
        Raw job offer / description text.

    Returns
    -------
    str
        Cleaned, lemmatized string ready for TF-IDF vectorization.
    """
    if not isinstance(text, str) or not text.strip():
        return ""

    text = text.lower()
    text = remove_urls(text)
    text = remove_emails(text)
    text = remove_punctuation(text)
    text = remove_digits(text)
    text = _WHITESPACE.sub(" ", text).strip()

    tokens = tokenize(text)
    tokens = remove_stopwords(tokens)
    tokens = lemmatize(tokens)

    # Drop very short tokens (single chars, noise)
    tokens = [t for t in tokens if len(t) > 1]

    return " ".join(tokens)
