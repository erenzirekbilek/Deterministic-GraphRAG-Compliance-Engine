import json
import logging
import re
import uuid
from app.core.llm_interface import LLMService
from app.graph.neo4j_client import Neo4jClient

logger = logging.getLogger(__name__)

ONTOLOGY_EXTRACTION_PROMPT = """You are a legal ontology extraction system. Your task is to analyze text from a document and map it to a predefined ontology in Neo4j.

ONTOLOGY ENTITY TYPES:
- Authority: A person or role that has power to make decisions
- Precondition: A condition that must be satisfied before an action
- Obligation: A requirement that a party must fulfill
- ProhibitedAction: An action that is explicitly forbidden
- Condition: A conditional clause that modifies a rule
- Party: A person, organization or role mentioned in the text
- Action: An activity or task that can be performed

VALID RELATIONSHIPS:
- HAS_AUTHORITY: Party → Action (Party has authority to perform action)
- REQUIRES_PRECONDITION: Action → Precondition (Action requires precondition)
- MUST_FULFILL: Party → Obligation (Party must fulfill obligation)
- IS_PROHIBITED: Party/Action → ProhibitedAction (Something is prohibited)
- DEPENDS_ON: Condition → Precondition (Condition depends on precondition)
- APPLIES_TO: Obligation/ProhibitedAction → Party (Rule applies to party)

INSTRUCTIONS:
1. Extract entities (Authority, Precondition, Obligation, ProhibitedAction, Condition, Party, Action) from the text
2. Map relationships between entities based on valid relationship types
3. For each extraction, provide the justification (the exact text that supports it)
4. If you cannot determine an entity or relationship, DO NOT guess - omit it
5. Only use the VALID RELATIONSHIPS listed above

TEXT TO ANALYZE:
{text}

REQUIRED OUTPUT FORMAT (valid JSON only):
{{
  "entities": [
    {{"name": "...", "entity_type": "Authority|Precondition|Obligation|ProhibitedAction|Condition|Party|Action", "mention": "the exact text from document", "confidence": 0.0-1.0}}
  ],
  "relationships": [
    {{"source": "entity name", "target": "entity name", "relationship": "HAS_AUTHORITY|REQUIRES_PRECONDITION|MUST_FULFILL|IS_PROHIBITED|DEPENDS_ON|APPLIES_TO", "justification": "the exact text from document that supports this"}}
  ]
}}

IMPORTANT: If the LLM extracts an incorrect relationship not in the valid list, the system will REJECT it with "This violates the rule." Be precise and only extract what is clearly stated in the text."""


