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
        cleaned = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`").strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            logger.warning("LLM output could not be parsed as JSON: %s", raw)
            return {"decision": "unknown", "reason": "LLM returned non-JSON output"}

    def ask(self, question: str, topic: str = "approval") -> ComplianceResponse:
        rules = self.graph.get_rules_by_topic(topic)
        if not rules:
            rules = self.graph.get_all_rules()

        context = self._build_context(rules)
        rule_ids = [r["id"] for r in rules]

        logger.info("Context built with %d rules for topic '%s'", len(rules), topic)

        prompt = PROMPT_TEMPLATE.format(rules=context, question=question)

        raw_output = self.llm.generate(prompt)
        logger.info("LLM OUTPUT: %s", raw_output)

        parsed = self._parse_llm_output(raw_output)

        validation_result = self.validation.validate(
            parsed_output=parsed,
            rules=rules,
            raw_llm_output=raw_output
        )

        return ComplianceResponse(
            question=question,
            topic=topic,
            llm_raw_output=parsed,
            approved=validation_result["approved"],
            validation_reason=validation_result["reason"],
            graph_rules_applied=rule_ids,
            llm_provider=self.llm.provider_name
        )
