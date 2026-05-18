"""
dashboard/app.py
----------------
Job Guard — Analytics Dashboard
Built with Streamlit + Plotly + Pandas

Run from backend/ directory:
    streamlit run dashboard/app.py
"""

import random
from datetime import datetime, timedelta

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ============================================================
# Page config — must be first Streamlit call
# ============================================================
st.set_page_config(
    page_title="Job Guard Dashboard",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# Global CSS — dark theme + card styles
# ============================================================
st.markdown("""
<style>
/* ── Base ─────────────────────────────────────────────────── */
html, body, [data-testid="stAppViewContainer"] {
    background-color: #0f1117;
    color: #e0e0e0;
    font-family: 'Segoe UI', system-ui, sans-serif;
}
[data-testid="stSidebar"] {
    background-color: #1a1d27;
    border-right: 1px solid #2a2d3e;
}
[data-testid="stSidebar"] * { color: #c9d1d9 !important; }

/* ── Metric cards ─────────────────────────────────────────── */
.metric-card {
    background: linear-gradient(135deg, #1e2130, #252840);
    border: 1px solid #2e3250;
    border-radius: 12px;
    padding: 20px 24px;
    text-align: center;
    box-shadow: 0 4px 20px rgba(0,0,0,0.4);
    transition: transform 0.2s;
}
.metric-card:hover { transform: translateY(-2px); }
.metric-value {
    font-size: 2.4rem;
    font-weight: 700;
    margin: 6px 0 2px;
    line-height: 1;
}
.metric-label {
    font-size: 0.78rem;
    color: #8b949e;
    text-transform: uppercase;
    letter-spacing: 0.08em;
}
.metric-delta {
    font-size: 0.75rem;
    margin-top: 6px;
}
.delta-up   { color: #3fb950; }
.delta-down { color: #f85149; }

/* ── Section headers ──────────────────────────────────────── */
.section-header {
    font-size: 1.05rem;
    font-weight: 600;
    color: #c9d1d9;
    border-left: 3px solid #4f6ef7;
    padding-left: 10px;
    margin: 8px 0 16px;
}

/* ── Alert badges ─────────────────────────────────────────── */
.badge-high   { background:#3d1a1a; color:#f85149; border:1px solid #f85149;
                border-radius:6px; padding:2px 10px; font-size:0.72rem; font-weight:600; }
.badge-medium { background:#2d2010; color:#e3b341; border:1px solid #e3b341;
                border-radius:6px; padding:2px 10px; font-size:0.72rem; font-weight:600; }
.badge-low    { background:#0d2818; color:#3fb950; border:1px solid #3fb950;
                border-radius:6px; padding:2px 10px; font-size:0.72rem; font-weight:600; }

/* ── Table ────────────────────────────────────────────────── */
[data-testid="stDataFrame"] { border-radius: 10px; overflow: hidden; }
thead tr th { background-color: #1e2130 !important; color: #8b949e !important; }

/* ── Plotly chart backgrounds ─────────────────────────────── */
.js-plotly-plot .plotly { border-radius: 12px; }

/* ── Divider ──────────────────────────────────────────────── */
hr { border-color: #2a2d3e; }
</style>
""", unsafe_allow_html=True)

# ============================================================
# Demo Data Generator
# ============================================================

@st.cache_data(ttl=300)
def generate_scan_history(n: int = 200) -> pd.DataFrame:
    """Generate realistic scan history for the past 30 days."""
    random.seed(42)
    base = datetime.now() - timedelta(days=30)
    records = []
    job_snippets = [
        "Urgent hiring! Pay registration fee via UPI. Earn 80k/month.",
        "Infosys hiring software engineers. CTC 6 LPA. Apply at careers.infosys.com",
        "Work from home. Earn 50k/month. No experience needed. WhatsApp only.",
        "TCS BPS hiring freshers. Salary 2.5 LPA. Walk-in at TCS Pune office.",
        "Pay 999 joining fee to confirm your seat. Refundable after 3 months.",
        "Amazon India hiring customer support. Fixed shift, 18k/month.",
        "Earn 1 lakh/month from home. No work required. Pay 5000 joining fee.",
        "Wipro Technologies hiring Java developers. Apply at wipro.com/careers",
        "Lottery job offer. Won a job in Canada. Pay 10000 visa processing fee.",
        "Google India hiring software engineers. Apply at careers.google.com",
        "Multinational company hiring freshers. Salary 8 LPA. No interview.",
        "HCL Technologies walk-in drive. Salary 3.2 LPA. HCL Noida campus.",
        "Send your Aadhaar and bank details to claim your offer letter.",
        "Cognizant hiring QA engineer. CTC up to 5 LPA. cognizant.com/careers",
        "Earn 500/hour. Pay 999 activation fee to start. Daily payment guaranteed.",
    ]
    predictions = ["Fake", "Genuine", "Suspicious"]
    risk_levels = ["HIGH", "MEDIUM", "LOW"]

    for i in range(n):
        ts = base + timedelta(
            days=random.randint(0, 29),
            hours=random.randint(0, 23),
            minutes=random.randint(0, 59),
        )
        pred_weights = [0.38, 0.42, 0.20]
        prediction = random.choices(predictions, weights=pred_weights)[0]

        if prediction == "Fake":
            risk = random.choices(["HIGH", "MEDIUM"], weights=[0.75, 0.25])[0]
            score = random.randint(62, 100)
            confidence = round(random.uniform(60, 95), 1)
        elif prediction == "Suspicious":
            risk = random.choices(["MEDIUM", "HIGH"], weights=[0.70, 0.30])[0]
            score = random.randint(31, 65)
            confidence = round(random.uniform(45, 75), 1)
        else:
            risk = "LOW"
            score = random.randint(0, 30)
            confidence = round(random.uniform(55, 92), 1)

        phishing = random.random() < (0.55 if prediction == "Fake" else 0.10)

        records.append({
            "timestamp":   ts,
            "job_snippet": random.choice(job_snippets),
            "prediction":  prediction,
            "confidence":  confidence,
            "risk_score":  score,
            "risk_level":  risk,
            "phishing":    phishing,
        })

    df = pd.DataFrame(records).sort_values("timestamp", ascending=False).reset_index(drop=True)
    df["date"] = df["timestamp"].dt.date
    return df


@st.cache_data(ttl=300)
def generate_url_scan_history(n: int = 80) -> pd.DataFrame:
    """Generate realistic URL scan history."""
    random.seed(99)
    base = datetime.now() - timedelta(days=30)
    urls = [
        "https://bit.ly/fake-job-2024",
        "https://careers.infosys.com/jobs",
        "http://192.168.1.100/apply-now",
        "https://secure-amazon-jobs-apply.tk/login",
        "https://linkedin.com/jobs/view/12345",
        "https://amazon.free-jobs-india.xyz/verify",
        "https://naukri.com/job-listings",
        "https://tcs-job-apply-now.ml/register",
        "https://careers.wipro.com/apply",
        "http://job-offer-india.top/joining-fee",
    ]
    records = []
    for _ in range(n):
        ts = base + timedelta(days=random.randint(0, 29), hours=random.randint(0, 23))
        url = random.choice(urls)
        is_phishing = any(x in url for x in ["bit.ly", "192.168", "tk/", "xyz/", "ml/", "top/"])
        risk = "HIGH" if is_phishing and random.random() > 0.3 else (
            "MEDIUM" if is_phishing else "LOW"
        )
        records.append({
            "timestamp":   ts,
            "url":         url,
            "is_phishing": is_phishing,
            "risk_level":  risk,
            "risk_score":  random.randint(65, 100) if is_phishing else random.randint(0, 30),
        })
    return pd.DataFrame(records).sort_values("timestamp", ascending=False).reset_index(drop=True)

# ============================================================
# Reusable Chart Builders
# ============================================================

DARK_BG    = "#0f1117"
CARD_BG    = "#1e2130"
GRID_COLOR = "#2a2d3e"
TEXT_COLOR = "#c9d1d9"
PALETTE    = ["#4f6ef7", "#f85149", "#e3b341", "#3fb950", "#a371f7", "#58a6ff"]

PRED_COLORS = {"Genuine": "#3fb950", "Suspicious": "#e3b341", "Fake": "#f85149"}
RISK_COLORS = {"LOW": "#3fb950", "MEDIUM": "#e3b341", "HIGH": "#f85149"}


def _base_layout(title: str = "", height: int = 360) -> dict:
    return dict(
        title=dict(text=title, font=dict(color=TEXT_COLOR, size=14), x=0.01),
        paper_bgcolor=CARD_BG,
        plot_bgcolor=CARD_BG,
        font=dict(color=TEXT_COLOR, family="Segoe UI, system-ui, sans-serif"),
        height=height,
        margin=dict(l=16, r=16, t=40, b=16),
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            bordercolor=GRID_COLOR,
            font=dict(color=TEXT_COLOR),
        ),
    )


