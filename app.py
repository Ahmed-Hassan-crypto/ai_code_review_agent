"""AI Code Review Agent — Streamlit Frontend"""

import streamlit as st
import requests
from utils.pdf_report import generate_review_pdf

# Page Config
st.set_page_config(
    page_title="AI Code Review Agent",
    page_icon="🔍",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# Styles
st.markdown(
    """
<style>
    .main .block-container {
        max-width: 900px;
        padding-top: 2rem;
    }
    .stButton button {
        width: 100%;
    }
    .hero-title {
        text-align: center;
        padding: 20px 0;
    }
    .feature-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 10px;
        color: white;
        margin: 10px 0;
    }
    .status-step {
        padding: 8px 0;
        color: #666;
    }
    .status-step.active {
        color: #4CAF50;
        font-weight: bold;
    }
</style>
""",
    unsafe_allow_html=True,
)


# Check for deployed API URL or use localhost
DEPLOYED_API = (
    None  # Set to your Render URL when deployed, e.g., "https://your-app.onrender.com"
)
API_URL = DEPLOYED_API if DEPLOYED_API else "http://localhost:8000"


# Header
st.markdown(
    """
<div class="hero-title">
    <h1>🔍 AI Code Review Agent</h1>
    <p>Automated code reviews powered by AI</p>
</div>
""",
    unsafe_allow_html=True,
)

st.divider()

# PR Input Section
st.subheader("🚀 Submit PR for Review")

col1, col2 = st.columns([5, 1])
with col1:
    pr_url = st.text_input(
        "GitHub Pull Request URL",
        placeholder="https://github.com/owner/repo/pull/123",
        label_visibility="collapsed",
    )
with col2:
    review_clicked = st.button("Review PR", type="primary")

st.divider()

# Run Review
if review_clicked and pr_url:
    with st.status("Running AI Code Review...", expanded=True) as status:
        st.write("📡 Fetching PR diff from GitHub...")
        st.write("🔎 Running AI analysis...")
        st.write("📊 Generating results...")

        try:
            response = requests.post(
                f"{API_URL}/review",
                json={"pr_url": pr_url},
                timeout=300,
            )

            if response.status_code == 200:
                status.update(label="Review Complete!", state="complete")
                data = response.json()
                st.session_state["review_data"] = data
                st.session_state["pr_url"] = pr_url
            else:
                status.update(label="Review Failed", state="error")
                st.error(f"Error {response.status_code}: {response.text}")
        except requests.exceptions.ConnectionError:
            status.update(label="Connection Failed", state="error")
            st.error(f"Cannot connect to API at {API_URL}")
        except Exception as e:
            status.update(label="Error", state="error")
            st.error(f"Error: {e}")

elif review_clicked and not pr_url:
    st.warning("Please enter a GitHub PR URL")

# Display Results
if "review_data" in st.session_state:
    data = st.session_state["review_data"]
    st.divider()

    # Score Overview
    overall = data.get("overall_score", 0)
    score_emoji = "✅" if overall >= 7 else "⚠️" if overall >= 5 else "❌"

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Overall Score", f"{overall}/10")
    with col2:
        st.metric("Files Reviewed", len(data.get("scores", [])))
    with col3:
        total_issues = sum(
            len(r.get("lint_issues", [])) for r in data.get("lint_results", [])
        )
        st.metric("Issues Found", total_issues)

    st.divider()

    # PDF Download
    try:
        pdf_bytes = generate_review_pdf(data)
        pr_title = data.get("pr_title", "review").replace(" ", "_")[:30]
        st.download_button(
            label="📥 Download PDF Report",
            data=pdf_bytes,
            file_name=f"review_{pr_title}.pdf",
            mime="application/pdf",
            type="primary",
            use_container_width=True,
        )
    except Exception as e:
        st.warning(f"PDF generation failed: {e}")

    st.divider()

    # Per-File Results
    st.subheader("📂 File Reviews")

    scores = data.get("scores", [])
    lint_results = data.get("lint_results", [])
    fix_suggestions = data.get("fix_suggestions", [])

    for s in scores:
        fname = s.get("filename", "unknown")
        fscore = s.get("score", 7)
        status_icon = "✅" if fscore >= 7 else "⚠️" if fscore >= 5 else "❌"

        with st.expander(f"{status_icon} {fname} — Score: {fscore}/10"):
            st.info(s.get("justification", ""))
            st.progress(fscore / 10)

            # Tabs
            tab1, tab2, tab3 = st.tabs(["Issues", "Fixes", "Raw"])

            with tab1:
                fl = next((r for r in lint_results if r.get("filename") == fname), {})
                issues = fl.get("lint_issues", [])
                if issues:
                    for i in issues:
                        st.markdown(
                            f"- **{i.get('severity', '')}** Line {i.get('line', '?')}: {i.get('message', '')}"
                        )
                        if i.get("suggestion"):
                            st.caption(f"💡 {i['suggestion']}")
                else:
                    st.success("No issues")

            with tab2:
                ff = next(
                    (r for r in fix_suggestions if r.get("filename") == fname), {}
                )
                fixes = ff.get("fixes", [])
                if fixes:
                    for f in fixes:
                        st.markdown(f"**{f.get('issue_title', 'Fix')}**")
                        if f.get("original_code") and f.get("fixed_code"):
                            col_a, col_b = st.columns(2)
                            with col_a:
                                st.code(f["original_code"], language="python")
                            with col_b:
                                st.code(f["fixed_code"], language="python")
                else:
                    st.success("No fixes needed")

            with tab3:
                st.json(s)

    # Full Review
    with st.expander("📄 Full Review"):
        st.markdown(data.get("final_review", ""))

# Footer
st.divider()
st.markdown(
    """
<div style="text-align: center; color: #888; padding: 20px;">
    <p>Powered by LangGraph + Groq</p>
</div>
""",
    unsafe_allow_html=True,
)
