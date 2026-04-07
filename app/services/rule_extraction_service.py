import json
import logging
import time
from app.graph.neo4j_client import Neo4jClient
from app.core.llm_interface import LLMService

logger = logging.getLogger(__name__)

RULE_EXTRACTION_PROMPT = """You are a deterministic compliance rule extraction engine. Your task is to extract structured compliance rules from policy documents, contracts, SOPs, or regulatory texts.

Extract rules that define:
- WHO can do WHAT (authority/permissions)
- What is PROHIBITED
- What MUST be fulfilled (obligations)
- What CONDITIONS must be met (preconditions)
- What DEPENDENCIES exist between rules

VALID RULE TYPES (use ONLY these):
1. HAS_AUTHORITY - Party/role can perform an action (e.g., "Manager can approve expenses up to $10,000")
2. IS_PROHIBITED - Party/role cannot perform an action (e.g., "Interns cannot approve any requests")
3. MUST_FULFILL - Party/role must fulfill an obligation (e.g., "All employees must complete security training")
4. REQUIRES_PRECONDITION - Action requires a condition (e.g., "Expense approval requires manager sign-off")
5. DEPENDS_ON - Rule/condition depends on another (e.g., "Budget approval depends on department head review")
6. APPLIES_TO - Policy/obligation applies to a party (e.g., "Code of conduct applies to all employees")

EXTRACTION RULES:
- source_entity: The party, role, or entity that has the authority/obligation/prohibition
- target_entity: The action, obligation, or thing being authorized/prohibited/required
- limit: For HAS_AUTHORITY rules, extract the monetary or numeric limit (use 0 for unlimited, null if not specified)
- confidence: 0.0-1.0 based on how clear and unambiguous the rule is in the text
- source_text: The EXACT sentence or phrase from the document that contains this rule

REQUIRED OUTPUT (valid JSON array only):
[
  {{
    "rule_type": "HAS_AUTHORITY",
    "source_entity": "manager",
    "target_entity": "approve_expense",
    "description": "Manager can approve expenses up to $10,000",
    "limit": 10000,
    "confidence": 0.95,
    "source_text": "The manager may approve expense requests up to $10,000."
  }}
]

IMPORTANT:
- Return ONLY a valid JSON array, no markdown, no explanations
- Each rule must have ALL fields present
- rule_type must be one of the 6 valid types listed above
- Normalize entity names to lowercase_snake_case (e.g., "department_manager" not "Department Manager")
- For HAS_AUTHORITY: limit should be a number (0 for unlimited, null if not specified)
- Be exhaustive - extract every rule you can find
- If the text contains no extractable rules, return an empty array []

Document text:
{text}
"""


class RuleExtractionService:
    def __init__(self, llm: LLMService, neo4j: Neo4jClient):
        self.llm = llm
        self.neo4j = neo4j

    def extract_rules_from_text(self, text: str, document_id: str = None, document_name: str = None):
        start_time = time.time()
        doc_id = document_id or f"rule-doc-{int(time.time())}"
        doc_name = document_name or doc_id

        prompt = RULE_EXTRACTION_PROMPT.format(text=text)
        raw_output = self.llm.generate(prompt)

        try:
            rules_data = self._repair_json(raw_output)
            rules_list = json.loads(rules_data)
            if not isinstance(rules_list, list):
                rules_list = [rules_list]
        except (json.JSONDecodeError, TypeError) as e:
            logger.error("Failed to parse LLM rule extraction output: %s", e)
            rules_list = []

        saved_rules = []
        for rule_data in rules_list:
            rule_id = self.neo4j.generate_rule_id()
            rule_type = rule_data.get("rule_type", "HAS_AUTHORITY")
            source_entity = rule_data.get("source_entity", "unknown")
            target_entity = rule_data.get("target_entity", "unknown")
            description = rule_data.get("description", "")
            limit = rule_data.get("limit")
            confidence = rule_data.get("confidence", 0.5)
            source_text = rule_data.get("source_text", "")

            saved_id = self.neo4j.save_pending_rule(
                rule_id=rule_id,
                rule_type=rule_type,
                source_entity=source_entity,
                target_entity=target_entity,
                description=description,
                limit=limit,
                confidence=confidence,
                source_text=source_text,
                source_document=doc_name,
                source_page=None
            )

            saved_rules.append({
                "rule_id": saved_id or rule_id,
                "rule_type": rule_type,
                "source_entity": source_entity,
                "target_entity": target_entity,
                "description": description,
                "limit": limit,
                "confidence": confidence,
                "source_text": source_text,
                "source_document": doc_name,
                "source_page": None,
                "status": "pending"
            })

        latency = round((time.time() - start_time) * 1000, 2)

        return {
            "document_id": doc_id,
            "document_name": doc_name,
            "rules_extracted": len(rules_list),
            "rules_saved": len(saved_rules),
            "rules": saved_rules,
            "latency_ms": latency
        }

    def review_rule(self, rule_id: str, status: str, edits: dict = None):
        if status not in ("approved", "rejected"):
            raise ValueError("status must be 'approved' or 'rejected'")

        self.neo4j.update_pending_rule_status(rule_id, status)

        if edits:
            self.neo4j.update_pending_rule_fields(rule_id, edits)

        return {"rule_id": rule_id, "status": status, "edits_applied": edits is not None}

    def apply_approved_rules(self, document_id: str = None):
        rules = self.neo4j.get_pending_rules(document_id)
        approved_rules = [r for r in rules if r["status"] == "approved"]

        applied = 0
        errors = []

        for rule in approved_rules:
            try:
                source_name = rule["source_entity"]
                target_name = rule["target_entity"]
                rule_type = rule["rule_type"]

                self._ensure_entity_exists(rule_type, "source", source_name, rule)
                self._ensure_entity_exists(rule_type, "target", target_name, rule)

                result = self.neo4j.apply_rule_to_graph(
                    rule_id=rule["rule_id"],
                    source_name=source_name,
                    target_name=target_name,
                    rule_type=rule_type,
                    limit=rule.get("limit")
                )

                if result and result > 0:
                    applied += 1
                else:
                    errors.append(f"Rule {rule['rule_id']}: Could not create relationship (entities may not exist)")
            except Exception as e:
                errors.append(f"Rule {rule['rule_id']}: {str(e)}")

        return {
            "applied": applied,
            "total_approved": len(approved_rules),
            "errors": errors
        }

    def _ensure_entity_exists(self, rule_type, side, name, rule):
        mapping = {
            "HAS_AUTHORITY": {"source": "Party", "target": "Action"},
            "IS_PROHIBITED": {"source": "Party", "target": "ProhibitedAction"},
            "MUST_FULFILL": {"source": "Party", "target": "Obligation"},
            "REQUIRES_PRECONDITION": {"source": "Action", "target": "Precondition"},
            "DEPENDS_ON": {"source": "Condition", "target": "Precondition"},
            "APPLIES_TO": {"source": "Obligation", "target": "Party"},
        }

        type_map = mapping.get(rule_type, {"source": "Party", "target": "Action"})
        label = type_map.get(side, "Party")
        desc = rule.get("description", "")

        self.neo4j._ensure_node_exists(label, name, desc)

    def _repair_json(self, text: str) -> str:
        text = text.strip()
        if text.startswith("```"):
            text = text.split("```", 1)[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.rsplit("```", 1)[0]
        text = text.strip()
        start = text.find("[")
        end = text.rfind("]")
        if start != -1 and end != -1:
            return text[start:end + 1]
        return text
