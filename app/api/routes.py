import logging
from fastapi import APIRouter, HTTPException, Depends
from app.models.schemas import QuestionRequest, ComplianceResponse, HealthResponse
from app.services.graphrag_service import GraphRAGService

logger = logging.getLogger(__name__)
router = APIRouter()


def get_graphrag_service() -> GraphRAGService:
    from app.main import graphrag_service
    return graphrag_service


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
    service: GraphRAGService = Depends(get_graphrag_service)
):
    """
    Submit a compliance question. Returns approved/rejected with reasoning.
    The LLM generates an answer; the graph validates it deterministically.
    """
    logger.info("Incoming question: %s (topic=%s)", request.question, request.topic)

    try:
        result = service.ask(question=request.question, topic=request.topic)
        return result
    except Exception as e:
        logger.error("Error processing question: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/rules", tags=["Compliance"])
async def list_rules(
    topic: str = "approval",
    service: GraphRAGService = Depends(get_graphrag_service)
):
    """List all rules in the graph for a given topic."""
    rules = service.graph.get_rules_by_topic(topic)
    return {"topic": topic, "rules": rules, "count": len(rules)}
