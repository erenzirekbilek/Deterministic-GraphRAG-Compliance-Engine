import os
from dotenv import load_dotenv
from app.graph.neo4j_client import Neo4jClient

load_dotenv()

client = Neo4jClient(
    uri=os.getenv("NEO4J_URI"),
    user=os.getenv("NEO4J_USER"),
    password=os.getenv("NEO4J_PASSWORD")
)

# Null-safe SEED_RULES
SAFE_SEED_RULES = """
// Roles
MERGE (ceo:Role {name:'ceo'})
MERGE (manager:Role {name:'manager'})
MERGE (employee:Role {name:'employee'})

// Actions
MERGE (approve_request:Action {name:'approve_request'})
MERGE (submit_report:Action {name:'submit_report'})

// Null-safe relationship creation
MERGE (ceo)-[:HAS_AUTHORITY {limit: 0}]->(approve_request)
MERGE (manager)-[:HAS_AUTHORITY {limit: 10}]->(submit_report)
MERGE (employee)-[:HAS_AUTHORITY {limit: 1}]->(submit_report)

// Example Parties (to prevent missing label warnings)
MERGE (default_party:Party {name:'Default Party'})

// Example EntityTypes
MERGE (et1:EntityType {name:'Contract', description:'Legal contract entity'})
MERGE (et2:EntityType {name:'Invoice', description:'Financial invoice entity'})
"""

# Seed the graph
client.run_raw(SAFE_SEED_RULES)

print("Graph seeded successfully.")
client.close()