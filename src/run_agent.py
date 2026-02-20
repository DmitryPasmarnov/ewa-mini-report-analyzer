import time
import json
from pathlib import Path
from datetime import datetime
from copy import deepcopy

from langchain_ollama import OllamaLLM
from rag_query import (
    load_vectorstore,
    decide_action,
    tool_get_findings,
    generate_answer,
    reflect,
    evaluate_answer
)

MAX_RETRIES = 2

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "agent_runs.jsonl"


def run_agent(question: str):

    overall_start = time.time()

    llm = OllamaLLM(model="mistral", temperature=0.0)
    vectorstore = load_vectorstore()

    trace = {
        "timestamp": datetime.utcnow().isoformat(),
        "question": question,
        "approved": False,
        "retries": 0,
        "stages": {}
    }

    # ==========================================================
    # 1️⃣ REASONING
    # ==========================================================
    start = time.time()
    raw_decision = decide_action(llm, question)

    trace["stages"]["reasoning"] = {
        "raw_output": raw_decision,
        "tool_selected": raw_decision.get("action"),
        "parameters": raw_decision.get("parameters"),
        "time_sec": round(time.time() - start, 2)
    }

    action_decision = deepcopy(raw_decision)
    retries = 0
    approved = False

    # ==========================================================
    # AGENT LOOP
    # ==========================================================
    while retries <= MAX_RETRIES and not approved:

        iteration_key = f"iteration_{retries+1}"
        trace["stages"][iteration_key] = {}

        # -------------------------
        # 2️⃣ TOOL CALLING
        # -------------------------
        start = time.time()
        params_before = deepcopy(action_decision.get("parameters", {}))

        docs = tool_get_findings(vectorstore, params_before)

        retrieved_meta = [
            {
                "page": d.metadata.get("page"),
                "section": d.metadata.get("section"),
                "severity": d.metadata.get("severity")
            }
            for d in docs
        ]

        trace["stages"][iteration_key]["tool_calling"] = {
            "parameters_used": params_before,
            "retrieved_count": len(docs),
            "retrieved_documents": retrieved_meta,
            "time_sec": round(time.time() - start, 2)
        }

        # -------------------------
        # 3️⃣ GENERATION
        # -------------------------
        start = time.time()
        answer, context = generate_answer(llm, question, docs)

        trace["stages"][iteration_key]["generation"] = {
            "context_length_chars": len(context),
            "answer_length_chars": len(answer),
            "answer_preview": answer[:300],
            "time_sec": round(time.time() - start, 2)
        }

        # -------------------------
        # 4️⃣ REFLECTION
        # -------------------------
        start = time.time()
        reflection = reflect(llm, question, answer, context)

        approved = reflection.get("approved", True)

        trace["stages"][iteration_key]["reflection"] = {
            "reflection_output": reflection,
            "approved": approved,
            "time_sec": round(time.time() - start, 2)
        }

        # -------------------------
        # 5️⃣ RETRY LOGIC
        # -------------------------
        if not approved:
            retries += 1
            retry_params = reflection.get("retry_with", {})

            action_decision.setdefault("parameters", {})

            for key, value in retry_params.items():
                if key == "k":
                    if isinstance(value, int) and value > 0:
                        action_decision["parameters"]["k"] = value
                elif key == "severity":
                    action_decision["parameters"]["severity"] = value
            trace["stages"][iteration_key]["retry"] = {
                "retry_triggered": True,
                "retry_parameters": retry_params,
                "updated_parameters": action_decision["parameters"]
            }
        else:
            trace["stages"][iteration_key]["retry"] = {
                "retry_triggered": False
            }

    trace["approved"] = approved
    trace["retries"] = retries
    trace["final_answer"] = answer

    # ==========================================================
    # 6️⃣ EVALUATION
    # ==========================================================
    start = time.time()
    evaluation = evaluate_answer(llm, question, answer, context)

    trace["stages"]["evaluation"] = {
        "evaluation_output": evaluation,
        "time_sec": round(time.time() - start, 2)
    }

    trace["total_time_sec"] = round(time.time() - overall_start, 2)

    # ==========================================================
    # LOG TO FILE
    # ==========================================================
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(trace, indent=None) + "\n")

    return trace
