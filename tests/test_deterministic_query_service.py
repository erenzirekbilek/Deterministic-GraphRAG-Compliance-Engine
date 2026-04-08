import pytest
from unittest.mock import MagicMock, patch
from app.services.deterministic_query_service import DeterministicQueryService


class TestDeterministicQueryService:
    @pytest.fixture
    def mock_graph(self):
        graph = MagicMock()
        return graph

    @pytest.fixture
    def query_service(self, mock_graph):
        return DeterministicQueryService(mock_graph)

    def test_extract_party_from_question(self, query_service):
        assert query_service.extract_party_from_question("Can an intern approve $500?") == "intern"
        assert query_service.extract_party_from_question("Can the CEO approve this?") == "ceo"
        assert query_service.extract_party_from_question("Can a manager delete records?") == "manager"
        assert query_service.extract_party_from_question("Unknown action here") is None

    def test_extract_action_from_question(self, query_service):
        assert query_service.extract_action_from_question("Can an intern approve $500?") == "approve_request"
        assert query_service.extract_action_from_question("Can manager delete records?") == "delete_records"
        assert query_service.extract_action_from_question("View reports access?") == "view_reports"
        assert query_service.extract_action_from_question("Something else entirely") is None

    def test_extract_amount_from_question(self, query_service):
        assert query_service.extract_amount_from_question("Can an intern approve $500?") == 500.0
        assert query_service.extract_amount_from_question("Can manager approve $10,000?") == 10000.0
        assert query_service.extract_amount_from_question("No amount here") is None

    def test_check_authority_found(self, query_service, mock_graph):
        mock_graph.run_raw.return_value = [{"limit": 1000.0}]
        
        result = query_service.check_authority("manager", "approve_request", 500.0)
        assert result["deterministic_result"] == True
        assert result["limit"] == 1000.0

    def test_check_authority_not_found(self, query_service, mock_graph):
        mock_graph.run_raw.return_value = []
        
        result = query_service.check_authority("intern", "approve_request", 500.0)
        assert result["deterministic_result"] == False
        assert "No authority record found" in result["reason"]

    def test_check_authority_exceeds_limit(self, query_service, mock_graph):
        mock_graph.run_raw.return_value = [{"limit": 1000.0}]
        
        result = query_service.check_authority("manager", "approve_request", 2000.0)
        assert result["deterministic_result"] == False
        assert "exceeds" in result["reason"]

    def test_check_authority_unlimited(self, query_service, mock_graph):
        mock_graph.run_raw.return_value = [{"limit": None}]
        
        result = query_service.check_authority("manager", "approve_request", 500.0)
        assert result["deterministic_result"] == True
        assert result["limit"] is None

    def test_check_prohibited_found(self, query_service, mock_graph):
        mock_graph.run_raw.return_value = [{"prohibited_action": "delete_records", "reason": "policy"}]
        
        result = query_service.check_prohibited("intern", "delete_records")
        assert result["deterministic_result"] == False

    def test_check_prohibited_not_found(self, query_service, mock_graph):
        mock_graph.run_raw.return_value = []
        
        result = query_service.check_prohibited("manager", "approve_request")
        assert result["deterministic_result"] == True

    def test_answer_question_missing_party(self, query_service):
        result = query_service.answer_question("Can someone approve?")
        assert result["deterministic_result"] is None
        assert result["requires_more_info"] == True

    def test_answer_question_missing_action(self, query_service):
        result = query_service.answer_question("Can manager do something?")
        assert result["deterministic_result"] is None
        assert result["requires_more_info"] == True
