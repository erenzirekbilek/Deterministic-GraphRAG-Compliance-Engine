import os
from dotenv import load_dotenv
from app.graph.neo4j_client import Neo4jClient
from app.graph.queries import SEED_RULES

load_dotenv()
client = Neo4jClient(
    uri=os.getenv("NEO4J_URI"),
    user=os.getenv("NEO4J_USER"),
    password=os.getenv("NEO4J_PASSWORD")
)
client.run_raw(SEED_RULES)
print("Graph seeded successfully.")
client.close()
