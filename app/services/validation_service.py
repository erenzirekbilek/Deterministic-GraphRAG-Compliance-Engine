import logging
import re
from app.graph.neo4j_client import Neo4jClient

logger = logging.getLogger(__name__)

KNOWN_ROLES = ["intern", "manager", "ceo", "analyst", "director", "employee"]


class ValidationService:
    def __init__(self, graph: Neo4jClient):
        self.graph = graph

    def validate(self, parsed_output: dict, rules: list[dict], raw_llm_output: str) -> dict:
        decision = parsed_output.get("decision", "").lower().strip()
        reason = parsed_output.get("reason", "").lower().strip()

        if decision == "unknown":
            result = {"approved": False, "reason": "LLM could not determine compliance from rules."}
            self._log(raw_llm_output, result, "UNCERTAIN")
            return result

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

        result = {
            "approved": decision == "approve",
            "reason": parsed_output.get("reason", "Validated against graph rules.")
        }
        self._log(raw_llm_output, result, "PASSED")
        return result

    def _extract_role(self, text: str):
        for role in KNOWN_ROLES:
            if role in text.lower():
                return role
        return None

    def _graph_check_role(self, role: str, action: str) -> bool:
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
            return True

    def _log(self, raw_output: str, result: dict, status: str):
        approved_str = "PASSED" if result["approved"] else "FAILED"
        logger.info(
            "VALIDATION: %s | STATUS: %s | REASON: %s | LLM_RAW: %s",
            approved_str, status, result["reason"], raw_output[:200]
        )
