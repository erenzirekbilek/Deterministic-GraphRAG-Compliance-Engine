import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from app.api.routes import router
from app.graph.neo4j_client import Neo4jClient
from app.graph.queries import SEED_RULES
from app.services.graphrag_service import GraphRAGService
from app.services.validation_service import ValidationService
from app.core.gemini_adapter import GeminiAdapter
from app.core.groq_adapter import GroqAdapter

load_dotenv()
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)
logger = logging.getLogger(__name__)

graphrag_service: GraphRAGService = None


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
    global graphrag_service

    logger.info("Starting up GraphRAG Compliance Engine...")

    graph = Neo4jClient(
        uri=os.getenv("NEO4J_URI"),
        user=os.getenv("NEO4J_USER"),
        password=os.getenv("NEO4J_PASSWORD")
    )

    existing = graph.get_all_rules()
    if not existing:
        logger.info("No rules found — seeding graph with default compliance rules...")
        graph.run_raw(SEED_RULES)
        logger.info("Graph seeded successfully.")
    else:
        logger.info("Graph already has %d rules.", len(existing))

    llm = build_llm_adapter()

    validation = ValidationService(graph=graph)

    graphrag_service = GraphRAGService(
        llm=llm,
        graph=graph,
        validation=validation
    )

    logger.info("GraphRAG service ready. LLM provider: %s", os.getenv("LLM_PROVIDER"))
    yield

    graph.close()
    logger.info("Neo4j connection closed.")


app = FastAPI(
    title="Deterministic GraphRAG Compliance Engine",
    description="LLM answers compliance questions; Neo4j graph validates the answers deterministically.",
    version="0.1.0-mvp",
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


@app.get("/", tags=["System"])
def root():
    return {
        "name": "GraphRAG Compliance Engine",
        "version": "0.1.0-mvp",
        "docs": "/docs"
    }
