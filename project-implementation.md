# Deterministic GraphRAG Compliance Engine — MVP Implementation Guide

> **Goal:** Build a working MVP that proves the core loop:  
> `User Question → Graph Context → LLM Answer → Deterministic Validation → Approved / Rejected`

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [MVP Scope Definition](#2-mvp-scope-definition)
3. [Architecture Deep Dive](#3-architecture-deep-dive)
4. [Phase 0 — Environment Setup](#phase-0--environment-setup)
5. [Phase 1 — Neo4j Graph Foundation](#phase-1--neo4j-graph-foundation)
6. [Phase 2 — FastAPI Skeleton](#phase-2--fastapi-skeleton)
7. [Phase 3 — LLM Integration](#phase-3--llm-integration)
8. [Phase 4 — GraphRAG Pipeline](#phase-4--graphrag-pipeline)
9. [Phase 5 — Validation Layer](#phase-5--validation-layer)
10. [Phase 6 — End-to-End Wiring](#phase-6--end-to-end-wiring)
11. [Phase 7 — Testing & Demo](#phase-7--testing--demo)
12. [File-by-File Implementation](#file-by-file-implementation)
13. [Data Seeding (Neo4j Rules)](#data-seeding-neo4j-rules)
14. [Environment Variables Reference](#environment-variables-reference)
15. [Running the Project](#running-the-project)
16. [MVP Checklist](#mvp-checklist)
17. [Post-MVP Roadmap](#post-mvp-roadmap)

---

## 1. Project Overview

### What This System Does

```
┌─────────────────────────────────────────────────────────────────┐
│                    COMPLIANCE CHECK FLOW                        │
│                                                                 │
│  User asks question                                             │
│       │                                                         │
│       ▼                                                         │
│  Neo4j Graph  ──► fetch relevant rules ──► build context        │
│       │                                                         │
│       ▼                                                         │
│  LLM (Gemini/Groq/MiniMax)  ──► generate JSON answer           │
│       │                                                         │
│       ▼                                                         │
│  Validation Layer  ──► cross-check answer vs graph rules        │
│       │                                                         │
│       ▼                                                         │
│  { approved: true/false, reason: "..." }                        │
└─────────────────────────────────────────────────────────────────┘
```

### Key Design Principles

- **Deterministic core** — validation never delegates to the LLM; rules are code
- **Model-agnostic** — swap LLM provider by changing one env variable
- **Graph-as-truth** — Neo4j is the single source of compliance rules
- **Structured output** — LLM is forced to return JSON; no free-text parsing

---

## 2. MVP Scope Definition

### ✅ IN SCOPE (MVP)

| Feature | Description |
|---------|-------------|
| Single domain | Approval/authorization rules only |
| 5–8 hardcoded rules | Seeded into Neo4j at startup |
| One LLM provider | Google Gemini (free tier) as default |
| REST API | Single `/ask` endpoint |
| Validation layer | Keyword + graph cross-check |
| JSON logging | Every request + validation decision logged |
| Local run | `uvicorn` on localhost |

### ❌ OUT OF SCOPE (MVP)

- Auth / API keys on the endpoint
- Multi-domain rules
- UI / Frontend
- Database migrations
- Docker / deployment
- Multiple concurrent LLM calls

---

## 3. Architecture Deep Dive

### Component Diagram

```
┌──────────────────────────────────────────────────────────────┐
│                        FastAPI App                           │
│                                                              │
│  POST /ask                                                   │
│       │                                                      │
│       ▼                                                      │
│  ┌─────────────────────────────────────────────────────┐     │
│  │               GraphRAGService                       │     │
│  │                                                     │     │
│  │  1. graph.get_context(question)                     │     │
│  │       └─► Neo4jClient ──► Cypher ──► rules list     │     │
│  │                                                     │     │
│  │  2. build_prompt(question, rules)                   │     │
│  │                                                     │     │
│  │  3. llm.generate(prompt)                            │     │
│  │       └─► GeminiAdapter / GroqAdapter / ...         │     │
│  │                                                     │     │
│  │  4. validation_service.validate(answer, rules)      │     │
│  │       └─► keyword check                             │     │
│  │       └─► graph cross-check                         │     │
│  │       └─► JSON parse check                          │     │
│  │                                                     │     │
│  │  5. return ComplianceResponse                       │     │
│  └─────────────────────────────────────────────────────┘     │
└──────────────────────────────────────────────────────────────┘
```

### Data Flow Detail

```
Step 1: User sends POST /ask  {"question": "Can intern approve $500?"}

Step 2: Neo4j Cypher query
        MATCH (r:Rule)-[:APPLIES_TO]->(t:Topic {name:"approval"})
        RETURN r.id, r.description, r.prohibited_keywords

Step 3: Context assembled as string
        "Rule 1: Manager can approve requests under 10k
         Rule 2: Intern cannot approve any requests
         Rule 3: ..."

Step 4: Prompt sent to LLM
        "You are a compliance assistant. Given ONLY these rules:
         {context}
         Answer this question in JSON:
         {question}
         Format: {"decision":"approve|reject","reason":"..."}"

Step 5: LLM returns
        {"decision":"approve","reason":"Intern can approve small requests"}

Step 6: ValidationService checks:
        - JSON valid? ✅
        - "intern can approve" in reason? ✅ → PROHIBITED
        - Result: approved=false, reason="Violates rule: intern cannot approve"

Step 7: Response sent back
        {
          "question": "Can intern approve $500?",
          "llm_output": {"decision":"approve","reason":"..."},
          "approved": false,
          "validation_reason": "Violates rule: intern cannot approve",
          "graph_rules_applied": ["Rule 2"]
        }
```

---

## Phase 0 — Environment Setup

### 0.1 Project Initialization

```bash
mkdir graphrag-lite
cd graphrag-lite

python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install fastapi uvicorn[standard] neo4j pydantic python-dotenv requests
pip freeze > requirements.txt
```

### 0.2 Folder Structure

```bash
mkdir -p app/api app/core app/graph app/services app/models data
touch app/__init__.py
touch app/api/__init__.py app/api/routes.py
touch app/core/__init__.py app/core/llm_interface.py
touch app/core/gemini_adapter.py app/core/groq_adapter.py
touch app/graph/__init__.py app/graph/neo4j_client.py app/graph/queries.py
touch app/services/__init__.py
touch app/services/graphrag_service.py app/services/validation_service.py
touch app/models/__init__.py app/models/schemas.py
touch app/main.py
touch data/rules.txt
touch .env .env.example README.md
```

### 0.3 .env.example

```env
# LLM Provider — choose one: gemini | groq | minimax
LLM_PROVIDER=gemini

# Google Gemini (free at ai.google.dev)
GEMINI_API_KEY=your_gemini_api_key_here

# Groq (free at console.groq.com)
GROQ_API_KEY=your_groq_api_key_here

# Neo4j Aura Free (console.neo4j.io)
NEO4J_URI=neo4j+s://xxxxxxxx.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password_here

# App settings
APP_ENV=development
LOG_LEVEL=INFO
```

### 0.4 Neo4j Aura Free Setup

1. Go to [console.neo4j.io](https://console.neo4j.io)
2. Create a free AuraDB instance
3. Download the credentials file
4. Copy `URI`, `Username`, `Password` into your `.env`
5. Wait ~2 minutes for the instance to be ready

---

## Phase 1 — Neo4j Graph Foundation

### 1.1 Neo4j Client

**File: `app/graph/neo4j_client.py`**

```python
import logging
from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable

logger = logging.getLogger(__name__)


class Neo4jClient:
    def __init__(self, uri: str, user: str, password: str):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self._verify_connection()

    def _verify_connection(self):
        try:
            self.driver.verify_connectivity()
            logger.info("Neo4j connection established successfully.")
        except ServiceUnavailable as e:
            logger.error("Could not connect to Neo4j: %s", e)
            raise

    def close(self):
        self.driver.close()

    def get_rules_by_topic(self, topic: str) -> list[dict]:
        """
        Fetch all compliance rules related to a topic.
        Returns list of {id, description, prohibited_keywords, severity}
        """
        query = """
        MATCH (r:Rule)-[:APPLIES_TO]->(t:Topic {name: $topic})
        RETURN r.id          AS id,
               r.description AS description,
               r.prohibited_keywords AS prohibited_keywords,
               r.severity    AS severity
        ORDER BY r.severity DESC
        """
        with self.driver.session() as session:
            results = session.run(query, topic=topic)
            return [dict(record) for record in results]

    def get_all_rules(self) -> list[dict]:
        """Fetch every rule in the graph (used for full context fallback)."""
        query = """
        MATCH (r:Rule)
        RETURN r.id          AS id,
               r.description AS description,
               r.prohibited_keywords AS prohibited_keywords,
               r.severity    AS severity
        ORDER BY r.severity DESC
        """
        with self.driver.session() as session:
            results = session.run(query)
            return [dict(record) for record in results]

    def get_role_permissions(self, role: str) -> list[dict]:
        """Fetch what a specific role can/cannot do."""
        query = """
        MATCH (p:Role {name: $role})-[rel]->(action:Action)
        RETURN type(rel) AS permission_type,
               action.name AS action,
               action.limit AS limit
        """
        with self.driver.session() as session:
            results = session.run(query, role=role)
            return [dict(record) for record in results]

    def run_raw(self, query: str, params: dict = None) -> list[dict]:
        """Execute a raw Cypher query. Use with caution."""
        with self.driver.session() as session:
            results = session.run(query, params or {})
            return [dict(record) for record in results]
```

### 1.2 Cypher Queries Reference

**File: `app/graph/queries.py`**

```python
# All Cypher queries used in the application, kept in one place for easy editing.

GET_RULES_BY_TOPIC = """
MATCH (r:Rule)-[:APPLIES_TO]->(t:Topic {name: $topic})
RETURN r.id AS id, r.description AS description,
       r.prohibited_keywords AS prohibited_keywords, r.severity AS severity
ORDER BY r.severity DESC
"""

GET_ALL_RULES = """
MATCH (r:Rule)
RETURN r.id AS id, r.description AS description,
       r.prohibited_keywords AS prohibited_keywords, r.severity AS severity
"""

GET_ROLE_PERMISSIONS = """
MATCH (role:Role {name: $role})-[rel]->(action:Action)
RETURN type(rel) AS permission_type, action.name AS action, action.limit AS limit
"""

CHECK_ROLE_CAN_DO = """
MATCH (role:Role {name: $role})-[:CAN_DO]->(action:Action {name: $action})
RETURN count(*) > 0 AS allowed
"""

SEED_RULES = """
// Topics
MERGE (t_approval:Topic {name: "approval"})
MERGE (t_access:Topic {name: "access"})

// Roles
MERGE (manager:Role {name: "manager"})
MERGE (intern:Role {name: "intern"})
MERGE (ceo:Role {name: "ceo"})
MERGE (analyst:Role {name: "analyst"})

// Actions
MERGE (approve_small:Action {name: "approve_request", limit: 10000})
MERGE (approve_unlimited:Action {name: "approve_request", limit: 999999999})
MERGE (view_reports:Action {name: "view_reports"})
MERGE (delete_records:Action {name: "delete_records"})

// Role → Action edges
MERGE (manager)-[:CAN_DO]->(approve_small)
MERGE (manager)-[:CAN_DO]->(view_reports)
MERGE (ceo)-[:CAN_DO]->(approve_unlimited)
MERGE (ceo)-[:CAN_DO]->(delete_records)
MERGE (analyst)-[:CAN_DO]->(view_reports)

// Rules
MERGE (r1:Rule {id: "RULE-001"})
SET r1.description = "Manager can approve requests under $10,000",
    r1.prohibited_keywords = ["intern can approve", "anyone can approve"],
    r1.severity = 1

MERGE (r2:Rule {id: "RULE-002"})
SET r2.description = "Intern cannot approve any requests under any circumstances",
    r2.prohibited_keywords = ["intern can approve", "intern is allowed to approve"],
    r2.severity = 2

MERGE (r3:Rule {id: "RULE-003"})
SET r3.description = "CEO can approve requests of any amount",
    r3.prohibited_keywords = [],
    r3.severity = 1

MERGE (r4:Rule {id: "RULE-004"})
SET r4.description = "Analysts can view reports but cannot approve or delete anything",
    r4.prohibited_keywords = ["analyst can approve", "analyst can delete"],
    r4.severity = 2

MERGE (r5:Rule {id: "RULE-005"})
SET r5.description = "No single employee can both initiate and approve the same request",
    r5.prohibited_keywords = ["can initiate and approve", "same person can approve"],
    r5.severity = 3

// Attach rules to topics
MERGE (r1)-[:APPLIES_TO]->(t_approval)
MERGE (r2)-[:APPLIES_TO]->(t_approval)
MERGE (r3)-[:APPLIES_TO]->(t_approval)
MERGE (r4)-[:APPLIES_TO]->(t_approval)
MERGE (r5)-[:APPLIES_TO]->(t_approval)
MERGE (r4)-[:APPLIES_TO]->(t_access)
"""
```

---

## Phase 2 — FastAPI Skeleton

### 2.1 Pydantic Schemas

**File: `app/models/schemas.py`**

```python
from pydantic import BaseModel, Field
from typing import Optional


class QuestionRequest(BaseModel):
    question: str = Field(..., min_length=5, max_length=500,
                          example="Can an intern approve a $500 expense?")
    topic: Optional[str] = Field(default="approval",
                                  example="approval")


class LLMRawOutput(BaseModel):
    decision: str   # "approve" | "reject" | "unknown"
    reason: str


class ComplianceResponse(BaseModel):
    question: str
    topic: str
    llm_raw_output: dict
    approved: bool
    validation_reason: str
    graph_rules_applied: list[str]
    llm_provider: str


class HealthResponse(BaseModel):
    status: str
    neo4j: str
    llm_provider: str
```

### 2.2 API Routes

**File: `app/api/routes.py`**

```python
import logging
from fastapi import APIRouter, HTTPException, Depends
from app.models.schemas import QuestionRequest, ComplianceResponse, HealthResponse
from app.services.graphrag_service import GraphRAGService
from app.graph.neo4j_client import Neo4jClient

logger = logging.getLogger(__name__)
router = APIRouter()


def get_graphrag_service() -> GraphRAGService:
    # Injected via app state — see main.py
    from app.main import graphrag_service
    return graphrag_service


@router.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check(service: GraphRAGService = Depends(get_graphrag_service)):
    """Check if Neo4j and LLM are reachable."""
    try:
        service.graph.get_all_rules()
        neo4j_status = "connected"
    except Exception:
        neo4j_status = "disconnected"

    return HealthResponse(
        status="ok",
        neo4j=neo4j_status,
        llm_provider=service.llm_provider_name
    )


@router.post("/ask", response_model=ComplianceResponse, tags=["Compliance"])
async def ask_compliance_question(
    request: QuestionRequest,
    service: GraphRAGService = Depends(get_graphrag_service)
):
    """
    Submit a compliance question. Returns approved/rejected with reasoning.
    The LLM generates an answer; the graph validates it deterministically.
    """
    logger.info("Incoming question: %s (topic=%s)", request.question, request.topic)

    try:
        result = service.ask(question=request.question, topic=request.topic)
        return result
    except Exception as e:
        logger.error("Error processing question: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/rules", tags=["Compliance"])
async def list_rules(
    topic: str = "approval",
    service: GraphRAGService = Depends(get_graphrag_service)
):
    """List all rules in the graph for a given topic."""
    rules = service.graph.get_rules_by_topic(topic)
    return {"topic": topic, "rules": rules, "count": len(rules)}
```

### 2.3 Main App Entry Point

**File: `app/main.py`**

```python
import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from dotenv import load_dotenv

from app.api.routes import router
from app.graph.neo4j_client import Neo4jClient
from app.graph.queries import SEED_RULES
from app.services.graphrag_service import GraphRAGService
from app.services.validation_service import ValidationService
from app.core.gemini_adapter import GeminiAdapter
from app.core.groq_adapter import GroqAdapter

load_dotenv()
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)
logger = logging.getLogger(__name__)

# Global service — injected into routes
graphrag_service: GraphRAGService = None


def build_llm_adapter():
    provider = os.getenv("LLM_PROVIDER", "gemini").lower()
    if provider == "gemini":
        return GeminiAdapter(api_key=os.getenv("GEMINI_API_KEY"))
    elif provider == "groq":
        return GroqAdapter(api_key=os.getenv("GROQ_API_KEY"))
    else:
        raise ValueError(f"Unknown LLM_PROVIDER: {provider}. Use 'gemini' or 'groq'.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    global graphrag_service

    logger.info("Starting up GraphRAG Compliance Engine...")

    # 1. Connect to Neo4j
    graph = Neo4jClient(
        uri=os.getenv("NEO4J_URI"),
        user=os.getenv("NEO4J_USER"),
        password=os.getenv("NEO4J_PASSWORD")
    )

    # 2. Seed rules if graph is empty
    existing = graph.get_all_rules()
    if not existing:
        logger.info("No rules found — seeding graph with default compliance rules...")
        graph.run_raw(SEED_RULES)
        logger.info("Graph seeded successfully.")
    else:
        logger.info("Graph already has %d rules.", len(existing))

    # 3. Build LLM adapter
    llm = build_llm_adapter()

    # 4. Build validation service
    validation = ValidationService(graph=graph)

    # 5. Wire everything together
    graphrag_service = GraphRAGService(
        llm=llm,
        graph=graph,
        validation=validation
    )

    logger.info("GraphRAG service ready. LLM provider: %s", os.getenv("LLM_PROVIDER"))
    yield

    # Shutdown
    graph.close()
    logger.info("Neo4j connection closed.")


app = FastAPI(
    title="Deterministic GraphRAG Compliance Engine",
    description="LLM answers compliance questions; Neo4j graph validates the answers deterministically.",
    version="0.1.0-mvp",
    lifespan=lifespan
)

app.include_router(router, prefix="/api/v1")


@app.get("/", tags=["System"])
def root():
    return {
        "name": "GraphRAG Compliance Engine",
        "version": "0.1.0-mvp",
        "docs": "/docs"
    }
```

---

## Phase 3 — LLM Integration

### 3.1 Abstract Interface

**File: `app/core/llm_interface.py`**

```python
from abc import ABC, abstractmethod


class LLMService(ABC):
    """
    Abstract base for all LLM providers.
    Every adapter must implement generate() and return a string.
    The string MUST be valid JSON: {"decision": "...", "reason": "..."}
    """

    @abstractmethod
    def generate(self, prompt: str) -> str:
        raise NotImplementedError

    @property
    @abstractmethod
    def provider_name(self) -> str:
        raise NotImplementedError
```

### 3.2 Google Gemini Adapter (Recommended — Free)

**File: `app/core/gemini_adapter.py`**

```python
import logging
import requests
from app.core.llm_interface import LLMService

logger = logging.getLogger(__name__)

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"


class GeminiAdapter(LLMService):
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("GEMINI_API_KEY is not set.")
        self.api_key = api_key

    @property
    def provider_name(self) -> str:
        return "google-gemini-2.0-flash"

    def generate(self, prompt: str) -> str:
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.1,       # low temp = more deterministic
                "maxOutputTokens": 512,
            }
        }
        try:
            response = requests.post(
                f"{GEMINI_URL}?key={self.api_key}",
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            logger.debug("Gemini raw output: %s", text)
            return text.strip()
        except requests.RequestException as e:
            logger.error("Gemini API call failed: %s", e)
            raise RuntimeError(f"Gemini request failed: {e}")
```

### 3.3 Groq Adapter (Alternative — Free & Fast)

**File: `app/core/groq_adapter.py`**

```python
import logging
import requests
from app.core.llm_interface import LLMService

logger = logging.getLogger(__name__)

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"


class GroqAdapter(LLMService):
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("GROQ_API_KEY is not set.")
        self.api_key = api_key

    @property
    def provider_name(self) -> str:
        return "groq-llama3-8b"

    def generate(self, prompt: str) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "llama3-8b-8192",
            "messages": [
                {
                    "role": "system",
                    "content": "You are a compliance assistant. Always respond with valid JSON only."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.1,
            "max_tokens": 512
        }
        try:
            response = requests.post(GROQ_URL, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            text = response.json()["choices"][0]["message"]["content"]
            logger.debug("Groq raw output: %s", text)
            return text.strip()
        except requests.RequestException as e:
            logger.error("Groq API call failed: %s", e)
            raise RuntimeError(f"Groq request failed: {e}")
```

---

## Phase 4 — GraphRAG Pipeline

### 4.1 Prompt Engineering

The prompt template is critical. It must:
1. Force the LLM to answer ONLY from the provided context
2. Force JSON output
3. Prevent hallucination by being explicit about format

```
SYSTEM ROLE PROMPT (embedded in user message for models without system role):

You are a strict compliance assistant. Your job is to determine whether an
action is allowed or prohibited based ONLY on the rules provided below.

RULES:
{rules_as_numbered_list}

QUESTION:
{question}

INSTRUCTIONS:
- Answer ONLY based on the rules above. Do NOT use any external knowledge.
- If the rules do not address the question, respond with decision: "unknown".
- You MUST respond with valid JSON only. No explanation outside JSON.
- Do NOT add markdown code fences. Return raw JSON.

REQUIRED OUTPUT FORMAT:
{
  "decision": "approve" | "reject" | "unknown",
  "reason": "one sentence explanation referencing the specific rule"
}
```

### 4.2 GraphRAG Service

**File: `app/services/graphrag_service.py`**

```python
import json
import logging
import re
from app.core.llm_interface import LLMService
from app.graph.neo4j_client import Neo4jClient
from app.services.validation_service import ValidationService
from app.models.schemas import ComplianceResponse

logger = logging.getLogger(__name__)

PROMPT_TEMPLATE = """You are a strict compliance assistant.
Your job is to determine whether an action is allowed or prohibited
based ONLY on the rules provided below.

RULES:
{rules}

QUESTION:
{question}

INSTRUCTIONS:
- Answer ONLY based on the rules above. Do NOT use any external knowledge.
- If the rules do not cover the question, use decision: "unknown".
- Respond with valid JSON ONLY. No markdown, no explanation outside JSON.

REQUIRED OUTPUT FORMAT:
{{"decision": "approve" | "reject" | "unknown", "reason": "one sentence citing the rule"}}"""


class GraphRAGService:
    def __init__(self, llm: LLMService, graph: Neo4jClient, validation: ValidationService):
        self.llm = llm
        self.graph = graph
        self.validation = validation

    @property
    def llm_provider_name(self) -> str:
        return self.llm.provider_name

    def _build_context(self, rules: list[dict]) -> str:
        lines = []
        for i, rule in enumerate(rules, 1):
            lines.append(f"{i}. [{rule['id']}] {rule['description']}")
        return "\n".join(lines)

    def _parse_llm_output(self, raw: str) -> dict:
        """
        Parse LLM output to JSON.
        Strips markdown fences if the LLM ignored instructions.
        """
        # Strip ```json ... ``` fences
        cleaned = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`").strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            logger.warning("LLM output could not be parsed as JSON: %s", raw)
            return {"decision": "unknown", "reason": "LLM returned non-JSON output"}

    def ask(self, question: str, topic: str = "approval") -> ComplianceResponse:
        # Step 1: Get context from graph
        rules = self.graph.get_rules_by_topic(topic)
        if not rules:
            rules = self.graph.get_all_rules()

        context = self._build_context(rules)
        rule_ids = [r["id"] for r in rules]

        logger.info("Context built with %d rules for topic '%s'", len(rules), topic)

        # Step 2: Build prompt
        prompt = PROMPT_TEMPLATE.format(rules=context, question=question)

        # Step 3: Call LLM
        raw_output = self.llm.generate(prompt)
        logger.info("LLM OUTPUT: %s", raw_output)

        # Step 4: Parse LLM output
        parsed = self._parse_llm_output(raw_output)

        # Step 5: Validate
        validation_result = self.validation.validate(
            parsed_output=parsed,
            rules=rules,
            raw_llm_output=raw_output
        )

        # Step 6: Return structured response
        return ComplianceResponse(
            question=question,
            topic=topic,
            llm_raw_output=parsed,
            approved=validation_result["approved"],
            validation_reason=validation_result["reason"],
            graph_rules_applied=rule_ids,
            llm_provider=self.llm.provider_name
        )
```

---

## Phase 5 — Validation Layer

This is the **core differentiator** of the system.  
The validation layer is **entirely deterministic** — it never asks the LLM to check itself.

### Validation Logic Flow

```
ValidationService.validate(parsed_output, rules)
        │
        ├─► Check 1: JSON parse valid?
        │       └── Failed? → REJECT (reason: invalid output)
        │
        ├─► Check 2: decision is one of approve/reject/unknown?
        │       └── "unknown" → REJECT (reason: LLM uncertain)
        │
        ├─► Check 3: Keyword scan
        │       └── scan reason + decision for prohibited_keywords from each rule
        │       └── Match found? → REJECT (reason: cites violated rule ID)
        │
        ├─► Check 4: Graph cross-check (role extraction)
        │       └── extract role mentions from LLM reason
        │       └── query graph: can that role do that action?
        │       └── Mismatch? → REJECT
        │
        └─► All checks pass → APPROVE
```

### 5.1 Validation Service

**File: `app/services/validation_service.py`**

```python
import logging
import re
from app.graph.neo4j_client import Neo4jClient

logger = logging.getLogger(__name__)

# Roles known to the system — used for graph cross-check
KNOWN_ROLES = ["intern", "manager", "ceo", "analyst", "director", "employee"]


class ValidationService:
    def __init__(self, graph: Neo4jClient):
        self.graph = graph

    def validate(self, parsed_output: dict, rules: list[dict], raw_llm_output: str) -> dict:
        """
        Run all deterministic validation checks.
        Returns {"approved": bool, "reason": str}
        """
        decision = parsed_output.get("decision", "").lower().strip()
        reason   = parsed_output.get("reason", "").lower().strip()

        # ── Check 1: LLM returned unknown ──────────────────────────────────
        if decision == "unknown":
            result = {"approved": False, "reason": "LLM could not determine compliance from rules."}
            self._log(raw_llm_output, result, "UNCERTAIN")
            return result

        # ── Check 2: Keyword scan against all rules ─────────────────────────
        for rule in rules:
            keywords = rule.get("prohibited_keywords") or []
            for keyword in keywords:
                if keyword.lower() in reason or keyword.lower() in decision:
                    result = {
                        "approved": False,
                        "reason": f"[{rule['id']}] Violation: '{keyword}' contradicts rule: \"{rule['description']}\""
                    }
                    self._log(raw_llm_output, result, "KEYWORD_VIOLATION")
                    return result

        # ── Check 3: Role-action graph cross-check ──────────────────────────
        role = self._extract_role(reason)
        if role:
            allowed = self._graph_check_role(role, action="approve_request")
            if not allowed and decision == "approve":
                result = {
                    "approved": False,
                    "reason": f"Graph check failed: role '{role}' does not have approve_request permission."
                }
                self._log(raw_llm_output, result, "GRAPH_VIOLATION")
                return result

        # ── All checks passed ───────────────────────────────────────────────
        result = {
            "approved": decision == "approve",
            "reason": parsed_output.get("reason", "Validated against graph rules.")
        }
        self._log(raw_llm_output, result, "PASSED")
        return result

    def _extract_role(self, text: str) -> str | None:
        """Try to extract a known role name from LLM reason text."""
        for role in KNOWN_ROLES:
            if role in text.lower():
                return role
        return None

    def _graph_check_role(self, role: str, action: str) -> bool:
        """Query graph to check if a role can perform an action."""
        try:
            from app.graph.queries import CHECK_ROLE_CAN_DO
            results = self.graph.run_raw(
                CHECK_ROLE_CAN_DO,
                {"role": role, "action": action}
            )
            if results:
                return results[0].get("allowed", False)
            return False
        except Exception as e:
            logger.warning("Graph cross-check failed for role='%s': %s", role, e)
            return True  # fail-open if graph unavailable

    def _log(self, raw_output: str, result: dict, status: str):
        approved_str = "PASSED" if result["approved"] else "FAILED"
        logger.info(
            "VALIDATION: %s | STATUS: %s | REASON: %s | LLM_RAW: %s",
            approved_str, status, result["reason"], raw_output[:200]
        )
```

---

## Phase 6 — End-to-End Wiring

### 6.1 `requirements.txt`

```txt
fastapi==0.115.0
uvicorn[standard]==0.30.6
neo4j==5.23.1
pydantic==2.9.2
python-dotenv==1.0.1
requests==2.32.3
```

### 6.2 Full Startup Sequence Verification

When you run `uvicorn app.main:app --reload`, you should see:

```
INFO | app.graph.neo4j_client | Neo4j connection established successfully.
INFO | app.main               | No rules found — seeding graph with default compliance rules...
INFO | app.main               | Graph seeded successfully.
INFO | app.main               | GraphRAG service ready. LLM provider: gemini
INFO | uvicorn.error          | Application startup complete.
```

---

## Phase 7 — Testing & Demo

### 7.1 Manual Test Cases

Run these with `curl` or Postman against `http://localhost:8000`.

#### Test 1: Intern trying to approve → SHOULD REJECT

```bash
curl -X POST http://localhost:8000/api/v1/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "Can an intern approve a $500 expense request?"}'
```

**Expected:**
```json
{
  "approved": false,
  "validation_reason": "[RULE-002] Violation: 'intern can approve' contradicts rule: \"Intern cannot approve any requests\""
}
```

#### Test 2: Manager approving under limit → SHOULD APPROVE

```bash
curl -X POST http://localhost:8000/api/v1/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "Can a manager approve a $5,000 purchase request?"}'
```

**Expected:**
```json
{
  "approved": true,
  "validation_reason": "Manager can approve requests under $10,000 per Rule 1."
}
```

#### Test 3: Manager exceeding limit → SHOULD REJECT

```bash
curl -X POST http://localhost:8000/api/v1/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "Can a manager approve a $50,000 contract?"}'
```

#### Test 4: Same person initiating and approving → SHOULD REJECT

```bash
curl -X POST http://localhost:8000/api/v1/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "Can the same employee who submitted the request also approve it?"}'
```

#### Test 5: List all rules

```bash
curl http://localhost:8000/api/v1/rules?topic=approval
```

#### Test 6: Health check

```bash
curl http://localhost:8000/api/v1/health
```

### 7.2 Expected Validation Logs

```
2025-01-15 10:22:01 | INFO | app.services.graphrag_service   | Context built with 5 rules for topic 'approval'
2025-01-15 10:22:03 | INFO | app.services.graphrag_service   | LLM OUTPUT: {"decision": "approve", "reason": "Intern can approve small requests under $1000"}
2025-01-15 10:22:03 | INFO | app.services.validation_service | VALIDATION: FAILED | STATUS: KEYWORD_VIOLATION | REASON: [RULE-002] Violation: 'intern can approve'...
```

---

## File-by-File Implementation

### Complete File Tree with Status

```
graphrag-lite/
│
├── app/
│   ├── __init__.py                    [empty]
│   ├── main.py                        [Phase 2.3]
│   │
│   ├── api/
│   │   ├── __init__.py                [empty]
│   │   └── routes.py                  [Phase 2.2]
│   │
│   ├── core/
│   │   ├── __init__.py                [empty]
│   │   ├── llm_interface.py           [Phase 3.1]
│   │   ├── gemini_adapter.py          [Phase 3.2]
│   │   └── groq_adapter.py            [Phase 3.3]
│   │
│   ├── graph/
│   │   ├── __init__.py                [empty]
│   │   ├── neo4j_client.py            [Phase 1.1]
│   │   └── queries.py                 [Phase 1.2]
│   │
│   ├── services/
│   │   ├── __init__.py                [empty]
│   │   ├── graphrag_service.py        [Phase 4.2]
│   │   └── validation_service.py      [Phase 5.1]
│   │
│   └── models/
│       ├── __init__.py                [empty]
│       └── schemas.py                 [Phase 2.1]
│
├── data/
│   └── rules.txt                      [human-readable rule reference]
│
├── .env                               [Phase 0.3 — never commit]
├── .env.example                       [Phase 0.3 — commit this]
├── .gitignore
├── requirements.txt                   [Phase 6.1]
└── README.md
```

### `.gitignore`

```gitignore
venv/
__pycache__/
*.pyc
.env
*.egg-info/
.DS_Store
```

### `data/rules.txt` (human-readable reference)

```
COMPLIANCE RULES — GraphRAG Compliance Engine MVP
==================================================

RULE-001 (severity: 1)
  Manager can approve requests under $10,000.
  Prohibited: "intern can approve", "anyone can approve"

RULE-002 (severity: 2)
  Intern cannot approve any requests under any circumstances.
  Prohibited: "intern can approve", "intern is allowed to approve"

RULE-003 (severity: 1)
  CEO can approve requests of any amount.
  Prohibited: none

RULE-004 (severity: 2)
  Analysts can view reports but cannot approve or delete anything.
  Prohibited: "analyst can approve", "analyst can delete"

RULE-005 (severity: 3)
  No single employee can both initiate and approve the same request.
  Prohibited: "can initiate and approve", "same person can approve"
```

---

## Data Seeding (Neo4j Rules)

### Option A — Auto-seed on startup (already in main.py)

The app checks if the graph is empty on startup and runs `SEED_RULES` automatically.

### Option B — Manual seed via Neo4j Browser

1. Open your Neo4j Aura instance in [console.neo4j.io](https://console.neo4j.io)
2. Click "Open with Neo4j Browser"
3. Paste the `SEED_RULES` Cypher from `app/graph/queries.py`
4. Run it

### Option C — Seed script

```python
# scripts/seed.py
import os
from dotenv import load_dotenv
from app.graph.neo4j_client import Neo4jClient
from app.graph.queries import SEED_RULES

load_dotenv()
client = Neo4jClient(
    uri=os.getenv("NEO4J_URI"),
    user=os.getenv("NEO4J_USER"),
    password=os.getenv("NEO4J_PASSWORD")
)
client.run_raw(SEED_RULES)
print("Graph seeded successfully.")
client.close()
```

```bash
python scripts/seed.py
```

---

## Environment Variables Reference

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `LLM_PROVIDER` | Yes | Which LLM to use | `gemini` |
| `GEMINI_API_KEY` | If Gemini | Google AI Studio key | `AIza...` |
| `GROQ_API_KEY` | If Groq | Groq console key | `gsk_...` |
| `NEO4J_URI` | Yes | Aura connection URI | `neo4j+s://xx.databases.neo4j.io` |
| `NEO4J_USER` | Yes | Database user | `neo4j` |
| `NEO4J_PASSWORD` | Yes | Database password | `your_password` |
| `LOG_LEVEL` | No | Logging verbosity | `INFO` |

**Where to get free API keys:**
- Gemini: [ai.google.dev](https://ai.google.dev) → Get API key
- Groq: [console.groq.com](https://console.groq.com) → Create key
- Neo4j Aura: [console.neo4j.io](https://console.neo4j.io) → New instance

---

## Running the Project

### Full startup sequence

```bash
# 1. Clone / enter directory
cd graphrag-lite

# 2. Activate virtualenv
source venv/bin/activate

# 3. Copy .env.example → .env and fill in your keys
cp .env.example .env
# edit .env with your actual keys

# 4. Install dependencies
pip install -r requirements.txt

# 5. Start the server
uvicorn app.main:app --reload --port 8000

# 6. Open API docs
# → http://localhost:8000/docs  (Swagger UI)
# → http://localhost:8000/redoc (ReDoc)
```

---

## MVP Checklist

### Phase 0 — Setup
- [ ] Python virtualenv created
- [ ] All folders and empty files created
- [ ] `.env` filled with real keys
- [ ] Neo4j Aura instance running

### Phase 1 — Graph
- [ ] `neo4j_client.py` connects without error
- [ ] `queries.py` seed runs successfully
- [ ] `/api/v1/rules` returns 5 rules

### Phase 2 — API
- [ ] `uvicorn app.main:app --reload` starts without error
- [ ] `GET /` returns app name
- [ ] `GET /api/v1/health` returns `{"status":"ok","neo4j":"connected",...}`

### Phase 3 — LLM
- [ ] Gemini API key works (`curl` test)
- [ ] `GeminiAdapter.generate()` returns a string
- [ ] Output contains `decision` and `reason`

### Phase 4 — GraphRAG
- [ ] `GraphRAGService.ask()` returns a `ComplianceResponse`
- [ ] Prompt includes all graph rules
- [ ] LLM JSON is parsed without errors

### Phase 5 — Validation
- [ ] Intern approve question → `approved: false`
- [ ] Manager approve under limit → `approved: true`
- [ ] Keyword violation detected and logged
- [ ] Graph cross-check fires for role mismatch

### Phase 6 — Polish
- [ ] All 6 test cases from Phase 7.1 pass
- [ ] Logs are clean and readable
- [ ] `README.md` is updated

---

## Post-MVP Roadmap

### v0.2 — Robustness
- [ ] Add retry logic on LLM timeout
- [ ] Add `/api/v1/rules/{id}` GET + PUT endpoints
- [ ] Add rule creation endpoint (`POST /api/v1/rules`)
- [ ] Structured log output as JSON (for ELK/Datadog)

### v0.3 — Multi-Domain
- [ ] Extend graph schema: HR, Finance, IT-Access domains
- [ ] Topic auto-detection from question (simple keyword match)
- [ ] Rule versioning in Neo4j (`r.version`, `r.effective_from`)

### v0.4 — Production Hardening
- [ ] Dockerize (`Dockerfile` + `docker-compose.yml`)
- [ ] API key authentication middleware
- [ ] Rate limiting
- [ ] `/metrics` endpoint (Prometheus format)

### v1.0 — Enterprise Features
- [ ] Rule management UI (React frontend)
- [ ] Audit trail stored in Neo4j (`AuditLog` node per validation)
- [ ] Multi-LLM consensus (ask 2 models, compare answers)
- [ ] Slack / webhook notifications on violation

---

*Built with FastAPI · Neo4j · Google Gemini · Pure Python Validation*  
*MVP target: 3 days · Zero infrastructure cost · Fully local runnable*
