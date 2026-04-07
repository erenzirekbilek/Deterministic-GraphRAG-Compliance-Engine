# Deterministic GraphRAG Compliance Engine

## 🎯 Aim of the Project

The **Deterministic GraphRAG Compliance Engine** addresses a critical problem in AI-powered compliance: **hallucination and lack of verification**.

### The Problem

Traditional RAG (Retrieval-Augmented Generation) systems suffer from:
- **AI Hallucinations** - Models generate plausible but false information
- **No Quality Control** - Invalid or fabricated relationships slip through
- **Black Box Decisions** - Users can't verify why AI made certain conclusions
- **Inconsistent Results** - Same input produces different outputs

### Our Solution

This project provides a **verification-first approach** to compliance:

1. **Extract Only What's Valid** - AI extracts entities/relationships from text, but they're validated against a strict Neo4j ontology schema before storage

2. **Reject Invalid Data** - If a relationship doesn't exist in the ontology, it's rejected with "This violates the rule" - not silently accepted

3. **Show Your Work** - Every decision includes validation steps, source citations, and graph highlights - making AI decisions transparent and auditable

4. **Detect Conflicts** - When the same entity has conflicting rules across documents, the system flags them automatically

### Core Mission

> **To build trust in AI for compliance by making every extraction deterministic, verifiable, and auditable.**

### Target Users

| User | Use Case |
|------|----------|
| **Compliance Officers** | Verify policies don't violate regulations |
| **Legal Teams** | Extract authority hierarchies from contracts |
| **Risk Managers** | Identify prohibited actions across documents |
| **Auditors** | Document review with proof of extraction |

### Value Proposition

| Traditional RAG | Our System |
|----------------|------------|
| Returns anything relevant | Returns only **validated** facts |
| "Maybe" answers | "Yes/No" with **proof** |
| No explanation | **Step-by-step** validation shown |
| Unverifiable | **Source citations** for every claim |
| Single document | **Conflict detection** across documents |

### Key Differentiators

✅ **Deterministic Validation** - Rules first, then extraction
✅ **Rejection, Not Acceptance** - Invalid data is rejected, not tolerated  
✅ **Visual Verification** - See exactly what AI extracted and why
✅ **Graph-Native Storage** - Relationships stored in Neo4j for queries
✅ **Multi-LLM** - Switch providers without changing code
✅ **Conflict Detection** - Automatic contradiction detection

---

## Recent Changes

### 🎨 Professional UI Redesign
- Complete CSS overhaul with **Inter font**
- Modern dark theme with deep navy background
- Purple primary accents with cyan highlights
- Smooth animations and glass-morphism effects
- Improved cards, buttons, and form elements
- Enhanced Ontology Canvas with better node styling

### 🔄 Multi-LLM Support Improvements
- **Retry Mechanism**: Exponential backoff (2s → 4s → 8s) for rate limits
- **JSON Mode**: Forces valid JSON output (Groq)
- **JSON Repair Buffer**: Removes markdown and filler text
- **Increased Tokens**: 4096 max_tokens for complete JSON output

### 🎯 Enhanced Compliance Auditor
- **Auditor Persona**: Strict system prompt for deterministic answers
- **Structured JSON Output**: decision, final_answer, validation_logic, graph_updates, source_citation
- **Step-by-Step Validation**: Visual validation steps with pass/fail icons
- **Graph Highlights**: Animated node and edge highlighting
- **Source Citations**: Quote display with visual feedback

### 🖼️ Ontology Canvas (Real-time Visualization)
- Animated nodes with spring bounce effect using **Framer Motion**
- SVG laser line connections between related entities
- Red glow + shake animation for prohibited actions
- Color-coded nodes by entity type
- Interactive hover effects

## Features

- **Text-to-Ontology Extraction** - Extract entities and relationships from text or PDF documents
- **Deterministic Validation** - All extractions validated against Neo4j ontology schema
- **Rejection of Invalid Relationships** - Invalid relationships rejected with clear reasons
- **Neo4j Graph Storage** - All extracted data stored in Neo4j for querying
- **Multi-LLM Support** - Works with Groq, Gemini, HuggingFace, and MiniMax
- **Conflict Detection** - Detects conflicts among extracted entities across documents
- **Visual Verification** - Step-by-step validation with graph highlights
- **Source Citations** - Exact quotes from source documents

## Technical Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Backend** | FastAPI | High-performance Python API |
| **Database** | Neo4j Aura | Graph storage for ontology |
| **LLM** | Groq/MiniMax/Gemini | Entity/relationship extraction |
| **Frontend** | React + Tailwind | User interface |
| **Animations** | Framer Motion | Smooth UI transitions |
| **PDF** | pypdf | Document parsing |

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
- **Frontend:** React + Tailwind CSS + Framer Motion
- **PDF Processing:** pypdf

## Version History

- **v0.3.0** - Professional UI & Canvas (Current)
  - Professional UI redesign with modern dark theme
  - Ontology Canvas with animated nodes and laser connections
  - Framer Motion for smooth animations
  - Tailwind CSS configuration
  - Enhanced Auditor persona with structured output
  - Validation steps display with animated icons
  - Graph highlights and source citations

- **v0.2.0** - Text-to-Ontology extraction with validation
  - Multi-LLM support (Groq, MiniMax, Gemini, HuggingFace)
  - Retry mechanism with exponential backoff
  - JSON mode and repair buffer
  - Expanded ontology validation types
  - Conflict detection across documents

## Contributing

Contributions are welcome! Here's how you can help:

### Development Setup

```bash
# Clone the repository
git clone https://github.com/erenzirekbilek/Deterministic-GraphRAG-Compliance-Engine.git
cd Deterministic-GraphRAG-Compliance-Engine

# Install backend dependencies
pip install -r requirements.txt

# Install frontend dependencies
cd frontend
npm install
```

### Adding New LLM Providers

1. Create a new adapter in `app/core/`
2. Implement the `LLMService` interface
3. Add provider selection in `app/main.py`
4. Update `.env` with provider configuration

### Adding New Features

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes
4. Commit with descriptive messages: `git commit -m 'Add amazing feature'`
5. Push to the branch: `git push origin feature/amazing-feature`
6. Open a Pull Request

### Code Style

- **Python**: Follow PEP 8, use type hints
- **JavaScript/React**: Use functional components with hooks
- **CSS**: Use Tailwind utility classes when possible

### Reporting Issues

Please report bugs and feature requests via [GitHub Issues](https://github.com/erenzirekbilek/Deterministic-GraphRAG-Compliance-Engine/issues).

## License

This project is licensed under the MIT License.