def chart_prediction_pie(df: pd.DataFrame) -> go.Figure:
    counts = df["prediction"].value_counts().reset_index()
    counts.columns = ["prediction", "count"]
    colors = [PRED_COLORS.get(p, "#8b949e") for p in counts["prediction"]]
    fig = go.Figure(go.Pie(
        labels=counts["prediction"],
        values=counts["count"],
        hole=0.55,
        marker=dict(colors=colors, line=dict(color=CARD_BG, width=2)),
        textinfo="label+percent",
        textfont=dict(color=TEXT_COLOR, size=12),
        hovertemplate="<b>%{label}</b><br>Count: %{value}<br>Share: %{percent}<extra></extra>",
    ))
    fig.update_layout(**_base_layout("Prediction Distribution"))
    fig.add_annotation(
        text=f"<b>{len(df)}</b><br><span style='font-size:11px'>Total</span>",
        x=0.5, y=0.5, showarrow=False,
        font=dict(color=TEXT_COLOR, size=16),
    )
    return fig


def chart_risk_bar(df: pd.DataFrame) -> go.Figure:
    counts = df["risk_level"].value_counts().reindex(["LOW", "MEDIUM", "HIGH"], fill_value=0)
    colors = [RISK_COLORS[r] for r in counts.index]
    fig = go.Figure(go.Bar(
        x=counts.index,
        y=counts.values,
        marker=dict(color=colors, line=dict(color=CARD_BG, width=1)),
        text=counts.values,
        textposition="outside",
        textfont=dict(color=TEXT_COLOR),
        hovertemplate="<b>%{x}</b><br>Count: %{y}<extra></extra>",
    ))
    fig.update_layout(
        **_base_layout("Risk Level Distribution"),
        xaxis=dict(showgrid=False, color=TEXT_COLOR),
        yaxis=dict(gridcolor=GRID_COLOR, color=TEXT_COLOR, showgrid=True),
        bargap=0.35,
    )
    return fig


