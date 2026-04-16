import pytest
from unittest.mock import MagicMock, patch
from app.services.rule_extraction_service import RuleExtractionService


class TestRuleExtractionService:
    @pytest.fixture
    def mock_llm(self):
        llm = MagicMock()
        return llm

    @pytest.fixture
    def mock_neo4j(self):
        neo4j = MagicMock()
        neo4j.generate_rule_id.return_value = "RULE-TEST123"
        return neo4j

    @pytest.fixture
    def rule_extraction_service(self, mock_llm, mock_neo4j):
        return RuleExtractionService(mock_llm, mock_neo4j)

    def test_extract_rules_from_text_success(
        self, rule_extraction_service, mock_llm, mock_neo4j
    ):
        mock_llm.generate.return_value = '[{"rule_type": "HAS_AUTHORITY", "source_entity": "manager", "target_entity": "approve_expense", "description": "Manager can approve expenses", "limit": 10000, "confidence": 0.95, "source_text": "Manager can approve expenses up to $10,000"}]'
        mock_neo4j.save_pending_rule.return_value = "RULE-TEST123"

        result = rule_extraction_service.extract_rules_from_text(
            "Manager can approve expenses up to $10,000", "doc-123", "test-doc"
        )

        assert result["rules_extracted"] == 1
        assert result["rules_saved"] == 1
        assert result["document_id"] == "doc-123"
        mock_neo4j.save_pending_rule.assert_called_once()

    def test_extract_rules_from_text_empty_response(
        self, rule_extraction_service, mock_llm
    ):
        mock_llm.generate.return_value = "[]"

        result = rule_extraction_service.extract_rules_from_text("Some text")

        assert result["rules_extracted"] == 0
        assert result["rules_saved"] == 0

    def test_extract_rules_from_text_invalid_json(
        self, rule_extraction_service, mock_llm
    ):
        mock_llm.generate.return_value = "not valid json"

        result = rule_extraction_service.extract_rules_from_text("Some text")

        assert result["rules_extracted"] == 0

    def test_extract_rules_from_text_multiple_rules(
        self, rule_extraction_service, mock_llm, mock_neo4j
    ):
        mock_llm.generate.return_value = """[
            {"rule_type": "HAS_AUTHORITY", "source_entity": "manager", "target_entity": "approve_expense", "description": "Manager can approve", "limit": 10000, "confidence": 0.95, "source_text": "text1"},
            {"rule_type": "IS_PROHIBITED", "source_entity": "intern", "target_entity": "approve", "description": "Interns cannot approve", "limit": null, "confidence": 0.9, "source_text": "text2"}
        ]"""
        mock_neo4j.save_pending_rule.return_value = "RULE-TEST"

        result = rule_extraction_service.extract_rules_from_text("Some policy text")

        assert result["rules_extracted"] == 2
        assert result["rules_saved"] == 2

    def test_review_rule_approve(self, rule_extraction_service, mock_neo4j):
        rule_extraction_service.review_rule("RULE-001", "approved")

        mock_neo4j.update_pending_rule_status.assert_called_with("RULE-001", "approved")

    def test_review_rule_reject(self, rule_extraction_service, mock_neo4j):
        rule_extraction_service.review_rule("RULE-001", "rejected")

        mock_neo4j.update_pending_rule_status.assert_called_with("RULE-001", "rejected")

    def test_review_rule_with_edits(self, rule_extraction_service, mock_neo4j):
        edits = {"limit": 5000, "description": "Updated description"}
        rule_extraction_service.review_rule("RULE-001", "approved", edits)

        mock_neo4j.update_pending_rule_status.assert_called_with("RULE-001", "approved")
        mock_neo4j.update_pending_rule_fields.assert_called_with("RULE-001", edits)

    def test_review_rule_invalid_status(self, rule_extraction_service):
        with pytest.raises(ValueError):
            rule_extraction_service.review_rule("RULE-001", "pending")

    def test_apply_approved_rules_success(self, rule_extraction_service, mock_neo4j):
        mock_neo4j.get_pending_rules.return_value = [
            {
                "rule_id": "RULE-001",
                "source_entity": "manager",
                "target_entity": "approve",
                "rule_type": "HAS_AUTHORITY",
                "limit": 10000,
            },
            {
                "rule_id": "RULE-002",
                "source_entity": "intern",
                "target_entity": "approve",
                "rule_type": "IS_PROHIBITED",
                "limit": None,
            },
        ]
        mock_neo4j.apply_rule_to_graph.return_value = 1

        result = rule_extraction_service.apply_approved_rules()

        assert result["applied"] == 2
        assert result["total_approved"] == 2
        assert result["errors"] == []

    def test_apply_approved_rules_partial_failure(
        self, rule_extraction_service, mock_neo4j
    ):
        mock_neo4j.get_pending_rules.return_value = [
            {
                "rule_id": "RULE-001",
                "source_entity": "manager",
                "target_entity": "approve",
                "rule_type": "HAS_AUTHORITY",
                "limit": 10000,
            }
        ]
        mock_neo4j.apply_rule_to_graph.return_value = 0

        result = rule_extraction_service.apply_approved_rules()

        assert result["applied"] == 0
        assert len(result["errors"]) == 1

    def test_ensure_entity_exists(self, rule_extraction_service, mock_neo4j):
        rule = {"description": "Manager approval"}
        rule_extraction_service._ensure_entity_exists(
            "HAS_AUTHORITY", "source", "manager", rule
        )

        mock_neo4j._ensure_node_exists.assert_called_with(
            "Party", "manager", "Manager approval"
        )

    def test_repair_json_with_markdown(self, rule_extraction_service):
        text = '```json\n[{"key": "value"}]\n```'
        result = rule_extraction_service._repair_json(text)

        assert result == '[{"key": "value"}]'

    def test_repair_json_with_text_prefix(self, rule_extraction_service):
        text = 'Here is the JSON: {"key": "value"}'
        result = rule_extraction_service._repair_json(text)

        assert '{"key": "value"}' in result
