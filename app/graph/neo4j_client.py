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

    def get_ontology_schema(self) -> list[dict]:
        """Get all entity types from the ontology."""
        query = """
        MATCH (n:EntityType)
        RETURN n.name AS entity_name, n.description AS description
        ORDER BY n.name
        """
        with self.driver.session() as session:
            results = session.run(query)
            return [dict(record) for record in results]

    def get_relationship_types(self) -> list[dict]:
        """Get all relationship types from the ontology."""
        query = """
        MATCH (r:RelationshipType)
        RETURN r.name AS rel_name, r.source_types AS source_types, 
               r.target_types AS target_types, r.description AS description
        ORDER BY r.rel_name
        """
        with self.driver.session() as session:
            results = session.run(query)
            return [dict(record) for record in results]

    def validate_relationship(self, relationship: str) -> dict:
        """Validate if a relationship type is valid in the ontology."""
        query = """
        MATCH (rt:RelationshipType {name: $relationship})
        RETURN rt.is_valid AS is_valid, rt.source_types AS valid_sources, 
               rt.target_types AS valid_targets
        """
        with self.driver.session() as session:
            results = session.run(query, relationship=relationship)
            record = results.single()
            if record:
                return dict(record)
            return {"is_valid": False, "valid_sources": [], "valid_targets": []}

    def save_extracted_entity(self, document_id: str, name: str, entity_type: str, mention: str, confidence: float):
        """Save an extracted entity to Neo4j."""
        query = """
        MERGE (e:ExtractedEntity {document_id: $document_id, name: $name})
        SET e.entity_type = $entity_type,
            e.mention = $mention,
            e.confidence = $confidence
        """
        with self.driver.session() as session:
            session.run(query, document_id=document_id, name=name, entity_type=entity_type, 
                       mention=mention, confidence=confidence)

    def save_extracted_relationship(self, document_id: str, source: str, target: str, 
                                     relationship: str, justification: str, limit: int = None):
        """Save an extracted relationship to Neo4j."""
        query = """
        MATCH (e1:ExtractedEntity {document_id: $document_id, name: $source})
        MATCH (e2:ExtractedEntity {document_id: $document_id, name: $target})
        MERGE (e1)-[r:EXTRACTED_RELATIONSHIP]->(e2)
        SET r.relationship = $relationship,
            r.justification = $justification,
            r.is_validated = false,
            r.limit = coalesce($limit, 0)
        """
        with self.driver.session() as session:
            session.run(query, document_id=document_id, source=source, target=target,
                       relationship=relationship, justification=justification, limit=limit)

    def get_document_entities(self, document_id: str) -> list[dict]:
        """Get all entities extracted from a document."""
        query = """
        MATCH (e:ExtractedEntity {document_id: $document_id})
        RETURN e.name AS name, e.entity_type AS type, e.mention AS mention, e.confidence AS confidence
        ORDER BY e.entity_type
        """
        with self.driver.session() as session:
            results = session.run(query, document_id=document_id)
            return [dict(record) for record in results]

    def get_document_relationships(self, document_id: str) -> list[dict]:
        """Get all relationships extracted from a document."""
        query = """
        MATCH (e1:ExtractedEntity {document_id: $document_id})-[r:EXTRACTED_RELATIONSHIP]->(e2:ExtractedEntity)
        RETURN e1.name AS source, e2.name AS target, 
               r.relationship AS relationship, r.justification AS justification,
               r.is_validated AS is_validated
        """
        with self.driver.session() as session:
            results = session.run(query, document_id=document_id)
            return [dict(record) for record in results]

    def mark_relationship_validated(self, document_id: str, source: str, target: str, is_valid: bool, reason: str):
        """Mark a relationship as validated with result."""
        query = """
        MATCH (e1:ExtractedEntity {document_id: $document_id, name: $source})-[r:EXTRACTED_RELATIONSHIP]->(e2:ExtractedEntity {name: $target})
        SET r.is_validated = true,
            r.validation_result = $is_valid,
            r.validation_reason = $reason
        """
        with self.driver.session() as session:
            session.run(query, document_id=document_id, source=source, target=target,
                       is_valid=is_valid, reason=reason)

    def clear_document(self, document_id: str):
        """Clear all extracted entities and relationships for a document."""
        query = """
        MATCH (e:ExtractedEntity {document_id: $document_id})
        DETACH DELETE e
        """
        with self.driver.session() as session:
            session.run(query, document_id=document_id)
