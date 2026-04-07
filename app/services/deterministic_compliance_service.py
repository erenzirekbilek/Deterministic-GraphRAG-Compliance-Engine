import logging
from app.core.llm_interface import LLMService
from app.graph.neo4j_client import Neo4jClient
from app.services.deterministic_query_service import DeterministicQueryService
from app.models.schemas import ComplianceResponse

logger = logging.getLogger(__name__)

TRANSLATION_PROMPT = """You are a compliance answer translator. 

The system has deterministically computed the following result from the knowledge base:
{deterministic_result}

Question: {question}

Your task is to translate this technical result into a human-readable response.
- If YES (deterministic_result = true): Confirm the action is allowed with the reason
- If NO (deterministic_result = false): Explain why the action is not allowed
- If UNKNOWN: Explain what information is missing

Respond ONLY with this JSON format:
{{"decision": "approve|reject|unknown", "reason": "human-readable explanation"}}
"""


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