def chart_daily_trend(df: pd.DataFrame) -> go.Figure:
    daily = (
        df.groupby(["date", "prediction"])
        .size()
        .reset_index(name="count")
    )
    fig = go.Figure()
    for pred, color in PRED_COLORS.items():
        subset = daily[daily["prediction"] == pred]
        fig.add_trace(go.Scatter(
            x=subset["date"],
            y=subset["count"],
            name=pred,
            mode="lines+markers",
            line=dict(color=color, width=2),
            marker=dict(size=5, color=color),
            fill="tozeroy",
            fillcolor=color.replace(")", ", 0.08)").replace("rgb", "rgba") if "rgb" in color
                       else color + "14",
            hovertemplate=f"<b>{pred}</b><br>Date: %{{x}}<br>Count: %{{y}}<extra></extra>",
        ))
    fig.update_layout(
        **_base_layout("Daily Scan Trend (30 days)", height=300),
        xaxis=dict(gridcolor=GRID_COLOR, color=TEXT_COLOR, showgrid=False),
        yaxis=dict(gridcolor=GRID_COLOR, color=TEXT_COLOR),
        hovermode="x unified",
    )
    return fig


def chart_confidence_histogram(df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    for pred, color in PRED_COLORS.items():
        subset = df[df["prediction"] == pred]["confidence"]
        fig.add_trace(go.Histogram(
            x=subset,
            name=pred,
            marker_color=color,
            opacity=0.75,
            nbinsx=20,
            hovertemplate=f"<b>{pred}</b><br>Confidence: %{{x:.0f}}%<br>Count: %{{y}}<extra></extra>",
        ))
    fig.update_layout(
        **_base_layout("Prediction Confidence Distribution"),
        barmode="overlay",
        xaxis=dict(title="Confidence (%)", gridcolor=GRID_COLOR, color=TEXT_COLOR),
        yaxis=dict(title="Count", gridcolor=GRID_COLOR, color=TEXT_COLOR),
    )
    return fig


def chart_risk_score_box(df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    for pred, color in PRED_COLORS.items():
        subset = df[df["prediction"] == pred]["risk_score"]
        fig.add_trace(go.Box(
            y=subset,
            name=pred,
            marker_color=color,
            line_color=color,
            fillcolor=color + "33",
            boxmean=True,
            hovertemplate=f"<b>{pred}</b><br>Score: %{{y}}<extra></extra>",
        ))
    fig.update_layout(
        **_base_layout("Risk Score Distribution by Prediction"),
        yaxis=dict(title="Risk Score", gridcolor=GRID_COLOR, color=TEXT_COLOR),
        xaxis=dict(color=TEXT_COLOR),
    )
    return fig


def chart_phishing_gauge(phishing_rate: float) -> go.Figure:
    color = "#f85149" if phishing_rate > 40 else "#e3b341" if phishing_rate > 20 else "#3fb950"
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=phishing_rate,
        number=dict(suffix="%", font=dict(color=TEXT_COLOR, size=28)),
        delta=dict(reference=25, increasing=dict(color="#f85149"), decreasing=dict(color="#3fb950")),
        gauge=dict(
            axis=dict(range=[0, 100], tickcolor=TEXT_COLOR, tickfont=dict(color=TEXT_COLOR)),
            bar=dict(color=color),
            bgcolor=CARD_BG,
            bordercolor=GRID_COLOR,
            steps=[
                dict(range=[0, 30],  color="#0d2818"),
                dict(range=[30, 60], color="#2d2010"),
                dict(range=[60, 100], color="#3d1a1a"),
            ],
            threshold=dict(line=dict(color="#ffffff", width=2), thickness=0.75, value=phishing_rate),
        ),
        title=dict(text="Phishing URL Rate", font=dict(color=TEXT_COLOR, size=13)),
    ))
    fig.update_layout(paper_bgcolor=CARD_BG, height=260, margin=dict(l=20, r=20, t=40, b=10))
    return fig


