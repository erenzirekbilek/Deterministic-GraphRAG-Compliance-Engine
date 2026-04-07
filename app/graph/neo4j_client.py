import logging
from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable

logger = logging.getLogger(__name__)


class Neo4jClient:
    def __init__(self, uri: str, user: str, password: str):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self._verify_connection()

    def _verify_connection(self):
        try:
            self.driver.verify_connectivity()
            logger.info("Neo4j connection established successfully.")
        except ServiceUnavailable as e:
            logger.error("Could not connect to Neo4j: %s", e)
            raise

    def close(self):
        self.driver.close()

    def get_rules_by_topic(self, topic: str) -> list[dict]:
        """
        Fetch all compliance rules related to a topic.
        Returns list of {id, description, prohibited_keywords, severity}
        """
        query = """
        MATCH (r:Rule)-[:APPLIES_TO]->(t:Topic {name: $topic})
        RETURN r.id          AS id,
               r.description AS description,
               r.prohibited_keywords AS prohibited_keywords,
               r.severity    AS severity
        ORDER BY r.severity DESC
        """
        with self.driver.session() as session:
            results = session.run(query, topic=topic)
            return [dict(record) for record in results]

    def get_all_rules(self) -> list[dict]:
        """Fetch every rule in the graph (used for full context fallback)."""
        query = """
        MATCH (r:Rule)
        RETURN r.id          AS id,
               r.description AS description,
               r.prohibited_keywords AS prohibited_keywords,
               r.severity    AS severity
        ORDER BY r.severity DESC
        """
        with self.driver.session() as session:
            results = session.run(query)
            return [dict(record) for record in results]

    def get_role_permissions(self, role: str) -> list[dict]:
        """Fetch what a specific role can/cannot do."""
        query = """
        MATCH (p:Role {name: $role})-[rel]->(action:Action)
        RETURN type(rel) AS permission_type,
               action.name AS action,
               action.limit AS limit
        """
        with self.driver.session() as session:
            results = session.run(query, role=role)
            return [dict(record) for record in results]

    def run_raw(self, query: str, params: dict = None) -> list[dict]:
        """Execute a raw Cypher query. Use with caution."""
        with self.driver.session() as session:
            results = session.run(query, params or {})
            return [dict(record) for record in results]
