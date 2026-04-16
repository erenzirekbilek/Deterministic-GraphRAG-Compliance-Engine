import pytest
from unittest.mock import MagicMock
from app.services.ontology_extraction_service import OntologyExtractionService


class TestOntologyExtractionService:
    @pytest.fixture
    def mock_llm(self):
        llm = MagicMock()
        return llm

    @pytest.fixture
    def mock_graph(self):
        graph = MagicMock()
        graph.validate_relationship.return_value = {
            "is_valid": True,
            "valid_sources": ["Party"],
            "valid_targets": ["Action"],
        }
        return graph

    @pytest.fixture
    def ontology_service(self, mock_llm, mock_graph):
        return OntologyExtractionService(mock_llm, mock_graph)

    def test_extract_from_text_success(self, ontology_service, mock_llm, mock_graph):
        mock_llm.generate.return_value = '{"entities": [{"name": "manager", "entity_type": "Party", "mention": "The manager", "confidence": 0.95}], "relationships": [{"source": "manager", "target": "approve_request", "relationship": "HAS_AUTHORITY", "justification": "Manager has authority"}]}'

        result = ontology_service.extract_from_text(
            "The manager has authority to approve requests"
        )

        assert "document_id" in result
        assert len(result["entities"]) == 1
        assert len(result["relationships"]) == 1

    def test_extract_from_text_invalid_relationship(
        self, ontology_service, mock_llm, mock_graph
    ):
        mock_llm.generate.return_value = '{"entities": [{"name": "manager", "entity_type": "Party", "mention": "The manager", "confidence": 0.95}], "relationships": [{"source": "manager", "target": "something", "relationship": "INVALID_REL", "justification": "test"}]}'

        result = ontology_service.extract_from_text("Test text")

        assert len(result["rejected"]) > 0

    def test_parse_llm_output_valid_json(self, ontology_service):
        raw = '{"entities": [], "relationships": []}'
        result = ontology_service._parse_llm_output(raw)

        assert result == {"entities": [], "relationships": []}

    def test_parse_llm_output_with_markdown(self, ontology_service):
        raw = '```json\n{"entities": [], "relationships": []}\n```'
        result = ontology_service._parse_llm_output(raw)

        assert result == {"entities": [], "relationships": []}

    def test_parse_llm_output_invalid_json(self, ontology_service):
        raw = "not valid json"
        result = ontology_service._parse_llm_output(raw)

        assert result == {"entities": [], "relationships": []}

    def test_get_valid_relationships(self, ontology_service):
        result = ontology_service._get_valid_relationships()

        assert "HAS_AUTHORITY" in result
        assert "IS_PROHIBITED" in result
        assert len(result) == 6

    def test_get_valid_entity_types(self, ontology_service):
        result = ontology_service._get_valid_entity_types()

        assert "Party" in result
        assert "Action" in result
        assert "Authority" in result
        assert len(result) == 7

    def test_validate_relationship_valid(self, ontology_service, mock_graph):
        result = ontology_service._validate_relationship(
            "HAS_AUTHORITY", "Party", "Action"
        )

        assert result["valid"] == True

    def test_validate_relationship_invalid_type(self, ontology_service, mock_graph):
        mock_graph.validate_relationship.return_value = {
            "is_valid": True,
            "valid_sources": ["Party"],
            "valid_targets": ["Action"],
        }

        result = ontology_service._validate_relationship(
            "HAS_AUTHORITY", "InvalidType", "Action"
        )

        assert result["valid"] == False
        assert "not valid" in result["reason"]

    def test_save_and_validate_valid_relationships(self, ontology_service, mock_graph):
        mock_graph.validate_relationship.return_value = {
            "is_valid": True,
            "valid_sources": ["Party"],
            "valid_targets": ["Action"],
        }

        parsed = {
            "entities": [
                {
                    "name": "manager",
                    "entity_type": "Party",
                    "mention": "manager",
                    "confidence": 0.9,
                }
            ],
            "relationships": [
                {
                    "source": "manager",
                    "target": "approve",
                    "relationship": "HAS_AUTHORITY",
                    "justification": "test",
                }
            ],
        }

        result = ontology_service._save_and_validate(parsed, "doc-123")

        assert len(result["entities"]) == 1
        assert len(result["relationships"]) == 1

    def test_save_and_validate_invalid_entity_type(self, ontology_service, mock_graph):
        parsed = {
            "entities": [
                {
                    "name": "unknown",
                    "entity_type": "InvalidType",
                    "mention": "test",
                    "confidence": 0.9,
                }
            ],
            "relationships": [],
        }

        result = ontology_service._save_and_validate(parsed, "doc-123")

        assert len(result["rejected"]) == 1

    def test_get_document_extraction(self, ontology_service, mock_graph):
        mock_graph.get_document_entities.return_value = [
            {"name": "manager", "entity_type": "Party"}
        ]
        mock_graph.get_document_relationships.return_value = [
            {"source": "manager", "target": "approve", "relationship": "HAS_AUTHORITY"}
        ]

        result = ontology_service.get_document_extraction("doc-123")

        assert len(result["entities"]) == 1
        assert len(result["relationships"]) == 1
