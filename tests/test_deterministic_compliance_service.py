import pytest
from unittest.mock import MagicMock
from app.services.deterministic_compliance_service import DeterministicComplianceService


class TestDeterministicComplianceService:
    @pytest.fixture
    def mock_llm(self):
        llm = MagicMock()
        llm.provider_name = "test-provider"
        return llm

    @pytest.fixture
    def mock_graph(self):
        graph = MagicMock()
        return graph

    @pytest.fixture
    def service(self, mock_llm, mock_graph):
        return DeterministicComplianceService(mock_llm, mock_graph)

    def test_ask_question_approved(self, service, mock_graph):
        mock_graph.run_raw.side_effect = [[{"limit": 10000}], []]

        result = service.ask("Can manager approve $500?")

        assert "question" in result
        assert "llm_raw_output" in result

    def test_ask_question_rejected(self, service, mock_graph):
        mock_graph.run_raw.side_effect = [[{"prohibited_action": "approve_request"}]]

        result = service.ask("Can intern approve $500?")

        assert "question" in result

    def test_ask_question_requires_more_info(self, service, mock_graph):
        pass

    def test_translate_to_human_readable_approved(self, service, mock_llm):
        mock_llm.generate.return_value = '{"decision": "APPROVED", "final_answer": "Manager can approve", "validation_logic": [{"step": "Check", "status": "PASSED", "detail": "OK"}]}'

        deterministic_result = {"deterministic_result": True, "reason": "Has authority"}
        result = service._translate_to_human_readable(
            "Can manager approve?", deterministic_result
        )

        assert "decision" in result

    def test_translate_to_human_readable_rejected(self, service, mock_llm):
        mock_llm.generate.return_value = '{"decision": "REJECTED", "final_answer": "Intern cannot approve", "validation_logic": [{"step": "Check", "status": "FAILED", "detail": "No authority"}]}'

        deterministic_result = {"deterministic_result": False, "reason": "No authority"}
        result = service._translate_to_human_readable(
            "Can intern approve?", deterministic_result
        )

        assert "decision" in result

    def test_translate_to_human_readable_requires_more_info(self, service, mock_llm):
        deterministic_result = {
            "requires_more_info": True,
            "reason": "Could not identify party",
        }
        result = service._translate_to_human_readable(
            "Can someone approve?", deterministic_result
        )

        assert result["decision"] == "unknown"
        assert "Could not identify" in result["reason"]

    def test_parse_llm_output_valid_json(self, service):
        raw = '{"decision": "APPROVED", "final_answer": "OK"}'
        result = service._parse_llm_output(raw)

        assert result["decision"] == "APPROVED"

    def test_parse_llm_output_with_markdown(self, service):
        raw = '```json\n{"decision": "APPROVED"}\n```'
        result = service._parse_llm_output(raw)

        assert result["decision"] == "APPROVED"

    def test_parse_llm_output_invalid_json(self, service):
        raw = "not valid json"
        result = service._parse_llm_output(raw)

        assert result["decision"] == "unknown"

    def test_get_knowledge_summary(self, service, mock_graph):
        mock_graph.run_raw.side_effect = [
            [{"party": "manager"}, {"party": "ceo"}],
            [{"action": "approve_request"}],
        ]

        result = service.get_knowledge_summary()

        assert "parties" in result
        assert "actions" in result