def chart_weekly_heatmap(df: pd.DataFrame) -> go.Figure:
    df2 = df.copy()
    df2["hour"]    = df2["timestamp"].dt.hour
    df2["weekday"] = df2["timestamp"].dt.day_name()
    order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    pivot = df2.groupby(["weekday", "hour"]).size().unstack(fill_value=0).reindex(order)
    fig = go.Figure(go.Heatmap(
        z=pivot.values,
        x=[f"{h:02d}:00" for h in pivot.columns],
        y=pivot.index,
        colorscale=[[0, CARD_BG], [0.5, "#4f6ef7"], [1, "#f85149"]],
        hovertemplate="<b>%{y} %{x}</b><br>Scans: %{z}<extra></extra>",
        showscale=True,
        colorbar=dict(tickfont=dict(color=TEXT_COLOR), outlinecolor=GRID_COLOR),
    ))
    fig.update_layout(
        **_base_layout("Scan Activity Heatmap (Hour × Day)", height=280),
        xaxis=dict(color=TEXT_COLOR, tickangle=-45),
        yaxis=dict(color=TEXT_COLOR),
    )
    return fig

# ============================================================
# Reusable UI Components
# ============================================================

def metric_card(label: str, value: str, delta: str = "", delta_up: bool = True, color: str = "#4f6ef7") -> str:
    delta_class = "delta-up" if delta_up else "delta-down"
    delta_arrow = "▲" if delta_up else "▼"
    delta_html  = f'<div class="metric-delta {delta_class}">{delta_arrow} {delta}</div>' if delta else ""
    return f"""
    <div class="metric-card">
        <div class="metric-label">{label}</div>
        <div class="metric-value" style="color:{color}">{value}</div>
        {delta_html}
    </div>"""


