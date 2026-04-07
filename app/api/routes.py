import logging
from fastapi import APIRouter, HTTPException, Depends
from app.models.schemas import (
    QuestionRequest, ComplianceResponse, HealthResponse,
    TextExtractionRequest, OntologyExtractionResponse, OntologySchemaResponse,
    ConflictDetectionResponse
)
from app.services.graphrag_service import GraphRAGService
from app.services.ontology_extraction_service import OntologyExtractionService
from app.services.deterministic_compliance_service import DeterministicComplianceService
from app.services.conflict_detection_service import ConflictDetectionService

logger = logging.getLogger(__name__)
router = APIRouter()


def get_graphrag_service() -> GraphRAGService:
    from app.main import graphrag_service
    return graphrag_service


def get_ontology_service() -> OntologyExtractionService:
    from app.main import ontology_service
    return ontology_service


def get_deterministic_service() -> DeterministicComplianceService:
    from app.main import deterministic_service
    return deterministic_service


def get_conflict_service() -> ConflictDetectionService:
    from app.main import conflict_service
    return conflict_service


@router.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check(service: GraphRAGService = Depends(get_graphrag_service)):
    """Check if Neo4j and LLM are reachable."""
    try:
        service.graph.get_all_rules()
        neo4j_status = "connected"
    except Exception:
        neo4j_status = "disconnected"

    return HealthResponse(
        status="ok",
        neo4j=neo4j_status,
        llm_provider=service.llm_provider_name
    )


@router.post("/ask", response_model=ComplianceResponse, tags=["Compliance"])
async def ask_compliance_question(
    request: QuestionRequest,
    service: DeterministicComplianceService = Depends(get_deterministic_service)
):
    """
    Submit a compliance question. 
    
    DETERMINISTIC MODE: First queries Neo4j for a mathematically definite YES/NO,
    then uses LLM ONLY to translate the result to human-readable language.
    """
    logger.info("Incoming deterministic question: %s", request.question)

    try:
        result = service.ask(question=request.question)
        return result
    except Exception as e:
        logger.error("Error processing question: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/knowledge-base", tags=["Knowledge Base"])
async def get_knowledge_base(
    service: DeterministicComplianceService = Depends(get_deterministic_service)
):
    """Get summary of what the system knows (parties, actions, limits)."""
    try:
        return service.get_knowledge_summary()
    except Exception as e:
        logger.error("Error getting knowledge base: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/rules", tags=["Compliance"])
async def list_rules(
    topic: str = "approval",
    service: GraphRAGService = Depends(get_graphrag_service)
):
    """List all rules in the graph for a given topic."""
    rules = service.graph.get_rules_by_topic(topic)
    return {"topic": topic, "rules": rules, "count": len(rules)}


@router.get("/ontology", response_model=OntologySchemaResponse, tags=["Ontology"])
async def get_ontology_schema(
    service: OntologyExtractionService = Depends(get_ontology_service)
):
    """Get the ontology schema (entity types and relationship types)."""
    entity_types = service.graph.get_ontology_schema()
    relationship_types = service.graph.get_relationship_types()
    
    return OntologySchemaResponse(
        entity_types=entity_types,
        relationship_types=relationship_types
    )


@router.post("/extract", response_model=OntologyExtractionResponse, tags=["Ontology"])
async def extract_ontology(
    request: TextExtractionRequest,
    service: OntologyExtractionService = Depends(get_ontology_service)
):
    """
    Extract entities and relationships from text and map to ontology.
    
    The system will:
    1. Use LLM to extract entities and relationships from the text
    2. Validate each relationship against the ontology schema
    3. Reject any invalid relationships with "This violates the rule."
    4. Store valid extractions in Neo4j
    """
    logger.info("Extracting ontology from text (document_id=%s)", request.document_id)
    
    try:
        result = service.extract_from_text(request.text, request.document_id)
        
        status = "partial" if result.get("rejected") else "success"
        if result.get("rejected"):
            status = "rejected" if not result.get("relationships") else "partial"
        
        return OntologyExtractionResponse(
            document_id=result["document_id"],
            entities=result["entities"],
            relationships=result["relationships"],
            validation=result["validation"],
            rejected=result["rejected"],
            status=status
        )
    except Exception as e:
        logger.error("Error extracting ontology: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/extraction/{document_id}", tags=["Ontology"])
async def get_extraction(
    document_id: str,
    service: OntologyExtractionService = Depends(get_ontology_service)
):
    """Get the extracted ontology for a specific document."""
    try:
        result = service.get_document_extraction(document_id)
        return result
    except Exception as e:
        logger.error("Error getting extraction: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conflicts", response_model=ConflictDetectionResponse, tags=["Conflict Detection"])
async def detect_all_conflicts(
    service: ConflictDetectionService = Depends(get_conflict_service)
):
    """
    Detect all conflicts in the database.
    
    Scans for:
    - Hierarchical conflicts: Multiple parties have authority over same action
    - Limit conflicts: Same party has different limits for same action
    - Prohibited conflicts: Party has both authority and prohibition
    - Obligation conflicts: Multiple parties have same obligation
    """
    try:
        return service.detect_all_conflicts()
    except Exception as e:
        logger.error("Error detecting conflicts: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conflicts/entity/{entity_name}", tags=["Conflict Detection"])
async def detect_entity_conflicts(
    entity_name: str,
    service: ConflictDetectionService = Depends(get_conflict_service)
):
    """Detect conflicts involving a specific entity."""
    try:
        return service.detect_conflicts_for_entity(entity_name)
    except Exception as e:
        logger.error("Error detecting entity conflicts: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conflicts/document/{document_id}", tags=["Conflict Detection"])
async def detect_document_conflicts(
    document_id: str,
    service: ConflictDetectionService = Depends(get_conflict_service)
):
    """Detect conflicts involving a specific document."""
    try:
        return service.detect_conflicts_for_document(document_id)
    except Exception as e:
        logger.error("Error detecting document conflicts: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e))
