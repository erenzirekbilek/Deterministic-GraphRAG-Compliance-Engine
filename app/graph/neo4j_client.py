import logging
from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable
import uuid
import logging

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

    def save_pending_rule(self, rule_id, rule_type, source_entity, target_entity,
                          description, limit, confidence, source_text, source_document, source_page):
        query = """
        MERGE (r:PendingRule {rule_id: $rule_id})
        SET r.rule_type = $rule_type,
            r.source_entity = $source_entity,
            r.target_entity = $target_entity,
            r.description = $description,
            r.limit = $limit,
            r.confidence = $confidence,
            r.source_text = $source_text,
            r.source_document = $source_document,
            r.source_page = $source_page,
            r.status = 'pending',
            r.created_at = datetime()
        RETURN r.rule_id AS rule_id
        """
        with self.driver.session() as session:
            result = session.run(query, rule_id=rule_id, rule_type=rule_type,
                                 source_entity=source_entity, target_entity=target_entity,
                                 description=description, limit=limit, confidence=confidence,
                                 source_text=source_text, source_document=source_document,
                                 source_page=source_page)
            record = result.single()
            return record["rule_id"] if record else None

    def get_pending_rules(self, document_id=None):
        query = """
        MATCH (r:PendingRule)
        WHERE $document_id IS NULL OR r.source_document = $document_id
        RETURN r.rule_id AS rule_id,
               r.rule_type AS rule_type,
               r.source_entity AS source_entity,
               r.target_entity AS target_entity,
               r.description AS description,
               r.limit AS limit,
               r.confidence AS confidence,
               r.source_text AS source_text,
               r.source_document AS source_document,
               r.source_page AS source_page,
               r.status AS status
        ORDER BY r.created_at DESC
        """
        with self.driver.session() as session:
            results = session.run(query, document_id=document_id)
            return [dict(record) for record in results]

    def update_pending_rule_status(self, rule_id, status):
        query = """
        MATCH (r:PendingRule {rule_id: $rule_id})
        SET r.status = $status
        """
        with self.driver.session() as session:
            session.run(query, rule_id=rule_id, status=status)

    def update_pending_rule_fields(self, rule_id, fields):
        query = """
        MATCH (r:PendingRule {rule_id: $rule_id})
        SET r += $fields
        RETURN r.rule_id AS rule_id
        """
        with self.driver.session() as session:
            result = session.run(query, rule_id=rule_id, fields=fields)
            record = result.single()
            return record["rule_id"] if record else None

    def delete_pending_rule(self, rule_id):
        query = """
        MATCH (r:PendingRule {rule_id: $rule_id})
        DELETE r
        """
        with self.driver.session() as session:
            session.run(query, rule_id=rule_id)

    def get_pending_rules_stats(self):
        query = """
        MATCH (r:PendingRule)
        RETURN count(r) AS total,
               count(CASE WHEN r.status = 'pending' THEN r END) AS pending,
               count(CASE WHEN r.status = 'approved' THEN r END) AS approved,
               count(CASE WHEN r.status = 'rejected' THEN r END) AS rejected,
               collect(DISTINCT r.source_document) AS documents
        """
        with self.driver.session() as session:
            results = session.run(query)
            record = results.single()
            if record:
                return {
                    "total": record["total"],
                    "pending": record["pending"],
                    "approved": record["approved"],
                    "rejected": record["rejected"],
                    "documents": record["documents"]
                }
            return {"total": 0, "pending": 0, "approved": 0, "rejected": 0, "documents": []}

    def _ensure_node_exists(self, label, name, description=""):
        query = f"""
        MERGE (n:{label} {{name: $name}})
        ON CREATE SET n.description = $description, n.created_from = 'rule_management'
        RETURN n.name AS name
        """
        with self.driver.session() as session:
            session.run(query, name=name, description=description)

    def apply_rule_to_graph(self, rule_id, source_name, target_name, rule_type, limit=None):
        query = """
        MATCH (r:PendingRule {rule_id: $rule_id})
        WHERE r.status = 'approved'
        WITH r
        MATCH (source)
        WHERE source.name = $source_name
        WITH source, r
        MATCH (target)
        WHERE target.name = $target_name
        WITH source, target, r
        CALL {
          WITH source, target, r
          WITH source, target, r
          WHERE r.rule_type = 'HAS_AUTHORITY'
          MERGE (source)-[rel:HAS_AUTHORITY {source_document: r.source_document}]->(target)
          SET rel.limit = r.limit, rel.applied_at = datetime()
          RETURN rel
          UNION
          WITH source, target, r
          WITH source, target, r
          WHERE r.rule_type = 'REQUIRES_PRECONDITION'
          MERGE (source)-[rel:REQUIRES_PRECONDITION {source_document: r.source_document}]->(target)
          SET rel.applied_at = datetime()
          RETURN rel
          UNION
          WITH source, target, r
          WITH source, target, r
          WHERE r.rule_type = 'MUST_FULFILL'
          MERGE (source)-[rel:MUST_FULFILL {source_document: r.source_document}]->(target)
          SET rel.applied_at = datetime()
          RETURN rel
          UNION
          WITH source, target, r
          WITH source, target, r
          WHERE r.rule_type = 'IS_PROHIBITED'
          MERGE (source)-[rel:IS_PROHIBITED {source_document: r.source_document}]->(target)
          SET rel.applied_at = datetime()
          RETURN rel
          UNION
          WITH source, target, r
          WITH source, target, r
          WHERE r.rule_type = 'DEPENDS_ON'
          MERGE (source)-[rel:DEPENDS_ON {source_document: r.source_document}]->(target)
          SET rel.applied_at = datetime()
          RETURN rel
          UNION
          WITH source, target, r
          WITH source, target, r
          WHERE r.rule_type = 'APPLIES_TO'
          MERGE (source)-[rel:APPLIES_TO {source_document: r.source_document}]->(target)
          SET rel.applied_at = datetime()
          RETURN rel
        }
        RETURN count(*) AS applied
        """
        with self.driver.session() as session:
            result = session.run(query, rule_id=rule_id, source_name=source_name,
                                 target_name=target_name)
            record = result.single()
            return record["applied"] if record else 0

    def get_all_applied_rules(self):
        query = """
        MATCH (source)-[r]->(target)
        WHERE r.source_document IS NOT NULL
        RETURN source.name AS source,
               type(r) AS rule_type,
               target.name AS target,
               r.limit AS limit,
               r.source_document AS source_document,
               r.applied_at AS applied_at
        ORDER BY r.applied_at DESC
        """
        with self.driver.session() as session:
            results = session.run(query)
            return [dict(record) for record in results]

    def generate_rule_id(self):
        return f"RULE-{uuid.uuid4().hex[:8].upper()}"