def section_header(title: str) -> None:
    st.markdown(f'<div class="section-header">{title}</div>', unsafe_allow_html=True)


def risk_badge(level: str) -> str:
    cls = {"HIGH": "badge-high", "MEDIUM": "badge-medium", "LOW": "badge-low"}.get(level, "badge-low")
    return f'<span class="{cls}">{level}</span>'


# ============================================================
# Sidebar
# ============================================================

def render_sidebar(df: pd.DataFrame) -> tuple[str, tuple]:
    with st.sidebar:
        st.markdown("## 🛡️ Job Guard")
        st.markdown("*AI-Powered Fake Job Detector*")
        st.markdown("---")

        page = st.radio(
            "Navigation",
            ["📊 Overview", "🔍 Predictions", "⚠️ Risk Analysis", "🌐 URL Scanner", "📋 Recent Scans"],
            label_visibility="collapsed",
        )

        st.markdown("---")
        st.markdown("### Filters")

        date_range = st.date_input(
            "Date Range",
            value=(df["date"].min(), df["date"].max()),
            min_value=df["date"].min(),
            max_value=df["date"].max(),
        )

        pred_filter = st.multiselect(
            "Prediction",
            options=["Genuine", "Suspicious", "Fake"],
            default=["Genuine", "Suspicious", "Fake"],
        )

        risk_filter = st.multiselect(
            "Risk Level",
            options=["LOW", "MEDIUM", "HIGH"],
            default=["LOW", "MEDIUM", "HIGH"],
        )

        st.markdown("---")
        st.markdown("### Backend Status")
        try:
            import requests
            r = requests.get("http://localhost:8000/health", timeout=2)
            if r.status_code == 200:
                data = r.json()
                st.success(f"✅ API Online  v{data.get('version','?')}")
                st.caption(f"Uptime: {data.get('uptime_seconds', 0):.0f}s")
            else:
                st.warning("⚠️ API returned non-200")
        except Exception:
            st.error("❌ API Offline")
            st.caption("Start: uvicorn main:app --reload")

        st.markdown("---")
        st.caption("Job Guard Dashboard v1.0")

    return page, (pred_filter, risk_filter, date_range)


# ============================================================
# Pages
# ============================================================

