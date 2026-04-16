import pytest
from unittest.mock import MagicMock, patch
import json


class TestValidationService:
    @pytest.fixture
    def mock_graph(self):
        graph = MagicMock()
        return graph

    @pytest.fixture
    def validation_service(self, mock_graph):
        from app.services.validation_service import ValidationService

        return ValidationService(mock_graph)

    def test_validate_approve_decision(self, validation_service):
        parsed_output = {"decision": "approve", "reason": "manager can approve"}
        rules = [
            {
                "id": "RULE-001",
                "description": "Manager can approve",
                "prohibited_keywords": [],
            }
        ]

        result = validation_service.validate(parsed_output, rules, "{}")

        assert result["approved"] == True

    def test_validate_reject_decision(self, validation_service):
        parsed_output = {"decision": "reject", "reason": "intern cannot approve"}
        rules = [
            {
                "id": "RULE-001",
                "description": "Interns cannot approve",
                "prohibited_keywords": ["intern can approve"],
            }
        ]

        result = validation_service.validate(parsed_output, rules, "{}")

        assert result["approved"] == False

    def test_validate_unknown_decision(self, validation_service):
        parsed_output = {"decision": "unknown", "reason": "not enough information"}
        rules = []

        result = validation_service.validate(parsed_output, rules, "{}")

        assert result["approved"] == False
        assert "could not determine" in result["reason"]

    def test_validate_keyword_violation(self, validation_service):
        parsed_output = {
            "decision": "approve",
            "reason": "intern can approve small amounts",
        }
        rules = [
            {
                "id": "RULE-001",
                "description": "Interns cannot approve",
                "prohibited_keywords": ["intern can approve"],
            }
        ]

        result = validation_service.validate(parsed_output, rules, "{}")

        assert result["approved"] == False
        assert "Violation" in result["reason"]

    def test_extract_role_from_text(self, validation_service):
        assert validation_service._extract_role("manager can approve") == "manager"
        assert validation_service._extract_role("CEO has authority") == "ceo"
        assert validation_service._extract_role("analyst can view") == "analyst"
        assert validation_service._extract_role("no role here") is None
