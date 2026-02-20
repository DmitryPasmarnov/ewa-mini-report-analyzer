import streamlit as st
import shutil
import tempfile
from pathlib import Path

from run_agent import run_agent
from data_preparation import main as run_data_preparation

# ========================
# Paths
# ========================
BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
PDF_PATH = DATA_DIR / "MiniEwa.pdf"

st.set_page_config(
    page_title="SAP EWA Assistant",
    layout="centered"
)

st.title("SAP EWA Assistant")

# ============================================================
# 1️⃣ Upload PDF
# ============================================================

st.header("1. Upload EWA Report")

uploaded_pdf = st.file_uploader(
    "Upload SAP MiniEWA PDF",
    type=["pdf"]
)

if uploaded_pdf:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(uploaded_pdf.read())
        tmp_path = Path(tmp.name)

    shutil.move(str(tmp_path), PDF_PATH)

    st.success("Document uploaded successfully.")

# ============================================================
# 2️⃣ Data Preparation
# ============================================================

st.header("2. Prepare Knowledge Base")

if st.button("Run Data Preparation"):

    if not PDF_PATH.exists():
        st.error("Please upload a PDF first.")
    else:
        with st.spinner("Preparing knowledge base..."):
            run_data_preparation()
        st.success("Data preparation completed.")

# ============================================================
# 3️⃣ Ask Question
# ============================================================

st.header("3. Ask a Question")

question = st.text_area(
    "Enter your question:",
    height=120
)

if st.button("Get Answer"):

    if not question.strip():
        st.warning("Please enter a question.")
        st.stop()

    if not PDF_PATH.exists():
        st.error("Please upload and prepare a document first.")
        st.stop()

    with st.spinner("Generating answer..."):
        try:
            trace = run_agent(question)
        except Exception as e:
            st.error(f"Error: {str(e)}")
            st.stop()

    final_answer = trace.get("final_answer", "No answer generated.")

    st.subheader("Answer")
    st.success(final_answer)
