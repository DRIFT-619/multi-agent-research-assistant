import streamlit as st
import requests
import time

API_URL = "http://127.0.0.1:8000/ask"

# ---------------- PAGE CONFIG ----------------
st.set_page_config(
    page_title="AI Risk Analyst",
    layout="wide"
)

# ---------------- CUSTOM CSS ----------------
st.markdown("""
<style>
.main {
    background-color: #0E1117;
}
.block-container {
    padding-top: 2rem;
}
.card {
    background-color: #f3f4f6;
    padding: 20px;
    border-radius: 12px;
    margin-bottom: 20px;
}
.title {
    font-size: 48px;
    font-weight: bold;
    color: black;
    text-align: center;
}
.subtitle {
    font-size: 20px;
    color: #4A90E2;
    text-align: center;
    margin-bottom: 30px;
}
.metric-box {
    background-color: #f3f4f6;
    padding: 15px;
    border-radius: 10px;
    text-align: center;
}
</style>
""", unsafe_allow_html=True)

# ---------------- HEADER ----------------
st.markdown('<div class="title">AI Financial Risk Analyst</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Hybrid RAG + Knowledge Graph System</div>', unsafe_allow_html=True)

st.write("")

# ---------------- INPUT ----------------
st.markdown(
    "<h4 style='color:black;'>Ask a question about company risks and mitigation strategies:</h4>",
    unsafe_allow_html=True
)

query = st.text_input("", placeholder="e.g. What risks does Alphabet face?")

# ---------------- BUTTON ----------------
if st.button("Analyze"):
    if query:
        with st.spinner("Running multi-agent analysis..."):
            start = time.time()

            response = requests.post(API_URL, json={"query": query})

            end = time.time()

        if response.status_code == 200:
            data = response.json()

            st.success("Analysis Complete")

            col1, col2, col3 = st.columns(3)

            with col1:
                st.markdown('<div class="metric-box">Decision<br><b>{}</b></div>'.format(data["decision"]), unsafe_allow_html=True)

            with col2:
                st.markdown('<div class="metric-box">Response Time<br><b>{:.2f}s</b></div>'.format(end - start), unsafe_allow_html=True)

            with col3:
                st.markdown('<div class="metric-box">Mode<br><b>Hybrid AI</b></div>', unsafe_allow_html=True)

            st.write("")

            # Reasoning Card
            st.markdown('<div class="card"><h4>Planner Reasoning</h4>{}</div>'.format(data["reasoning"]), unsafe_allow_html=True)

            # Answer Card
            st.markdown('<div class="card"><h4>Final Analysis</h4>{}</div>'.format(data["answer"]), unsafe_allow_html=True)

        else:
            st.error(f"API request failed: {response.status_code}")
            st.write(response.text)
    else:
        st.warning("Please enter a query")