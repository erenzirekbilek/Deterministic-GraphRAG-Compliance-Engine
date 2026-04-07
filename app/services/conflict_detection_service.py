import logging
from app.graph.neo4j_client import Neo4jClient
from app.graph.queries import (
    DETECT_HIERARCHICAL_CONFLICTS,
    DETECT_LIMIT_CONFLICTS,
    DETECT_PROHIBITED_AUTHORIZED_CONFLICTS,
    DETECT_OBLIGATION_CONFLICTS,
    GET_ALL_CONFLICTS
)

logger = logging.getLogger(__name__)


class ConflictDetectionService:
    def __init__(self, graph: Neo4jClient):
        self.graph = graph

    def detect_hierarchical_conflicts(self) -> list[dict]:
        """Detect when multiple parties have authority over the same action."""
        return self.graph.run_raw(DETECT_HIERARCHICAL_CONFLICTS)

    def detect_limit_conflicts(self) -> list[dict]:
        """Detect when same party has different limits for same action."""
        return self.graph.run_raw(DETECT_LIMIT_CONFLICTS)

    def detect_prohibited_authorized_conflicts(self) -> list[dict]:
        """Detect when party has both HAS_AUTHORITY and IS_PROHIBITED."""
        return self.graph.run_raw(DETECT_PROHIBITED_AUTHORIZED_CONFLICTS)

    def detect_obligation_conflicts(self) -> list[dict]:
        """Detect when multiple parties have the same obligation."""
        return self.graph.run_raw(DETECT_OBLIGATION_CONFLICTS)

    def detect_all_conflicts(self) -> dict:
        """Run all conflict detection queries and return categorized results."""
        hierarchical = self.detect_hierarchical_conflicts()
        limits = self.detect_limit_conflicts()
        prohibited = self.detect_prohibited_authorized_conflicts()
        obligations = self.detect_obligation_conflicts()

        all_conflicts = []
        
        for c in hierarchical:
            all_conflicts.append({
                "type": "hierarchical",
                "severity": "critical",
                "message": f"Hierarchical Conflict: '{c.get('party1')}' and '{c.get('party2')}' both have authority over '{c.get('action')}'",
                "details": c
            })

        for c in limits:
            all_conflicts.append({
                "type": "limit",
                "severity": "warning",
                "message": f"Limit Conflict: '{c.get('party')}' has conflicting limits (${c.get('limit1')} vs ${c.get('limit2')}) for '{c.get('action')}'",
                "details": c
            })

        for c in prohibited:
            all_conflicts.append({
                "type": "prohibited",
                "severity": "critical",
                "message": f"Authorization Conflict: '{c.get('party')}' can and cannot perform '{c.get('action')}'",
                "details": c
            })

        for c in obligations:
            all_conflicts.append({
                "type": "obligation",
                "severity": "warning",
                "message": f"Obligation Conflict: '{c.get('party1')}' and '{c.get('party2')}' both have obligation '{c.get('obligation')}'",
                "details": c
            })

        return {
            "total_conflicts": len(all_conflicts),
            "critical": len([c for c in all_conflicts if c["severity"] == "critical"]),
            "warning": len([c for c in all_conflicts if c["severity"] == "warning"]),
            "conflicts": all_conflicts
        }

    def detect_conflicts_for_entity(self, entity_name: str) -> list[dict]:
        """Detect conflicts involving a specific entity."""
        query = """
        MATCH (e:ExtractedEntity {name: $entity_name})-[r]->(target)
        MATCH (e2:ExtractedEntity)-[r2]->(target)
        WHERE type(r) = type(r2) AND e.name <> e2.name
        RETURN e.name AS entity1, e2.name AS conflicting_entity,
               type(r) AS relationship, target.name AS target
        """
        results = self.graph.run_raw(query, {"entity_name": entity_name})
        
        conflicts = []
        for r in results:
            conflicts.append({
                "type": "entity_conflict",
                "severity": "warning",
                "message": f"Entity '{r.get('entity1')}' conflicts with '{r.get('conflicting_entity')}' on '{r.get('relationship')}'",
                "details": r
            })
        
        return conflicts

    def detect_conflicts_for_document(self, document_id: str) -> list[dict]:
        """Detect conflicts involving a specific document."""
        query = """
        MATCH (e1:ExtractedEntity {document_id: $document_id})-[r1]->(e2)
        MATCH (e3:ExtractedEntity)-[r2]->(e4)
        WHERE e1.name = e3.name AND e2.name = e4.name
          AND type(r1) = type(r2)
          AND e1.document_id <> e3.document_id
        RETURN e1.name AS entity, e2.name AS target,
               type(r1) AS relationship,
               e1.document_id AS source_doc,
               e3.document_id AS conflicting_doc
        """
        results = self.graph.run_raw(query, {"document_id": document_id})
        
        conflicts = []
        for r in results:
            conflicts.append({
                "type": "document_conflict",
                "severity": "warning",
                "message": f"Document conflict: '{r.get('source_doc')}' and '{r.get('conflicting_doc')}' have conflicting '{r.get('relationship')}'",
                "details": r
            })
        
        return conflicts

    def check_document_for_conflicts(self, entities: list[dict], relationships: list[dict]) -> dict:
        """Check extracted entities/relationships against existing database for conflicts before saving."""
        conflicts = []
        
        for rel in relationships:
            if rel.get("relationship") == "HAS_AUTHORITY":
                check_query = """
                MATCH (p:ExtractedEntity {name: $party})-[r:HAS_AUTHORITY]->(a:Action {name: $action})
                RETURN p.name AS existing_party, a.name AS existing_action, r.limit AS limit
                """
                existing = self.graph.run_raw(check_query, {
                    "party": rel.get("source"),
                    "action": rel.get("target")
                })
                
                for e in existing:
                    if e.get("existing_party") != rel.get("source"):
                        conflicts.append({
                            "type": "hierarchical",
                            "severity": "critical",
                            "message": f"'{e.get('existing_party')}' already has authority over '{e.get('existing_action')}'. Adding '{rel.get('source')}' would create conflict.",
                            "details": {
                                "existing": e,
                                "proposed": rel
                            }
                        })
            
            if rel.get("relationship") == "IS_PROHIBITED":
                check_query = """
                MATCH (p:ExtractedEntity {name: $party})-[r:HAS_AUTHORITY]->(a:Action {name: $action})
                RETURN p.name AS existing_party, a.name AS existing_action
                """
                existing = self.graph.run_raw(check_query, {
                    "party": rel.get("source"),
                    "action": rel.get("target")
                })
                
                if existing:
                    conflicts.append({
                        "type": "prohibited",
                        "severity": "critical",
                        "message": f"'{rel.get('source')}' already has authority but new extraction says they are prohibited.",
                        "details": {
                            "existing": existing,
                            "proposed": rel
                        }
                    })
        
        return {
            "has_conflicts": len(conflicts) > 0,
            "conflicts": conflicts
        }
