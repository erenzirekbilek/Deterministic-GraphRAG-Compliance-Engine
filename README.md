# Deterministic GraphRAG Compliance Engine

A **Text-to-Ontology** extraction engine that maps legal/compliance text to a pre-defined schema in Neo4j. The system validates all extractions against the ontology and rejects invalid relationships with "This violates the rule."

## Features

- **Text-to-Ontology Extraction** - Extract entities and relationships from text or PDF documents
- **Deterministic Validation** - All extractions are validated against the ontology schema
- **Rejection of Invalid Relationships** - Invalid relationships are rejected with clear reasons
- **Neo4j Graph Storage** - All extracted data stored in Neo4j for querying
- **Multi-LLM Support** - Works with Groq, Gemini, HuggingFace, and MiniMax
- **Conflict Detection** - Detects conflicts among extracted entities across multiple documents

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Text-to-Ontology Flow                        │
│                                                                 │
│  Input Text/PDF                                                 │
│       │                                                         │
│       ▼                                                         │
│  LLM extracts entities & relationships                         │
│       │                                                         │
│       ▼                                                         │
│  Validation Layer ──► Check against Neo4j ontology             │
│       │                                                         │
│       ├─► Valid?   ──► Store in Neo4j                          │
│       └─► Invalid? ──► Reject with "This violates the rule"     │
└─────────────────────────────────────────────────────────────────┘
```

## Supported LLM Providers

| Provider | Model | Status |
|----------|-------|--------|
| **Groq** | llama-3.3-70b-versatile | ✅ Default |
| **MiniMax** | MiniMax-M2.1 | ✅ |
| **Gemini** | gemini-2.0-flash | ✅ |
| **HuggingFace** | mistralai/Mistral-7B-Instruct-v0.2 | ✅ |

### LLM Adapter Features

- **Retry Mechanism**: Exponential backoff (2s → 4s → 8s) for rate limits
- **JSON Mode**: Forces valid JSON output (Groq)
- **JSON Repair Buffer**: Removes markdown, "Here is the JSON..." text
- **Increased Tokens**: 4096 max_tokens (vs default 512)
- **Strict System Prompts**: No conversational filler

## Ontology Schema

### Entity Types
- **Authority** - A person or role that has power to make decisions
- **Precondition** - A condition that must be satisfied before an action
- **Obligation** - A requirement that a party must fulfill
- **ProhibitedAction** - An action that is explicitly forbidden
- **Condition** - A conditional clause that modifies a rule
- **Party** - A person, organization or role (also: Authority, Role, User, Employee)
- **Action** - An activity or task that can be performed (also: Activity, Task)

### Valid Relationships
- `HAS_AUTHORITY` - Party → Action
- `REQUIRES_PRECONDITION` - Action → Precondition
- `MUST_FULFILL` - Party → Obligation
- `IS_PROHIBITED` - Party/Action → ProhibitedAction
- `DEPENDS_ON` - Condition → Precondition
- `APPLIES_TO` - Obligation/ProhibitedAction → Party

## API Endpoints

### Ontology
- `GET /api/v1/ontology` - Get ontology schema
- `POST /api/v1/extract` - Extract ontology from text
- `POST /api/v1/extract/pdf` - Extract ontology from PDF
- `GET /api/v1/extraction/{document_id}` - Get extraction results

### Compliance
- `POST /api/v1/ask` - Ask compliance questions
- `GET /api/v1/rules` - List rules

### Conflict Detection
- `GET /api/v1/conflicts` - Detect all conflicts
- `GET /api/v1/conflicts/entity/{entity_name}` - Conflicts for specific entity

### System
- `GET /api/v1/health` - Health check
- `GET /` - Root info

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Copy `.env.example` to `.env` and fill in your API keys:

```env
# LLM Provider — choose: groq | minimax | huggingface | gemini
LLM_PROVIDER=groq

# Groq (free at console.groq.com)
GROQ_API_KEY=your_groq_api_key

# MiniMax (free at platform.minimax.io)
MINIMAX_API_KEY=your_minimax_api_key
MINIMAX_MODEL=MiniMax-M2.1

# HuggingFace (free at huggingface.co)
HUGGINGFACE_API_KEY=your_huggingface_api_key

# Google Gemini (free at ai.google.dev)
GEMINI_API_KEY=your_gemini_api_key

# Neo4j Aura Free (console.neo4j.io)
NEO4J_URI=neo4j+s://xxxx.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password
```

### 3. Start Backend

```bash
python -m uvicorn app.main:app --reload --port 8000
```

### 4. Start Frontend

```bash
cd frontend
npm start
```

Open http://localhost:3000

## Usage

### Extract from Text

```bash
curl -X POST http://localhost:8000/api/v1/extract \
  -H "Content-Type: application/json" \
  -d '{
    "text": "The Manager has authority to approve requests up to $10,000. An Intern requires Manager approval for any request."
  }'
```

### Extract from PDF

```bash
curl -X POST http://localhost:8000/api/v1/extract/pdf \
  -F "file=@document.pdf"
```

### Example Text for Testing

```
The manager can approve expense requests up to $10,000. The CFO has authority to approve requests up to $50,000. The CEO can approve any request without limit. Interns cannot approve any requests.
```

### Example Response

```json
{
  "document_id": "doc_1234567890",
  "entities": [
    {"name": "manager", "entity_type": "Party", "mention": "The manager", "confidence": 0.95},
    {"name": "approve expense requests", "entity_type": "Action", "mention": "approve expense requests", "confidence": 0.90},
    {"name": "cfo", "entity_type": "Party", "mention": "The CFO", "confidence": 0.95},
    {"name": "ceo", "entity_type": "Party", "mention": "The CEO", "confidence": 0.95},
    {"name": "interns", "entity_type": "Party", "mention": "Interns", "confidence": 0.95}
  ],
  "relationships": [
    {
      "source": "manager",
      "target": "approve expense requests",
      "relationship": "HAS_AUTHORITY",
      "limit": 10000,
      "justification": "The manager can approve expense requests up to $10,000"
    },
    {
      "source": "cfo",
      "target": "approve expense requests",
      "relationship": "HAS_AUTHORITY",
      "limit": 50000,
      "justification": "The CFO has authority to approve requests up to $50,000"
    },
    {
      "source": "ceo",
      "target": "approve expense requests",
      "relationship": "HAS_AUTHORITY",
      "limit": 0,
      "justification": "The CEO can approve any request without limit"
    },
    {
      "source": "interns",
      "target": "approve expense requests",
      "relationship": "IS_PROHIBITED",
      "justification": "Interns cannot approve any requests"
    }
  ],
  "validation": [
    {"relationship": "HAS_AUTHORITY", "valid": true, "reason": "Valid relationship"}
  ],
  "rejected": [],
  "status": "success"
}
```

## Technology Stack

- **Backend:** FastAPI, Neo4j, Python
- **LLM:** Groq / MiniMax / Google Gemini / HuggingFace
- **Frontend:** React
- **PDF Processing:** pypdf

## Version History

- **v0.2.0** - Text-to-Ontology extraction with validation
  - Multi-LLM support (Groq, MiniMax, Gemini, HuggingFace)
  - Retry mechanism with exponential backoff
  - JSON mode and repair buffer
  - Expanded ontology validation types
  - Conflict detection across documents