def page_overview(df: pd.DataFrame, url_df: pd.DataFrame) -> None:
    st.markdown("## 📊 Overview")

    total        = len(df)
    fake_count   = (df["prediction"] == "Fake").sum()
    susp_count   = (df["prediction"] == "Suspicious").sum()
    phish_count  = df["phishing"].sum()
    high_risk    = (df["risk_level"] == "HIGH").sum()
    avg_conf     = df["confidence"].mean()

    # ── KPI row ──────────────────────────────────────────────
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    cards = [
        (c1, "Total Scans",       str(total),                  "+12 today",  True,  "#4f6ef7"),
        (c2, "Fake Detected",     str(fake_count),             f"{fake_count/total*100:.1f}%", False, "#f85149"),
        (c3, "Suspicious",        str(susp_count),             f"{susp_count/total*100:.1f}%", False, "#e3b341"),
        (c4, "Phishing Alerts",   str(int(phish_count)),       "URLs flagged", False, "#a371f7"),
        (c5, "High Risk",         str(int(high_risk)),         f"{high_risk/total*100:.1f}%", False, "#f85149"),
        (c6, "Avg Confidence",    f"{avg_conf:.1f}%",          "+2.3% vs last week", True, "#3fb950"),
    ]
    for col, label, val, delta, up, color in cards:
        with col:
            st.markdown(metric_card(label, val, delta, up, color), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Row 1: Pie + Bar + Trend ──────────────────────────────
    col1, col2 = st.columns([1, 1])
    with col1:
        section_header("Prediction Breakdown")
        st.plotly_chart(chart_prediction_pie(df), use_container_width=True, config={"displayModeBar": False})
    with col2:
        section_header("Risk Level Distribution")
        st.plotly_chart(chart_risk_bar(df), use_container_width=True, config={"displayModeBar": False})

    # ── Row 2: Trend ─────────────────────────────────────────
    section_header("Daily Scan Trend")
    st.plotly_chart(chart_daily_trend(df), use_container_width=True, config={"displayModeBar": False})

    # ── Row 3: Heatmap + Gauge ────────────────────────────────
    col3, col4 = st.columns([2, 1])
    with col3:
        section_header("Scan Activity Heatmap")
        st.plotly_chart(chart_weekly_heatmap(df), use_container_width=True, config={"displayModeBar": False})
    with col4:
        section_header("Phishing URL Rate")
        phishing_rate = round(url_df["is_phishing"].mean() * 100, 1)
        st.plotly_chart(chart_phishing_gauge(phishing_rate), use_container_width=True, config={"displayModeBar": False})


def page_predictions(df: pd.DataFrame) -> None:
    st.markdown("## 🔍 Prediction Analysis")

    col1, col2 = st.columns(2)
    with col1:
        section_header("Confidence Distribution")
        st.plotly_chart(chart_confidence_histogram(df), use_container_width=True, config={"displayModeBar": False})
    with col2:
        section_header("Risk Score by Prediction")
        st.plotly_chart(chart_risk_score_box(df), use_container_width=True, config={"displayModeBar": False})

    st.markdown("<br>", unsafe_allow_html=True)
    section_header("Confidence vs Risk Score")

    fig = px.scatter(
        df, x="confidence", y="risk_score",
        color="prediction",
        color_discrete_map=PRED_COLORS,
        opacity=0.7,
        hover_data={"job_snippet": True, "risk_level": True},
        labels={"confidence": "Confidence (%)", "risk_score": "Risk Score"},
    )
    fig.update_layout(
        **_base_layout("", height=380),
        xaxis=dict(gridcolor=GRID_COLOR, color=TEXT_COLOR),
        yaxis=dict(gridcolor=GRID_COLOR, color=TEXT_COLOR),
    )
    fig.update_traces(marker=dict(size=7, line=dict(width=0)))
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    # ── Accuracy summary table ────────────────────────────────
    section_header("Prediction Summary")
    summary = df.groupby("prediction").agg(
        Count=("prediction", "count"),
        Avg_Confidence=("confidence", "mean"),
        Avg_Risk_Score=("risk_score", "mean"),
        Phishing_Rate=("phishing", "mean"),
    ).round(2).reset_index()
    summary["Phishing_Rate"] = (summary["Phishing_Rate"] * 100).round(1).astype(str) + "%"
    summary["Avg_Confidence"] = summary["Avg_Confidence"].astype(str) + "%"
    st.dataframe(
        summary,
        use_container_width=True,
        hide_index=True,
        column_config={
            "prediction":     st.column_config.TextColumn("Prediction"),
            "Count":          st.column_config.NumberColumn("Count"),
            "Avg_Confidence": st.column_config.TextColumn("Avg Confidence"),
            "Avg_Risk_Score": st.column_config.NumberColumn("Avg Risk Score"),
            "Phishing_Rate":  st.column_config.TextColumn("Phishing Rate"),
        },
    )


def page_risk_analysis(df: pd.DataFrame) -> None:
    st.markdown("## ⚠️ Risk Analysis")

    # ── Risk level over time ──────────────────────────────────
    section_header("Risk Level Trend Over Time")
    daily_risk = (
        df.groupby(["date", "risk_level"])
        .size()
        .reset_index(name="count")
    )
    fig = px.bar(
        daily_risk, x="date", y="count", color="risk_level",
        color_discrete_map=RISK_COLORS,
        barmode="stack",
        labels={"count": "Scans", "date": "Date", "risk_level": "Risk Level"},
    )
    fig.update_layout(
        **_base_layout("", height=320),
        xaxis=dict(gridcolor=GRID_COLOR, color=TEXT_COLOR),
        yaxis=dict(gridcolor=GRID_COLOR, color=TEXT_COLOR),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color=TEXT_COLOR)),
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    col1, col2 = st.columns(2)

    with col1:
        section_header("Risk Score Histogram")
        fig2 = px.histogram(
            df, x="risk_score", nbins=25,
            color="risk_level",
            color_discrete_map=RISK_COLORS,
            opacity=0.8,
            labels={"risk_score": "Risk Score", "count": "Count"},
        )
        fig2.update_layout(
            **_base_layout("", height=300),
            xaxis=dict(gridcolor=GRID_COLOR, color=TEXT_COLOR),
            yaxis=dict(gridcolor=GRID_COLOR, color=TEXT_COLOR),
            barmode="overlay",
        )
        st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})

    with col2:
        section_header("High Risk Detections by Day")
        high_daily = df[df["risk_level"] == "HIGH"].groupby("date").size().reset_index(name="count")
        fig3 = go.Figure(go.Bar(
            x=high_daily["date"], y=high_daily["count"],
            marker_color="#f85149",
            hovertemplate="<b>%{x}</b><br>High Risk: %{y}<extra></extra>",
        ))
        fig3.update_layout(
            **_base_layout("", height=300),
            xaxis=dict(gridcolor=GRID_COLOR, color=TEXT_COLOR),
            yaxis=dict(gridcolor=GRID_COLOR, color=TEXT_COLOR),
        )
        st.plotly_chart(fig3, use_container_width=True, config={"displayModeBar": False})


