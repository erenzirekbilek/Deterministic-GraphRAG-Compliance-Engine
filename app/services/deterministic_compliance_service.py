import logging
from app.core.llm_interface import LLMService
from app.graph.neo4j_client import Neo4jClient
from app.services.deterministic_query_service import DeterministicQueryService
from app.models.schemas import ComplianceResponse

logger = logging.getLogger(__name__)

AUDITOR_SYSTEM_PROMPT = """You are a Deterministic Compliance Auditor. Your mission is not just to answer user queries, but to prove every answer by grounding it in strict Neo4j ontological rules.

CORE RULES:
1. Zero Speculation: Never guess. If a relationship does not exist in the ontology, return 'Data not found.'
2. Step-by-Step Logic: Always break down the answer into 'Validation Steps.'
3. Visual Mapping: Explicitly specify which nodes and edges must be highlighted for visualization.
4. Source Grounding: Extract the exact quote from the document for verification.
5. Strict JSON: Output must strictly follow the defined JSON schema. DO NOT include conversational filler, greetings, or introductory phrases (e.g., 'Sure, I can help with that').

OUTPUT SCHEMA:
{
  "decision": "APPROVED | REJECTED",
  "final_answer": "A natural yet precise and definitive explanation...",
  "validation_logic": [
    { "step": "Authority Check", "status": "PASSED | FAILED", "detail": "..." }
  ],
  "graph_updates": {
    "highlight_nodes": ["entity1", "entity2"],
    "highlight_edges": ["HAS_AUTHORITY"],
    "violation_edge": "IS_PROHIBITED"
  },
  "source_citation": {
    "file": "document.pdf",
    "page": 1,
    "exact_quote": "...",
    "coordinates": [0, 0, 0, 0]
  }
}"""

TRANSLATION_PROMPT = """You are a Deterministic Compliance Auditor.

The system has deterministically computed the following result from the knowledge base:
{deterministic_result}

Question: {question}

CRITICAL: If the decision is REJECTED, you MUST explain WHY in detail. Use these patterns:
- "REJECTED because [specific reason]"
- "REJECTED: [rule ID] - [exact rule description]"
- "FAILED: [entity] does not have [permission] permission"

If APPROVED, explain what rule permitted it.

REQUIRED OUTPUT (valid JSON only):
{{
  "decision": "APPROVED | REJECTED",
  "final_answer": "Clear explanation: APPROVED because... OR REJECTED because...",
  "validation_logic": [
    {{ "step": "Database Lookup", "status": "PASSED | FAILED", "detail": "Found/Unfound [entity] in Neo4j with [permission] permission" }},
    {{ "step": "Permission Check", "status": "PASSED | FAILED", "detail": "Has/Does not have authority based on rule [ID]" }},
    {{ "step": "Limit Validation", "status": "PASSED | FAILED", "detail": "$[amount] is within/exceeds $[limit] limit" }}
  ],
  "graph_updates": {{
    "highlight_nodes": ["entity1", "entity2"],
    "highlight_edges": ["HAS_AUTHORITY"],
    "violation_edge": null
  }},
  "source_citation": {{
    "file": "ontology_rules",
    "page": 1,
    "exact_quote": "[exact rule from Neo4j if available]",
    "coordinates": [0, 0, 0, 0]
  }}
}}

IMPORTANT: 
- For REJECTED: validation_logic must have FAILED steps with specific reasons
- Include dollar amounts, limits, and rule IDs when applicable
- Be deterministic - if graph says NO, output REJECTED"""


class DeterministicComplianceService:
    def __init__(self, llm: LLMService, graph: Neo4jClient):
        self.llm = llm
        self.graph = graph
        self.query_service = DeterministicQueryService(graph)

    def _translate_to_human_readable(self, question: str, deterministic_result: dict) -> dict:
        """Use LLM only to translate the deterministic result to human-readable language."""
        if deterministic_result.get("requires_more_info"):
            return {
                "decision": "unknown",
                "reason": deterministic_result["reason"]
            }
        
        prompt = TRANSLATION_PROMPT.format(
            deterministic_result=str(deterministic_result),
            question=question
        )
        
        try:
            raw_output = self.llm.generate(prompt)
            parsed = self._parse_llm_output(raw_output)
            return parsed
        except Exception as e:
            logger.error("Failed to translate result: %s", str(e))
            fallback_reason = deterministic_result.get("reason", "Deterministic check completed")
            return {
                "decision": "approve" if deterministic_result.get("deterministic_result") else "reject",
                "reason": fallback_reason
            }

    def _parse_llm_output(self, raw: str) -> dict:
        import re
        import json
        cleaned = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`").strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            logger.warning("Could not parse translation: %s", raw)
            return {"decision": "unknown", "reason": "Translation failed"}

    def ask(self, question: str) -> ComplianceResponse:
        """
        Answer compliance question with ABSOLUTE ACCURACY:
        1. First, query Neo4j for deterministic YES/NO
        2. Then, use LLM ONLY to translate to human-readable language
        """
        logger.info("Processing question: %s", question)
        
        deterministic_result = self.query_service.answer_question(question)
        
        logger.info("Deterministic result: %s", deterministic_result)
        
        llm_translation = self._translate_to_human_readable(question, deterministic_result)
        
        is_approved = deterministic_result.get("deterministic_result", False)
        
        return ComplianceResponse(
            question=question,
            topic="deterministic",
            llm_raw_output=llm_translation,
            approved=is_approved,
            validation_reason=deterministic_result.get("reason", ""),
            graph_rules_applied=[deterministic_result.get("query_used", "unknown")],
            llm_provider=self.llm.provider_name
        )

    def get_knowledge_summary(self) -> dict:
        """Get summary of what the system knows."""
        return self.query_service.get_knowledge_base_summary()
