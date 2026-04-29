import streamlit as st
import requests
import time

API_URL = "http://127.0.0.1:8000/ask"

st.set_page_config(page_title="AI Risk Analyst", layout="wide")

st.title("AI Financial Risk Analyst")
st.write("Ask questions about company risks and mitigation strategies.")

query = st.text_input("Enter your question:")

if st.button("Analyze"):
    if query:
        with st.spinner("Analyzing..."):
            start = time.time()

            response = requests.post(API_URL, json={"query": query})

            end = time.time()

            if response.status_code == 200:
                data = response.json()

                st.success("Analysis complete")

                st.subheader("Decision")
                st.write(data["decision"])

                st.subheader("Reasoning")
                st.write(data["reasoning"])

                st.subheader("Answer")
                st.write(data["answer"])

                st.caption(f"⏱ Response time: {round(end - start, 2)} sec")

            else:
                st.error(f"API request failed: {response.status_code}")
                st.write(response.text)
    else:
        st.warning("Please enter a query")