import pytest
from unittest.mock import MagicMock
from app.services.conflict_detection_service import ConflictDetectionService


class TestConflictDetectionService:
    @pytest.fixture
    def mock_graph(self):
        graph = MagicMock()
        return graph

    @pytest.fixture
    def conflict_service(self, mock_graph):
        return ConflictDetectionService(mock_graph)

    def test_detect_hierarchical_conflicts(self, conflict_service, mock_graph):
        mock_graph.run_raw.return_value = [
            {"party1": "manager", "party2": "director", "action": "approve_request"}
        ]

        result = conflict_service.detect_hierarchical_conflicts()

        assert len(result) == 1
        mock_graph.run_raw.assert_called_once()

    def test_detect_limit_conflicts(self, conflict_service, mock_graph):
        mock_graph.run_raw.return_value = [
            {
                "party": "manager",
                "action": "approve_request",
                "limit1": 10000,
                "limit2": 5000,
            }
        ]

        result = conflict_service.detect_limit_conflicts()

        assert len(result) == 1

    def test_detect_prohibited_authorized_conflicts(self, conflict_service, mock_graph):
        mock_graph.run_raw.return_value = [
            {
                "party": "intern",
                "action": "approve_request",
                "prohibited_action": "approve",
            }
        ]

        result = conflict_service.detect_prohibited_authorized_conflicts()

        assert len(result) == 1

    def test_detect_obligation_conflicts(self, conflict_service, mock_graph):
        mock_graph.run_raw.return_value = [
            {"party1": "manager", "party2": "cfo", "obligation": "compliance_review"}
        ]

        result = conflict_service.detect_obligation_conflicts()

        assert len(result) == 1

    def test_detect_all_conflicts(self, conflict_service, mock_graph):
        mock_graph.run_raw.side_effect = [
            [{"party1": "manager", "party2": "director", "action": "approve"}],
            [
                {
                    "party": "manager",
                    "action": "approve",
                    "limit1": 10000,
                    "limit2": 5000,
                }
            ],
            [],
            [],
        ]

        result = conflict_service.detect_all_conflicts()

        assert result["total_conflicts"] == 2
        assert result["critical"] == 1
        assert result["warning"] == 1

    def test_detect_all_conflicts_empty(self, conflict_service, mock_graph):
        mock_graph.run_raw.side_effect = [[], [], [], []]

        result = conflict_service.detect_all_conflicts()

        assert result["total_conflicts"] == 0
        assert result["conflicts"] == []

    def test_detect_conflicts_for_entity(self, conflict_service, mock_graph):
        mock_graph.run_raw.return_value = [
            {
                "entity1": "manager",
                "conflicting_entity": "director",
                "relationship": "HAS_AUTHORITY",
                "target": "approve",
            }
        ]

        result = conflict_service.detect_conflicts_for_entity("manager")

        assert len(result) == 1
        assert result[0]["type"] == "entity_conflict"

    def test_detect_conflicts_for_document(self, conflict_service, mock_graph):
        mock_graph.run_raw.return_value = [
            {
                "entity": "manager",
                "target": "approve",
                "relationship": "HAS_AUTHORITY",
                "source_doc": "doc1",
                "conflicting_doc": "doc2",
            }
        ]

        result = conflict_service.detect_conflicts_for_document("doc1")

        assert len(result) == 1

    def test_check_document_for_conflicts_no_conflicts(
        self, conflict_service, mock_graph
    ):
        mock_graph.run_raw.return_value = []

        entities = [{"name": "manager", "entity_type": "Party"}]
        relationships = [
            {
                "source": "manager",
                "target": "approve_request",
                "relationship": "HAS_AUTHORITY",
            }
        ]

        result = conflict_service.check_document_for_conflicts(entities, relationships)

        assert result["has_conflicts"] == False
        assert result["conflicts"] == []

    def test_check_document_for_conflicts_with_conflicts(
        self, conflict_service, mock_graph
    ):
        mock_graph.run_raw.return_value = [
            {"existing_party": "cfo", "existing_action": "approve_request"}
        ]

        entities = [{"name": "manager", "entity_type": "Party"}]
        relationships = [
            {
                "source": "manager",
                "target": "approve_request",
                "relationship": "HAS_AUTHORITY",
            }
        ]

        result = conflict_service.check_document_for_conflicts(entities, relationships)

        assert result["has_conflicts"] == True
        assert len(result["conflicts"]) == 1
