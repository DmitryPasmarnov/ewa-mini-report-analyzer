from pathlib import Path
import json
from typing import Dict

from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.prompts import PromptTemplate

# ========================
# Paths
# ========================
BASE_DIR = Path(__file__).resolve().parents[1]
VECTORSTORE_PATH = BASE_DIR / "vectorstore" / "sap_mini_ewa_faiss"


# ========================
# Load vectorstore
# ========================
def load_vectorstore():
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )
    return FAISS.load_local(
        VECTORSTORE_PATH,
        embeddings,
        allow_dangerous_deserialization=True
    )


# ========================
# Hybrid Retrieval
# ========================
def hybrid_retrieve(vectorstore, question: str, k=8, severity=None):

    if not question:
        return []

    docs = vectorstore.max_marginal_relevance_search(
        question,
        k=k,
        fetch_k=12
    )

    if severity:
        filtered = [d for d in docs if d.metadata.get("severity") == severity]
        if filtered:
            docs = filtered

    seen = set()
    unique_docs = []
    for d in docs:
        key = (d.metadata.get("page"), d.metadata.get("section"))
        if key not in seen:
            seen.add(key)
            unique_docs.append(d)

    return unique_docs


# ========================
# Tool Execution
# ========================
def tool_get_findings(vectorstore, args: Dict):
    question = args.get("question")
    k = args.get("k", 8)
    if not isinstance(k, int) or k <= 0:
        k = 8
    severity = args.get("severity")
    print("k value:", k, type(k))

    return hybrid_retrieve(vectorstore, question, k=k, severity=severity)


# ========================
# Tool Decision
# ========================
def decide_action(llm, question):

    tool_schema = """
You are an SAP AI agent.

Available tools:
1. get_findings

Return ONLY valid JSON:
{
  "action": "...",
  "parameters": {
      "question": "...",
      "k": int,
      "severity": string or null
  }
}
"""

    response = llm.invoke(
        f"{tool_schema}\n\nUser question:\n{question}"
    ).strip()

    # Remove markdown wrappers if present
    if response.startswith("```"):
        response = response.split("```")[1].strip()

    try:
        return json.loads(response)
    except:
        return {
            "action": "get_findings",
            "parameters": {"question": question, "k": 5, "severity": None}
        }


# ========================
# Answer Generation
# ========================
def generate_answer(llm, question, docs):

    context = "\n\n".join(
        f"[Page {d.metadata.get('page')} | "
        f"{d.metadata.get('section')} | "
        f"{d.metadata.get('severity')}]\n"
        f"{d.page_content[:800]}"  # truncate
        for d in docs
    )

    prompt = PromptTemplate.from_template(
        """
You are an SAP consultant.

Answer ONLY using the provided context.
If unsupported, respond: Not found in the report.

Context:
{context}

Question:
{question}

Answer:
"""
    )

    answer = llm.invoke(
        prompt.format(context=context, question=question)
    )

    return answer, context


# ========================
# Reflection
# ========================
def reflect(llm, question, answer, context):

    reflection_prompt = f"""
Evaluate the SAP answer.

Return JSON:
{{
  "approved": true/false,
  "retry_with": {{
      "k": int,
      "severity": string or null
  }}
}}

Question:
{question}

Answer:
{answer}
"""

    response = llm.invoke(reflection_prompt).strip()

    if response.startswith("```"):
        response = response.split("```")[1].strip()

    try:
        return json.loads(response)
    except:
        return {"approved": True}


# ========================
# Evaluation
# ========================
def evaluate_answer(llm, question, answer, context):

    scoring_prompt = f"""
Score the SAP answer from 1–5.

Return JSON:
{{
 "accuracy": int,
 "relevance": int,
 "completeness": int,
 "clarity": int,
 "confidence": float
}}

Question:
{question}

Answer:
{answer}
"""

    response = llm.invoke(scoring_prompt).strip()

    if response.startswith("```"):
        response = response.split("```")[1].strip()

    try:
        return json.loads(response)
    except:
        return {}
