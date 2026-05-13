# 🛡️ Job Guard — Fake Job Offer Detector

A Chrome Extension + FastAPI backend that analyzes job offer messages and detects scams using rule-based signals and Groq AI (Llama 3.3-70b).

---

## 📸 How It Works

1. Paste a suspicious job message into the extension popup
2. Click **Analyze**
3. Get an instant risk score, flagged signals, and an AI-generated explanation

---

## 🚨 What It Detects

| Signal | Weight |
|---|---|
| Unrealistically high salary for freshers | +20 |
| Recruiter using Gmail / Yahoo / Hotmail | +25 |
| Asks for registration / joining fee | +40 |
| Urgency pressure tactics | +15 |
| No company website or official domain | +20 |

**Risk Labels:**
- 🟢 0–30 → Low Risk
- 🟡 31–60 → Medium Risk
- 🔴 61–100 → High Risk

---

## 🗂️ Project Structure

```
job-guard/
├── backend/
│   ├── main.py          # FastAPI app with detection logic + Groq AI
│   ├── .env             # Your API key (never committed)
│   └── .env.example     # Safe template to share
├── extension/
│   ├── manifest.json    # Chrome Extension Manifest V3
│   ├── popup.html       # Extension UI
│   ├── popup.css        # Styles
│   └── popup.js         # Fetch logic + result rendering
└── requirements.txt
```

---

## ⚙️ Setup & Run

### 1. Clone the repo
```bash
git clone https://github.com/ShivaniGholap25/job-guard-ai-extension.git
cd job-guard-ai-extension
```

### 2. Install Python dependencies
```bash
pip install -r job-guard/requirements.txt
```

### 3. Add your Groq API key
Get a free key at [console.groq.com](https://console.groq.com)

```bash
# Create job-guard/backend/.env
GROQ_API_KEY=your_key_here
```

### 4. Start the backend
```bash
cd job-guard/backend
uvicorn main:app --reload --port 8000
```

Backend runs at → `http://localhost:8000`
Interactive docs → `http://localhost:8000/docs`

### 5. Load the Chrome Extension
1. Open `chrome://extensions`
2. Enable **Developer mode** (top right)
3. Click **Load unpacked**
4. Select the `job-guard/extension/` folder
5. Pin the 🛡️ Job Guard icon in your toolbar

---

## 🧪 Test Cases

**Fake job (High Risk):**
```
Urgent hiring! Work from home paying 80k/month. Send registration fee via UPI.
Contact jobs@gmail.com. Apply now, only 5 seats left!
```

**Borderline (Medium Risk):**
```
We are hiring freshers for a remote role. Salary: 5 LPA.
Immediate joiners preferred. Contact hr@gmail.com
```

**Legitimate job (Low Risk):**
```
Infosys Pvt Ltd is hiring software engineers. CTC: 3.5 LPA.
Apply at www.infosys.com/careers. Contact: hr@infosys.com
```

---

## 🛠️ Tech Stack

- **Backend:** Python, FastAPI, Uvicorn
- **AI:** Groq API — Llama 3.3-70b-versatile
- **Frontend:** Chrome Extension (Manifest V3), Vanilla JS
- **Pattern Matching:** Python `re` module (no ML libraries)

---

## 📄 License

MIT License — free to use, modify, and distribute.
