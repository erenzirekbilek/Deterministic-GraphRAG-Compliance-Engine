# Deterministic GraphRAG Compliance Engine - User Manual

## Quick Overview

This system extracts compliance rules from policy documents and stores them in a Neo4j graph database. It allows you to:
1. **Extract Rules** - Parse text/PDF documents to find compliance rules
2. **Review Rules** - Approve or reject extracted rules
3. **Apply Rules** - Add approved rules to the knowledge base
4. **Query Compliance** - Ask questions like "Can an intern approve $500?"

---

## Tabs Overview

### 1. Compliance Q&A Tab
Ask compliance questions about your extracted rules.
- Example: "Can an intern approve a $500 expense?"
- Shows APPROVED/REJECTED with validation steps

### 2. Text-to-Ontology Tab
Extract entities and relationships from policy text.
- Paste text or upload PDF
- Shows extracted entities, relationships, and validation results

### 3. Conflict Detection Tab
Scans for contradictions in your rules.
- Example: Manager has $10K limit vs $5K limit

### 4. Rule Manager Tab (Main Issue Fixed)
**Extract → Review → Apply workflow:**

1. **Extract Rules**
   - Paste policy text OR upload PDF/DOCX file
   - Click "Extract Rules from Text" or "Upload & Extract"
   - System uses AI to find compliance rules

2. **Review Rules**
   - Rules appear in the table with status "pending"
   - Each rule shows: Type, Source Entity, Target Entity, Limit, Description
   - Actions per rule:
     - ✓ Approve individual rule
     - ✗ Reject individual rule
     - ✎ Edit rule details
     - 🗑 Delete rule
   - Bulk actions at top:
     - "Approve All Pending" - Approves all rules at once
     - "Reject All Pending" - Rejects all rules at once

3. **Apply Rules to Neo4j**
   - After approving rules, click "Apply to Neo4j"
   - This creates the rules in the knowledge base
   - Rules become available for Compliance Q&A

---

## Rule Types Explained

| Type | Meaning | Example |
|------|---------|---------|
| HAS_AUTHORITY | Party can perform action with limits | Manager can approve up to $10,000 |
| IS_PROHIBITED | Party cannot perform action | Interns cannot approve anything |
| MUST_FULFILL | Party must fulfill obligation | All employees must complete training |
| REQUIRES_PRECONDITION | Action requires condition | Expense approval requires receipt |
| DEPENDS_ON | Rule depends on another | Budget approval depends on manager review |
| APPLIES_TO | Policy applies to party | Code of conduct applies to all employees |

---

## How to Use - Step by Step

### Step 1: Extract Rules
1. Go to **Rule Manager** tab
2. In left panel, paste policy text (e.g., "The Manager may approve expenses up to $10,000. Interns require manager approval for all requests.")
3. Click **"Extract Rules from Text"**
4. Wait for extraction to complete

### Step 2: Review Extracted Rules
1. Look at the **Rule Review** table on the right
2. Each rule has status "pending" (yellow)
3. Click **✓** to approve or **✗** to reject
4. Or use **"Approve All Pending"** button at top

### 3. Apply Rules to Knowledge Base
1. Once rules are approved, click **"Apply to Neo4j"**
2. This saves rules to the graph database
3. Now you can ask compliance questions!

### Step 4: Ask Compliance Questions
1. Go to **Compliance Q&A** tab
2. Type: "Can an intern approve a $500 expense?"
3. Click **Submit Question**
4. System responds APPROVED or REJECTED based on rules

---

## Troubleshooting

### "Approve All Pending" not working
- **Fixed**: Now uses correct field name `id` instead of `rule_id`
- Make sure you have pending rules (yellow status)

### No rules extracted
- Check that text contains clear rule statements
- Use explicit language like "can", "must", "prohibited"

### Apply button disabled
- You must have at least one approved rule (green status)
- Click "Apply to Neo4j" to create relationships in database

### Questions always rejected
- Make sure rules are applied to Neo4j first
- Check that party name matches (e.g., "intern" not "interns")

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/extract` | POST | Extract rules from text |
| `/api/v1/extract/pdf` | POST | Extract rules from PDF |
| `/api/v1/pending` | GET | Get all pending rules |
| `/api/v1/review` | POST | Review single rule |
| `/api/v1/review/bulk` | POST | Bulk review rules |
| `/api/v1/apply` | POST | Apply approved rules |
| `/api/v1/ask` | POST | Ask compliance question |

---

## Technical Details

- **Frontend**: React with proxy to `localhost:8000`
- **Backend**: FastAPI
- **Database**: Neo4j
- **AI**: MiniMax/Gemini/Groq/HuggingFace (configurable)
