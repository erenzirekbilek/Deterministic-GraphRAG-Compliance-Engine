import pytest
from unittest.mock import MagicMock, patch


class TestNeo4jClientMethods:
    def test_generate_rule_id_format(self):
        with patch('app.graph.neo4j_client.GraphDatabase') as mock_graph:
            mock_driver = MagicMock()
            mock_graph.driver.return_value = mock_driver
            mock_driver.verify_connectivity = MagicMock()
            
            from app.graph.neo4j_client import Neo4jClient
            client = Neo4jClient("bolt://localhost:7687", "neo4j", "password")
            
            rule_id = client.generate_rule_id()
            assert rule_id.startswith("RULE-")
            assert len(rule_id) == 13

    def test_generate_rule_id_unique(self):
        with patch('app.graph.neo4j_client.GraphDatabase') as mock_graph:
            mock_driver = MagicMock()
            mock_graph.driver.return_value = mock_driver
            mock_driver.verify_connectivity = MagicMock()
            
            from app.graph.neo4j_client import Neo4jClient
            client = Neo4jClient("bolt://localhost:7687", "neo4j", "password")
            
            ids = [client.generate_rule_id() for _ in range(100)]
            assert len(set(ids)) == 100
