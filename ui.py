import streamlit as st
import time

from src.multi_agent_pipeline import get_answer

st.set_page_config(page_title="AI Risk Analyst", layout="wide")

st.title("AI Financial Risk Analyst")
st.write("Ask questions about company risks and mitigation strategies.")

query = st.text_input("Enter your question:")

if st.button("Analyze"):
    if query:
        with st.spinner("Analyzing..."):
            start = time.time()

            try:
                data = get_answer(query)

                end = time.time()

                st.success("Analysis complete")

                st.subheader("Decision")
                st.write(data["decision"])

                st.subheader("Reasoning")
                st.write(data["reasoning"])

                st.subheader("Answer")
                st.write(data["answer"])

                st.caption(f"Response time: {round(end - start, 2)} sec")

            except Exception as e:
                st.error("Something went wrong")
                st.write(str(e))
    else:
        st.warning("Please enter a query")
