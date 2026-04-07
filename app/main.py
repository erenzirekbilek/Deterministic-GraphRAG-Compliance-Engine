import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from app.api.routes import router
from app.api.pdf_routes import router as pdf_router
from app.graph.neo4j_client import Neo4jClient
from app.graph.queries import SEED_RULES, SEED_ONTOLOGY
from app.services.graphrag_service import GraphRAGService
from app.services.validation_service import ValidationService
from app.services.ontology_extraction_service import OntologyExtractionService
from app.core.gemini_adapter import GeminiAdapter
from app.core.groq_adapter import GroqAdapter

load_dotenv()
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)
logger = logging.getLogger(__name__)

graphrag_service: GraphRAGService = None
ontology_service: OntologyExtractionService = None


def build_llm_adapter():
    provider = os.getenv("LLM_PROVIDER", "gemini").lower()
    if provider == "gemini":
        return GeminiAdapter(api_key=os.getenv("GEMINI_API_KEY"))
    elif provider == "groq":
        return GroqAdapter(api_key=os.getenv("GROQ_API_KEY"))
    else:
        raise ValueError(f"Unknown LLM_PROVIDER: {provider}. Use 'gemini' or 'groq'.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    global graphrag_service, ontology_service

    logger.info("Starting up Deterministic GraphRAG Compliance Engine...")

    graph = Neo4jClient(
        uri=os.getenv("NEO4J_URI"),
        user=os.getenv("NEO4J_USER"),
        password=os.getenv("NEO4J_PASSWORD")
    )

    existing = graph.get_all_rules()
    if not existing:
        logger.info("No rules found — seeding graph with default compliance rules...")
        graph.run_raw(SEED_RULES)
        logger.info("Rules seeded successfully.")
    else:
        logger.info("Graph already has %d rules.", len(existing))

    ontology = graph.get_ontology_schema()
    if not ontology:
        logger.info("No ontology found — seeding ontology schema...")
        graph.run_raw(SEED_ONTOLOGY)
        logger.info("Ontology seeded successfully.")
    else:
        logger.info("Ontology already exists with %d entity types.", len(ontology))

    llm = build_llm_adapter()

    validation = ValidationService(graph=graph)

    graphrag_service = GraphRAGService(
        llm=llm,
        graph=graph,
        validation=validation
    )

    ontology_service = OntologyExtractionService(
        llm=llm,
        graph=graph
    )

    logger.info("GraphRAG service ready. LLM provider: %s", os.getenv("LLM_PROVIDER"))
    logger.info("Ontology extraction service ready.")
    yield

    graph.close()
    logger.info("Neo4j connection closed.")


app = FastAPI(
    title="Deterministic GraphRAG Compliance Engine",
    description="Text-to-Ontology extraction with deterministic validation. "
                "Maps legal/compliance text to pre-defined schema in Neo4j.",
    version="0.2.0-ontology",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api/v1")
app.include_router(pdf_router, prefix="/api/v1")


@app.get("/", tags=["System"])
def root():
    return {
        "name": "Deterministic GraphRAG Compliance Engine",
        "version": "0.2.0-ontology",
        "docs": "/docs",
        "features": [
            "Text-to-Ontology extraction",
            "Entity mapping to schema",
            "Relationship validation against ontology",
            "Rejection of invalid extractions"
        ]
    }
