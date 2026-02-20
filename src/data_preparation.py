from pathlib import Path
import re
from typing import List, Dict
from pypdf import PdfReader
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS


# ========================
# Paths
# ========================
BASE_DIR = Path(__file__).resolve().parents[1]
VECTORSTORE_PATH = BASE_DIR / "vectorstore" / "sap_mini_ewa_faiss"
PDF_PATH = BASE_DIR / "data" / "MiniEwa.pdf"


# ========================
# PDF Loader
# ========================
def load_pdf(pdf_path: Path) -> List[Dict]:
    reader = PdfReader(str(pdf_path))
    pages = []

    for idx, page in enumerate(reader.pages):
        text = page.extract_text()
        if text:
            pages.append({
                "page": idx + 1,
                "text": text
            })

    return pages


# ==========================
# Structured SAP Parsing
# ==========================
# SECTION_PATTERN: <number>[.<number>]* <space> <text>
# 1 Introduction
# 2.1 Architecture Overview
# 3.4.2 Database Layer
# 10.2.5.1 Detailed Findings
# --------------------------
# Below does not match
# Introduction
# 1Introduction
# 1.
SECTION_PATTERN = re.compile(r"^\d+(\.\d+)*\s+.+")

# SEVERITY_PATTERN: Severity:\s*(CRITICAL|WARNING|OK)
# Matches:
# Severity: CRITICAL
# Severity:WARNING
# Severity:   OK
# severity: warning
# --------------------------
# Does NOT match:
# Severity - CRITICAL
# Severity CRITICAL
# Severity: INFO

SEVERITY_PATTERN = re.compile(r"Severity:\s*(CRITICAL|WARNING|OK)", re.IGNORECASE)


def normalize_severity(sev: str):
    if not sev:
        return "UNKNOWN"
    sev = sev.upper()
    if "CRITICAL" in sev:
        return "CRITICAL"
    if "WARNING" in sev:
        return "WARNING"
    if "OK" in sev:
        return "OK"
    return "UNKNOWN"


def parse_sections(pages: List[Dict]):

    chunks = []
    current_section = "General"
    current_severity = "UNKNOWN"
    buffer = []

    for page in pages:
        lines = page["text"].split("\n")

        for line in lines:

            # Detect new numbered section (e.g., 3.1 SAP Application Maintenance Status)
            if SECTION_PATTERN.match(line.strip()):

                if buffer:
                    chunks.append({
                        "content": "\n".join(buffer).strip(),
                        "section": current_section,
                        "severity": current_severity,
                        "page": page["page"]
                    })
                    buffer = []

                current_section = line.strip()
                current_severity = "UNKNOWN"

            # Detect severity line
            sev_match = SEVERITY_PATTERN.search(line)
            if sev_match:
                current_severity = normalize_severity(sev_match.group(1))

            buffer.append(line)

        # Flush page boundary safely
        if buffer and len("\n".join(buffer)) > 2000:
            chunks.append({
                "content": "\n".join(buffer).strip(),
                "section": current_section,
                "severity": current_severity,
                "page": page["page"]
            })
            buffer = []

    if buffer:
        chunks.append({
            "content": "\n".join(buffer).strip(),
            "section": current_section,
            "severity": current_severity,
            "page": page["page"]
        })

    return chunks


# ========================
# Metadata Enrichment
# ========================
def enrich_chunks(chunks):

    documents = []

    for c in chunks:
        documents.append(
            Document(
                page_content=c["content"],
                metadata={
                    "section": c["section"],
                    "severity": c["severity"],
                    "page": c["page"],
                    "document": "MiniEWA",
                    "system": "SAP S/4HANA 1610",
                    "database": "SAP HANA 2.0 SP05"
                }
            )
        )

    return documents


# ========================
# Main Execution
# ========================
def main():

    print("Loading PDF...")
    pages = load_pdf(PDF_PATH)

    print("Parsing structured SAP sections...")
    chunks = parse_sections(pages)

    print(f"Generated {len(chunks)} structured chunks")

    documents = enrich_chunks(chunks)

    print("Creating embeddings...")
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )

    vectorstore = FAISS.from_documents(documents, embeddings)

    VECTORSTORE_PATH.mkdir(parents=True, exist_ok=True)
    vectorstore.save_local(str(VECTORSTORE_PATH))

    print("Vectorstore saved successfully.")


if __name__ == "__main__":
    main()