class OntologyExtractionService:
    def __init__(self, llm: LLMService, graph: Neo4jClient):
        self.llm = llm
        self.graph = graph

    def _get_valid_relationships(self) -> list[str]:
        return [
            "HAS_AUTHORITY",
            "REQUIRES_PRECONDITION", 
            "MUST_FULFILL",
            "IS_PROHIBITED",
            "DEPENDS_ON",
            "APPLIES_TO"
        ]

    def _get_valid_entity_types(self) -> list[str]:
        return [
            "Authority",
            "Precondition", 
            "Obligation",
            "ProhibitedAction",
            "Condition",
            "Party",
            "Action"
        ]

    def _validate_relationship(self, relationship: str, source_type: str, target_type: str) -> dict:
        """Check if relationship is valid according to ontology."""
        validation = self.graph.validate_relationship(relationship)
        
        if not validation.get("is_valid", False):
            return {"valid": False, "reason": f"Relationship '{relationship}' is not a valid relationship type in the ontology."}
        
        valid_sources = validation.get("valid_sources", [])
        valid_targets = validation.get("valid_targets", [])
        
        if valid_sources and source_type not in valid_sources:
            return {"valid": False, "reason": f"Source type '{source_type}' is not valid for relationship '{relationship}'. Expected: {valid_sources}"}
        
        if valid_targets and target_type not in valid_targets:
            return {"valid": False, "reason": f"Target type '{target_type}' is not valid for relationship '{relationship}'. Expected: {valid_targets}"}
        
        return {"valid": True, "reason": "Valid relationship"}

    def extract_from_text(self, text: str, document_id: str = None) -> dict:
        """Extract entities and relationships from text using LLM."""
        if not document_id:
            document_id = str(uuid.uuid4())
        
        self.graph.clear_document(document_id)
        
        prompt = ONTOLOGY_EXTRACTION_PROMPT.format(text=text)
        
        raw_output = self.llm.generate(prompt)
        logger.info("LLM extraction output: %s", raw_output[:500])
        
        parsed = self._parse_llm_output(raw_output)
        
        extraction_result = self._save_and_validate(parsed, document_id)
        
        return {
            "document_id": document_id,
            "entities": extraction_result["entities"],
            "relationships": extraction_result["relationships"],
            "validation": extraction_result["validation"],
            "rejected": extraction_result["rejected"]
        }

    def _parse_llm_output(self, raw: str) -> dict:
        """Parse LLM output to JSON."""
        cleaned = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`").strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            logger.error("Failed to parse LLM output as JSON: %s", raw)
            return {"entities": [], "relationships": []}

    def _save_and_validate(self, parsed: dict, document_id: str) -> dict:
        """Save extracted entities/relationships to graph and validate them."""
        valid_rels = self._get_valid_relationships()
        valid_entities = self._get_valid_entity_types()
        
        entities_map = {}
        validation_results = []
        rejected = []
        saved_entities = []
        saved_relationships = []
        
        for entity in parsed.get("entities", []):
            if entity.get("entity_type") in valid_entities:
                self.graph.save_extracted_entity(
                    document_id=document_id,
                    name=entity.get("name", ""),
                    entity_type=entity.get("entity_type", ""),
                    mention=entity.get("mention", ""),
                    confidence=entity.get("confidence", 0.0)
                )
                entities_map[entity.get("name")] = entity.get("entity_type")
                saved_entities.append(entity)
            else:
                rejected.append({
                    "type": "entity",
                    "name": entity.get("name"),
                    "reason": f"Invalid entity type: {entity.get('entity_type')}. This violates the rule."
                })
        
        for rel in parsed.get("relationships", []):
            source = rel.get("source", "")
            target = rel.get("target", "")
            relationship = rel.get("relationship", "")
            justification = rel.get("justification", "")
            
            if relationship not in valid_rels:
                rejected.append({
                    "type": "relationship",
                    "source": source,
                    "target": target,
                    "relationship": relationship,
                    "reason": f"Invalid relationship: '{relationship}'. This violates the rule. Valid relationships: {valid_rels}"
                })
                continue
            
            source_type = entities_map.get(source)
            target_type = entities_map.get(target)
            
            if not source_type or not target_type:
                rejected.append({
                    "type": "relationship",
                    "source": source,
                    "target": target,
                    "relationship": relationship,
                    "reason": "Source or target entity not found in extracted entities."
                })
                continue
            
            validation = self._validate_relationship(relationship, source_type, target_type)
            
            if validation["valid"]:
                self.graph.save_extracted_relationship(
                    document_id=document_id,
                    source=source,
                    target=target,
                    relationship=relationship,
                    justification=justification
                )
                saved_relationships.append(rel)
                validation_results.append({
                    "source": source,
                    "target": target,
                    "relationship": relationship,
                    "is_valid": True,
                    "reason": "Valid according to ontology schema"
                })
            else:
                rejected.append({
                    "type": "relationship",
                    "source": source,
                    "target": target,
                    "relationship": relationship,
                    "reason": f"This violates the rule: {validation['reason']}"
                })
                validation_results.append({
                    "source": source,
                    "target": target,
                    "relationship": relationship,
                    "is_valid": False,
                    "reason": validation["reason"]
                })
        
        return {
            "entities": saved_entities,
            "relationships": saved_relationships,
            "validation": validation_results,
            "rejected": rejected
        }

    def get_document_extraction(self, document_id: str) -> dict:
        """Get all extracted entities and relationships for a document."""
        entities = self.graph.get_document_entities(document_id)
        relationships = self.graph.get_document_relationships(document_id)
        
        return {
            "document_id": document_id,
            "entities": entities,
            "relationships": relationships
        }