def page_url_scanner(url_df: pd.DataFrame) -> None:
    st.markdown("## 🌐 URL Scanner Analytics")

    total_urls   = len(url_df)
    phish_urls   = url_df["is_phishing"].sum()
    safe_urls    = total_urls - phish_urls
    phish_rate   = round(phish_urls / total_urls * 100, 1)

    c1, c2, c3, c4 = st.columns(4)
    with c1: st.markdown(metric_card("URLs Scanned", str(total_urls), "+8 today", True, "#4f6ef7"), unsafe_allow_html=True)
    with c2: st.markdown(metric_card("Phishing Detected", str(int(phish_urls)), f"{phish_rate}%", False, "#f85149"), unsafe_allow_html=True)
    with c3: st.markdown(metric_card("Safe URLs", str(int(safe_urls)), "", True, "#3fb950"), unsafe_allow_html=True)
    with c4: st.markdown(metric_card("Detection Rate", f"{phish_rate}%", "vs 25% baseline", phish_rate < 25, "#a371f7"), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        section_header("Phishing vs Safe URLs")
        counts = url_df["is_phishing"].value_counts()
        fig = go.Figure(go.Pie(
            labels=["Safe", "Phishing"],
            values=[counts.get(False, 0), counts.get(True, 0)],
            hole=0.5,
            marker=dict(colors=["#3fb950", "#f85149"], line=dict(color=CARD_BG, width=2)),
            textinfo="label+percent",
            textfont=dict(color=TEXT_COLOR),
        ))
        fig.update_layout(**_base_layout("", height=300))
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    with col2:
        section_header("URL Risk Level Breakdown")
        risk_counts = url_df["risk_level"].value_counts().reindex(["LOW", "MEDIUM", "HIGH"], fill_value=0)
        fig2 = go.Figure(go.Bar(
            x=risk_counts.index, y=risk_counts.values,
            marker_color=[RISK_COLORS[r] for r in risk_counts.index],
            text=risk_counts.values, textposition="outside",
            textfont=dict(color=TEXT_COLOR),
        ))
        fig2.update_layout(
            **_base_layout("", height=300),
            xaxis=dict(color=TEXT_COLOR, showgrid=False),
            yaxis=dict(gridcolor=GRID_COLOR, color=TEXT_COLOR),
            bargap=0.35,
        )
        st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})

    section_header("Recent URL Scans")
    display = url_df.head(15).copy()
    display["timestamp"] = display["timestamp"].dt.strftime("%Y-%m-%d %H:%M")
    display["Status"] = display["is_phishing"].map({True: "🔴 Phishing", False: "🟢 Safe"})
    st.dataframe(
        display[["timestamp", "url", "Status", "risk_level", "risk_score"]],
        use_container_width=True,
        hide_index=True,
        column_config={
            "timestamp":  st.column_config.TextColumn("Time"),
            "url":        st.column_config.TextColumn("URL", width="large"),
            "Status":     st.column_config.TextColumn("Status"),
            "risk_level": st.column_config.TextColumn("Risk Level"),
            "risk_score": st.column_config.ProgressColumn("Score", min_value=0, max_value=100),
        },
    )


