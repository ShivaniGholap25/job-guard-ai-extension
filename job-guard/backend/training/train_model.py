"""
train_model.py
--------------
Trains a TF-IDF + Logistic Regression classifier for fake job detection.

Labels:
  0 → Genuine
  1 → Suspicious
  2 → Fake

Outputs saved to backend/models/:
  - tfidf_vectorizer.pkl
  - job_classifier.pkl
  - label_encoder.pkl

Run from the backend/ directory:
  python -m training.train_model
"""

import os
import pickle
import sys

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.feature_extraction.text import TfidfVectorizer

# Allow running as a script from backend/
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from preprocessing.preprocessing import preprocess

# ── Paths ────────────────────────────────────────────────────
MODELS_DIR      = os.path.join(os.path.dirname(__file__), "..", "models")
VECTORIZER_PATH = os.path.join(MODELS_DIR, "tfidf_vectorizer.pkl")
CLASSIFIER_PATH = os.path.join(MODELS_DIR, "job_classifier.pkl")
ENCODER_PATH    = os.path.join(MODELS_DIR, "label_encoder.pkl")

os.makedirs(MODELS_DIR, exist_ok=True)


# ── Training Dataset ─────────────────────────────────────────
# Curated examples covering real-world patterns seen in Indian job scams.
# Each tuple: (text, label)
RAW_DATA: list[tuple[str, str]] = [

    # ── GENUINE ──────────────────────────────────────────────
    ("Infosys is hiring software engineers with 2 years experience. CTC 6 LPA. Apply at careers.infosys.com", "Genuine"),
    ("TCS BPS hiring freshers for data entry roles. Salary 2.5 LPA. Walk-in at TCS Pune office on Monday.", "Genuine"),
    ("Wipro Technologies is looking for Java developers. 3-5 years experience required. Official apply link: wipro.com/careers", "Genuine"),
    ("Amazon India hiring for customer support. Fixed shift, 18000 per month. Interview at Amazon Hyderabad office.", "Genuine"),
    ("Accenture is recruiting for business analyst role. MBA preferred. Salary negotiable. Apply via accenture.com", "Genuine"),
    ("HCL Technologies walk-in drive for freshers. BE/BTech required. Salary 3.2 LPA. Venue: HCL Noida campus.", "Genuine"),
    ("Cognizant hiring for QA engineer. 2 years experience in Selenium. CTC up to 5 LPA. Apply at cognizant.com/careers", "Genuine"),
    ("Deloitte India is hiring for audit associate. CA freshers preferred. Competitive salary. Apply at deloitte.com", "Genuine"),
    ("IBM India hiring data scientists. Python and ML experience required. Salary 8-12 LPA. Apply at ibm.com/jobs", "Genuine"),
    ("Flipkart hiring logistics executives. 12th pass eligible. Salary 15000 per month. Interview at Flipkart warehouse.", "Genuine"),
    ("Google India hiring software engineers. Competitive salary and benefits. Apply at careers.google.com", "Genuine"),
    ("Microsoft hiring for cloud solutions architect. Azure certification preferred. Apply at careers.microsoft.com", "Genuine"),
    ("Zomato hiring delivery partners. Flexible hours. Earn up to 25000 per month. Register at zomato.com/partner", "Genuine"),
    ("HDFC Bank hiring relationship managers. Graduate required. Salary 3-4 LPA plus incentives. Apply at hdfcbank.com", "Genuine"),
    ("Byju's hiring academic counselors. Good communication required. Salary 4 LPA plus commission. Apply at byjus.com", "Genuine"),
    ("Swiggy hiring delivery executives. Own vehicle required. Earn 20000-30000 per month. Register at swiggy.com", "Genuine"),
    ("Tech Mahindra hiring for network engineers. CCNA certification preferred. Salary 4.5 LPA. Apply at techmahindra.com", "Genuine"),
    ("Reliance Jio hiring for retail store executives. Graduate required. Salary 2.5 LPA. Apply at jio.com/careers", "Genuine"),
    ("Capgemini hiring freshers for software developer role. BE/BTech 2024 batch. CTC 3.8 LPA. Apply at capgemini.com", "Genuine"),
    ("Tata Motors hiring production engineers. Diploma or BE required. Salary 3 LPA. Apply at tatamotors.com/careers", "Genuine"),

    # ── SUSPICIOUS ───────────────────────────────────────────
    ("Work from home job available. Earn 30000 per month. No experience needed. Contact on WhatsApp only.", "Suspicious"),
    ("Part time job for students. Earn 500 per day from home. Simple data entry work. Call now for details.", "Suspicious"),
    ("Urgent requirement for telecallers. Salary 25000 per month. No interview required. Join immediately.", "Suspicious"),
    ("Online job opportunity. Earn money by liking YouTube videos. Payment daily. Contact recruiter on Telegram.", "Suspicious"),
    ("Hiring for top MNC company. Salary 50000 per month for freshers. No experience required. Apply today.", "Suspicious"),
    ("Work from home data entry jobs. Earn 15000 to 40000 per month. Flexible hours. No qualification required.", "Suspicious"),
    ("Immediate joiners required for reputed firm. Salary 35000 per month. Contact hr12345@gmail.com", "Suspicious"),
    ("Good company hiring for multiple positions. High salary. Limited seats. Apply before tomorrow.", "Suspicious"),
    ("Earn money online by completing simple tasks. No investment. Daily payment. WhatsApp 9999999999", "Suspicious"),
    ("Part time work from home. Earn 1000 per hour. No experience needed. Hurry limited slots available.", "Suspicious"),
    ("Multinational company hiring freshers. Salary 8 LPA. No interview. Direct joining. Contact on WhatsApp.", "Suspicious"),
    ("Online reselling job. Earn 20000 per month from home. No target. Contact recruiter@yahoo.com", "Suspicious"),
    ("Hiring for leading company. Salary 45000 per month. Immediate requirement. Only 10 seats left.", "Suspicious"),
    ("Work from home opportunity for housewives and students. Earn 500 to 2000 daily. No experience required.", "Suspicious"),
    ("Urgent hiring for well known company. Salary 60000 per month fresher. Apply now last date today.", "Suspicious"),

    # ── FAKE ─────────────────────────────────────────────────
    ("Congratulations you are selected. Pay registration fee of 500 rupees via UPI to confirm your joining.", "Fake"),
    ("Job offer from abroad. Salary 2 lakh per month. Send your passport copy and pay 2000 processing fee.", "Fake"),
    ("You have been selected for a government job. Pay security deposit of 5000 to get your appointment letter.", "Fake"),
    ("Work from home packing job. Earn 50000 per month. Pay 1500 advance to get the kit delivered to your home.", "Fake"),
    ("Lottery job offer. You won a job in Canada. Pay 10000 visa processing fee to claim your offer letter.", "Fake"),
    ("Urgent hiring. Pay 999 registration fee via UPI to unlock your interview slot. Refundable after joining.", "Fake"),
    ("Selected for BPO job. Salary 40000 per month. Pay training fee of 2000 before joining. Contact gmail only.", "Fake"),
    ("Government scheme job. Pay 3000 deposit to get your ID card and joining letter. Limited seats hurry.", "Fake"),
    ("Amazon work from home job. Earn 80000 per month. Pay 1000 registration fee to start. Apply now today only.", "Fake"),
    ("You are shortlisted. Pay 1500 security amount via UPI to confirm your seat. Refundable after 3 months.", "Fake"),
    ("Earn 1 lakh per month from home. No work required. Pay 5000 joining fee to get started immediately.", "Fake"),
    ("Job in Dubai. Salary 3 lakh per month. Pay 15000 visa and processing fee. Send Aadhaar and bank details.", "Fake"),
    ("Data entry job. Earn 2000 per day. Pay 800 advance payment to receive work material. WhatsApp only.", "Fake"),
    ("Selected for MNC job. Pay 2500 training fee via UPI before your joining date. Offer letter will be sent.", "Fake"),
    ("Congratulations your resume is shortlisted. Pay 1200 document verification fee to proceed further.", "Fake"),
    ("Online job. Earn 500 per hour. Pay 999 activation fee to start working. Daily payment guaranteed.", "Fake"),
    ("Government job vacancy. Pay 4000 application fee to apply. Last date today. Limited seats available.", "Fake"),
    ("Work from home job. Earn 60000 per month. Pay 2000 refundable deposit to get your login credentials.", "Fake"),
    ("You are selected for abroad job. Salary 5 lakh per month. Pay 20000 processing fee to get visa stamped.", "Fake"),
    ("Earn money daily. Pay 500 registration fee via UPI. Get 2000 per day working from home. Hurry apply now.", "Fake"),
]


