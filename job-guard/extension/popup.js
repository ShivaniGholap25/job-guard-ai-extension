// ============================================================
// Job Guard — Popup Script
// Sends job text to the FastAPI backend and renders the result
// ============================================================

const API_URL = "http://localhost:8000/analyze";

// ── DOM references ───────────────────────────────────────────
const analyzeBtn     = document.getElementById("analyzeBtn");
const jobText        = document.getElementById("jobText");
const loading        = document.getElementById("loading");
const result         = document.getElementById("result");
const badge          = document.getElementById("badge");
const scoreEl        = document.getElementById("score");
const reasonsEl      = document.getElementById("reasons");
const explanationBox = document.getElementById("explanation-box");
const explanationText = document.getElementById("explanation-text");

// ── Helper: map label string to CSS class ───────────────────
function labelToClass(label) {
  const l = label.toLowerCase();
  if (l.includes("high"))   return "high";
  if (l.includes("medium")) return "medium";
  return "low";
}

// ── Helper: show loading state ───────────────────────────────
function showLoading() {
  loading.classList.remove("hidden");
  result.classList.add("hidden");
  // Reset AI explanation box so stale content isn't shown
  explanationBox.style.display = "none";
  explanationText.textContent  = "";
  analyzeBtn.disabled = true;
}

// ── Helper: hide loading state ───────────────────────────────
function hideLoading() {
  loading.classList.add("hidden");
  analyzeBtn.disabled = false;
}

// ── Helper: render the result card ──────────────────────────
function renderResult(data) {
  // Badge — label text + color class
  badge.textContent = data.label;
  badge.className   = "badge " + labelToClass(data.label);

  // Score line
  scoreEl.textContent = `Risk Score: ${data.score} / 100`;

  // Reasons — build <li> for each reason
  reasonsEl.innerHTML = "";
  data.reasons.forEach((reason) => {
    const li = document.createElement("li");
    li.textContent = reason;
    reasonsEl.appendChild(li);
  });

  // AI explanation — show if present in response
  if (data.explanation) {
    explanationText.textContent  = data.explanation;
    explanationBox.style.display = "block";
  }

  // Show the card
  result.classList.remove("hidden");
}

// ── Helper: render an error message inside the result card ──
function renderError(message) {
  badge.textContent = "Error";
  badge.className   = "badge high";
  scoreEl.textContent = "";
  reasonsEl.innerHTML = `<li>${message}</li>`;
  result.classList.remove("hidden");
}

// ── Main click handler ───────────────────────────────────────
analyzeBtn.addEventListener("click", async () => {
  const text = jobText.value.trim();

  // Guard: empty input
  if (!text) {
    alert("Please paste a job message first");
    return;
  }

  showLoading();

  try {
    const response = await fetch(API_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });

    if (!response.ok) {
      throw new Error(`Server returned ${response.status}`);
    }

    const data = await response.json();
    renderResult(data);

  } catch (err) {
    // Network error or backend not running
    renderError("Could not connect to server. Make sure backend is running.");
  } finally {
    // Always hide loading, re-enable button
    hideLoading();
  }
});