def page_recent_scans(df: pd.DataFrame) -> None:
    st.markdown("## 📋 Recent Scans")

    col1, col2, col3 = st.columns(3)
    with col1:
        search = st.text_input("🔍 Search job text", placeholder="e.g. UPI, registration fee...")
    with col2:
        pred_sel = st.selectbox("Filter by Prediction", ["All", "Genuine", "Suspicious", "Fake"])
    with col3:
        risk_sel = st.selectbox("Filter by Risk Level", ["All", "LOW", "MEDIUM", "HIGH"])

    filtered = df.copy()
    if search:
        filtered = filtered[filtered["job_snippet"].str.contains(search, case=False, na=False)]
    if pred_sel != "All":
        filtered = filtered[filtered["prediction"] == pred_sel]
    if risk_sel != "All":
        filtered = filtered[filtered["risk_level"] == risk_sel]

    st.caption(f"Showing {len(filtered)} of {len(df)} records")

    display = filtered.head(50).copy()
    display["timestamp"] = display["timestamp"].dt.strftime("%Y-%m-%d %H:%M")
    display["Phishing"] = display["phishing"].map({True: "⚠️ Yes", False: "—"})

    st.dataframe(
        display[["timestamp", "job_snippet", "prediction", "confidence", "risk_level", "risk_score", "Phishing"]],
        use_container_width=True,
        hide_index=True,
        column_config={
            "timestamp":   st.column_config.TextColumn("Time"),
            "job_snippet": st.column_config.TextColumn("Job Snippet", width="large"),
            "prediction":  st.column_config.TextColumn("Prediction"),
            "confidence":  st.column_config.ProgressColumn("Confidence", min_value=0, max_value=100, format="%.1f%%"),
            "risk_level":  st.column_config.TextColumn("Risk"),
            "risk_score":  st.column_config.ProgressColumn("Score", min_value=0, max_value=100),
            "Phishing":    st.column_config.TextColumn("Phishing"),
        },
    )

    st.markdown("<br>", unsafe_allow_html=True)
    section_header("Export Data")
    csv = filtered.drop(columns=["date"]).to_csv(index=False).encode("utf-8")
    st.download_button(
        label="⬇️ Download CSV",
        data=csv,
        file_name=f"job_guard_scans_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
        mime="text/csv",
    )


# ============================================================
# Main App
# ============================================================

def main() -> None:
    df     = generate_scan_history(200)
    url_df = generate_url_scan_history(80)

    page, (pred_filter, risk_filter, date_range) = render_sidebar(df)

    # Apply sidebar filters
    if len(date_range) == 2:
        start, end = date_range
        df = df[(df["date"] >= start) & (df["date"] <= end)]

    if pred_filter:
        df = df[df["prediction"].isin(pred_filter)]
    if risk_filter:
        df = df[df["risk_level"].isin(risk_filter)]

    if df.empty:
        st.warning("No data matches the selected filters. Adjust the sidebar filters.")
        return

    if   page == "📊 Overview":      page_overview(df, url_df)
    elif page == "🔍 Predictions":   page_predictions(df)
    elif page == "⚠️ Risk Analysis": page_risk_analysis(df)
    elif page == "🌐 URL Scanner":   page_url_scanner(url_df)
    elif page == "📋 Recent Scans":  page_recent_scans(df)


if __name__ == "__main__":
    main()
