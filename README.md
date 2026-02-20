# Ewa_Mini_Report_Analyzer
Agentic solution to provide response to request regarding SAP Early Watch Alert Mini (short) report.

# Technology Stack Summary
<img width="814" height="306" alt="image" src="https://github.com/user-attachments/assets/45666b7e-47b7-4528-9408-bb2339e86bfa" />

!!! In the future agent to be extended and to be used for production analysis of EWA reports for all customers, that is why all components are working only locally.

# What is SAP Early Watch alert?
SAP EarlyWatch Alert (EWA) is a periodic health-check service delivered by SAP that analyzes the technical status and performance of SAP systems. It identifies risks, bottlenecks, and optimization opportunities before they escalate into incidents.
It helps provide proactive system stabilization through performance analysis, capacity evaluation, configuration validation, risk detection and Security and compliance checks
Below you can find description of the main steps and its execution in this project.


## 1. Data Preparation
The PDF report is:

- Parsed into structured sections
- Severity levels detected (CRITICAL, WARNING, etc.)
- Converted into embeddings
- Stored in a FAISS vector index

Each chunk contains metadata (section, page, severity), enabling contextual retrieval.

## 2. RAG & Agent Flow
1. The LLM first performs **reasoning** to decide how to retrieve data.
2. The retrieval tool (`get_findings`) queries the FAISS vectorstore.
3. Retrieved chunks are injected into the LLM for grounded answer generation.
4. A **reflection step** validates grounding and may trigger a retry.
5. An **evaluation step** scores the final answer.

Execution traces are stored in: logs/agent_runs.jsonl


## 3. Reasoning & Reflection
1. Structured tool reasoning
Before answering, the LLM selects a retrieval strategy (get_findings) and defines parameters such as number of chunks (k) and optional severity filtering (e.g., CRITICAL).

2. Separation of planning and execution
The system explicitly separates reasoning (deciding how to search) from retrieval and generation, enabling dynamic, context-aware behavior instead of static querying.

3. Grounding verification
After generating an answer, the agent performs a reflection step to verify that the response is supported by the retrieved context and sufficiently complete.

4. Self-corrective retry loop
If the answer is not approved, the agent automatically adjusts retrieval parameters (e.g., increases k or modifies severity filter) and retries the process.

5. Uncertainty handling
If relevant context is not found, the system responds with “Not found in the report” instead of fabricating information, reducing hallucination risk.


## 4. Tool-Calling Mechanisms
1. Retrieval Tool (get_findings)
The LLM invokes a structured retrieval tool that queries the FAISS vectorstore using semantic similarity (MMR).

2. Metadata-aware filtering
The tool supports severity-based filtering (e.g., CRITICAL findings) and section-aware retrieval through metadata stored during data preparation.

3. Hybrid Retrieval Strategy
Uses Max Marginal Relevance (MMR) to balance relevance and diversity of retrieved chunks.

4. Parameter-driven execution
Tool behavior is controlled by LLM-generated parameters (k, severity), enabling adaptive retrieval depth and filtering.

5. Execution trace logging
All tool invocations, parameters, and retrieved document metadata are logged for transparency and review.

## 5. Evaluation
1. Automated evaluation scoring:**
After answer approval, the system scores the response on:
- Accuracy
- Relevance
- Completeness
- Confidence

2. Execution logging (agent_runs.jsonl):**
Each run stores reasoning decisions, tool parameters, reflection output, retry behavior, evaluation scores, and timing metrics.

3. Grounded response enforcement:**
The system enforces context-only generation and rejects unsupported claims via reflection.

**Manual QA validation (results could be found in attached screenshots)** 
Tested with SAP EWA-specific queries such as:
1. List all CRITICAL findings in the report. [Severity-Based Query (Metadata Filtering Test)]
2. What are the main risks identified in Finance processes? [Specific Domain Query (Semantic Retrieval Test)]
3. What actions are recommended to improve overall system performance? [Incomplete Context Trigger (Reflection & Retry Test)]
4. What cloud migration strategy is recommended in the report? [Unsupported Query (Hallucination Guard Test)]
5. Compare Finance and Procurement issues mentioned in the report. [Comparative Retrieval Test]

**Performance measurement:**
Timing metrics are recorded per stage (reasoning, retrieval, generation, reflection, evaluation), enabling transparent performance analysis.

**Project Structure**
<img width="910" height="541" alt="image" src="https://github.com/user-attachments/assets/5f13534f-abb6-4bed-b16c-41290cb1c928" />


**Execution instaruction**
### 1. Install dependencies

pip install -r requirements.txt

### 2. Start Ollama (ensure Mistral is installed)

ollama run mistral

### 3. Run the application

streamlit run /sap_ewa_agent/src/ui_app.py

http://localhost:8501/

1. Upload EWA report
2. Prepare knowledge base -> click: "Run data preparation"
3. Provide question
4. Get response