def build_dataset() -> tuple[list[str], list[str]]:
    """Return (texts, labels) lists from RAW_DATA."""
    texts  = [item[0] for item in RAW_DATA]
    labels = [item[1] for item in RAW_DATA]
    return texts, labels


def train() -> None:
    print("=" * 55)
    print("  Job Guard — NLP Model Training")
    print("=" * 55)

    # ── 1. Load data ─────────────────────────────────────────
    texts, labels = build_dataset()
    print(f"\n[1/5] Dataset loaded: {len(texts)} samples")
    for lbl in ("Genuine", "Suspicious", "Fake"):
        print(f"      {lbl}: {labels.count(lbl)}")

    # ── 2. Preprocess ────────────────────────────────────────
    print("\n[2/5] Preprocessing text...")
    cleaned = [preprocess(t) for t in texts]

    # ── 3. Encode labels ─────────────────────────────────────
    encoder = LabelEncoder()
    y = encoder.fit_transform(labels)
    print(f"\n[3/5] Label classes: {list(encoder.classes_)}")

    # ── 4. TF-IDF vectorization ──────────────────────────────
    vectorizer = TfidfVectorizer(
        max_features=3000,
        ngram_range=(1, 2),   # unigrams + bigrams
        sublinear_tf=True,    # apply log normalization
        min_df=1,
    )
    X = vectorizer.fit_transform(cleaned)
    print(f"\n[4/5] TF-IDF matrix: {X.shape[0]} samples × {X.shape[1]} features")

    # ── 5. Train / evaluate ──────────────────────────────────
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    model = LogisticRegression(
        max_iter=1000,
        C=1.0,
        solver="lbfgs",
        random_state=42,
    )
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    print("\n[5/5] Evaluation on test split:")
    print(classification_report(y_test, y_pred, target_names=encoder.classes_))

    # ── 6. Save artifacts ────────────────────────────────────
    with open(VECTORIZER_PATH, "wb") as f:
        pickle.dump(vectorizer, f)

    with open(CLASSIFIER_PATH, "wb") as f:
        pickle.dump(model, f)

    with open(ENCODER_PATH, "wb") as f:
        pickle.dump(encoder, f)

    print(f"Models saved to: {os.path.abspath(MODELS_DIR)}")
    print("  ✓ tfidf_vectorizer.pkl")
    print("  ✓ job_classifier.pkl")
    print("  ✓ label_encoder.pkl")
    print("\nTraining complete.")


if __name__ == "__main__":
    train()
