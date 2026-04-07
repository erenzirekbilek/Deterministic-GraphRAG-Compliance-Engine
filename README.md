# Deterministic GraphRAG Compliance Engine

A **Text-to-Ontology** extraction engine that maps legal/compliance text to a pre-defined schema in Neo4j. The system validates all extractions against the ontology and rejects invalid relationships with "This violates the rule."

## Features

- **Text-to-Ontology Extraction** - Extract entities and relationships from text or PDF documents
- **Deterministic Validation** - All extractions are validated against the ontology schema
- **Rejection of Invalid Relationships** - Invalid relationships are rejected with clear reasons
- **Neo4j Graph Storage** - All extracted data stored in Neo4j for querying
- **Model-Agnostic** - Supports Google Gemini and Groq LLMs

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

## Ontology Schema

### Entity Types
- **Authority** - A person or role that has power to make decisions
- **Precondition** - A condition that must be satisfied before an action
- **Obligation** - A requirement that a party must fulfill
- **ProhibitedAction** - An action that is explicitly forbidden
- **Condition** - A conditional clause that modifies a rule
- **Party** - A person, organization or role
- **Action** - An activity or task that can be performed

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
LLM_PROVIDER=gemini
GEMINI_API_KEY=your_gemini_api_key
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

### Example Response

```json
{
  "document_id": "abc-123",
  "entities": [
    {"name": "Manager", "entity_type": "Party", "mention": "The Manager", "confidence": 0.95},
    {"name": "approve requests", "entity_type": "Action", "mention": "approve requests", "confidence": 0.90}
  ],
  "relationships": [
    {
      "source": "Manager",
      "target": "approve requests",
      "relationship": "HAS_AUTHORITY",
      "justification": "The Manager has authority to approve requests..."
    }
  ],
  "status": "success"
}
```

## Technology Stack

- **Backend:** FastAPI, Neo4j, Python
- **LLM:** Google Gemini / Groq
- **Frontend:** React
- **PDF Processing:** pypdf

## Version

- v0.2.0 - Text-to-Ontology extraction with validation
