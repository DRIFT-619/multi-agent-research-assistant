import os
from pathlib import Path
from dotenv import load_dotenv
from neo4j import GraphDatabase

# URI = "bolt://127.0.0.1:7687"
# USERNAME = "neo4j"
# PASSWORD = "multi-agent-assistant"

# driver = GraphDatabase.driver(URI,auth=(USERNAME, PASSWORD))

# Get project root (go one level up from src/)
env_path = Path(__file__).resolve().parent.parent / ".env"

# Load .env file
load_dotenv(dotenv_path=env_path)

# Connect to Neo4j Aura
driver = GraphDatabase.driver(
    os.getenv("NEO4J_URI"),
    auth=(
        os.getenv("NEO4J_USERNAME"),
        os.getenv("NEO4J_PASSWORD")
    )
)

def test_connection():
    with driver.session() as session:
        result = session.run("MATCH (n) RETURN count(n) AS count")
        print("Connection successful")
        print("Node count:", result.single()["count"])

def insert_company_data(data):
    with driver.session() as session:

        # Insert company if present
        if "company" in data and data["company"]:
            session.run(
                """
                MERGE (c:Company {name: $company})
                """,
                company = data["company"]
            )

        # Insert risks if present
        if "risks" in data and data["risks"]:
            session.run(
                """
                MATCH (c:Company {name: $company})
                UNWIND $risks AS risk
                MERGE (r:Risk {name: risk})
                MERGE (c)-[:HAS_RISK]->(r)
                """,
                company = data["company"],
                risks = data["risks"]
            )

        # Insert mitigation if present
        if "mitigation" in data and data["mitigation"]:
            session.run(
                """
                MATCH (c:Company {name: $company})
                UNWIND $mitigation AS m
                MERGE (mit:Mitigation {name: m})
                MERGE (c)-[:MITIGATES_WITH]->(mit)
                """,
                company = data["company"],
                mitigation = data["mitigation"]
            )

        # Sector (optional)
        if "sector" in data and data["sector"]:
            session.run(
                """
                MATCH (c:Company {name: $company})
                MERGE (s:Sector {name: $sector})
                MERGE (c)-[:OPERATES_IN]->(s)
                """,
                company = data["company"],
                sector = data["sector"]
            )

def main():
    test_connection()

if __name__ == "__main__":
    main()