# src/test_data_preparation.py

from pathlib import Path
from data_preparation import (
    load_pdf,
    sap_aware_chunking,
    enrich_chunks,
    build_vectorstore
)


PDF_PATH = Path("../data/MiniEwa.pdf")


def test_pdf_loading():
    pages = load_pdf(PDF_PATH)
    assert len(pages) > 0
    assert "text" in pages[0]
    print("✔ PDF loading test passed")


def test_chunking():
    pages = load_pdf(PDF_PATH)
    chunks = sap_aware_chunking(pages[0])

    assert len(chunks) > 0
    assert "section" in chunks[0]
    assert "severity" in chunks[0]
    print("✔ Chunking test passed")


def test_metadata_enrichment():
    pages = load_pdf(PDF_PATH)
    chunks = sap_aware_chunking(pages[0])
    documents = enrich_chunks(chunks)

    doc = documents[0]
    assert doc.metadata["document"] == "MiniEWA"
    assert doc.metadata["system"] == "SAP S/4HANA"
    print("✔ Metadata enrichment test passed")


def test_vectorstore_retrieval():
    pages = load_pdf(PDF_PATH)
    all_chunks = []

    for page in pages:
        all_chunks.extend(sap_aware_chunking(page))

    documents = enrich_chunks(all_chunks)
    vectorstore = build_vectorstore(documents)

    results = vectorstore.similarity_search("CRITICAL security risks", k=3)

    assert len(results) > 0
    print("✔ Vector store retrieval test passed")


if __name__ == "__main__":
    test_pdf_loading()
    test_chunking()
    test_metadata_enrichment()
    test_vectorstore_retrieval()
