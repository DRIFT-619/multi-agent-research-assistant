import os
from src.entity_extractor import extract_entities
from src.graph_db import insert_company_data
from src.ingestion import load_all_pdfs, chunk_documents

def normalize_data(data):
    ticker_map = {
                "alphabet inc.": "Alphabet",
                "alphabet inc": "Alphabet",
                "Alphabet Inc.": "Alphabet",
                "Alphabet Inc": "Alphabet",
                "GOOGL": "Alphabet",
                "GOOGLE": "Alphabet",
                "Google": "Alphabet",
                "goog": "Alphabet",
                "googl": "Alphabet",
                "google (goog)": "Alphabet",
                "goog (google)": "Alphabet",
                "Google Services": "Alphabet",
                "Alphabet (Waymo, Isomorphic Labs Are Subsidiaries)": "Alphabet",
                "Waymo": "Alphabet",
                "AAPL": "Apple",
                "MSFT": "Microsoft"
        }

    # Normalize company
    if "company" in data:
        company = data.get("company")
    
        if isinstance(company, list):
            if len(company) > 0:
                company = company[0]
            else:
                company = None
        
        if isinstance(company, str):
            if company in ticker_map:
                data["company"] = ticker_map[company]
            else:
                data["company"] = data["company"].title()
        else:
            data["company"] = None

    # Normalize sector
    if "sector" in data:
        data["sector"] = data["sector"].title()

    # Normalize risks
    normalized_risks = []
    if "risks" in data:
        for r in data["risks"]:
            r = r.lower()
    
            if "regulatory" in r:
                normalized_risks.append("Regulatory Risk")
            elif "supply" in r:
                normalized_risks.append("Supply Chain Disruption")
            elif "competition" in r:
                normalized_risks.append("Market Competition")
            else:
                normalized_risks.append(r.title())

    data["risks"] = list(set(normalized_risks))  # removing duplicates

    return data

def get_company_from_metadata(chunk):
    source = chunk.metadata.get("source", "").lower()

    if "alphabet" in source:
        return "Alphabet"
    elif "amazon" in source:
        return "Amazon"
    elif "apple" in source:
        return "Apple"
    elif "tesla" in source:
        return "Tesla"
    else:
        return "Microsoft"
    
    return None

def process_chunk(chunk, idx):
    text = chunk.page_content

    print(f"\nProcessing chunk {idx}...\n")

    data = extract_entities(text)

    if not data:
        print("Not relevant\n")
        return

    # Ensuring company exists
    if not data.get("company"):
        data["company"] = get_company_from_metadata(chunk)

    if data:
        data = normalize_data(data)
        print(data)
        insert_company_data(data)
        print("Inserted\n")
    else:
        print("No relevant information found\n")

def process_chunks_in_batches(chunks, batch_size = 50):
    # total = len(chunks)
    total = 50 # For Testing

    for i in range(0, total, batch_size):
        batch = chunks[i:i+batch_size]

        print(f"\nProcessing batch {i} to {i+batch_size-1}\n")

        for j, chunk in enumerate(batch):
            process_chunk(chunk, i + j)
            time.sleep(1)   # Prevents overload

        print("Batch complete\n")

def link_risk_mitigation(company):
    with driver.session() as session:
        data = session.run("""
        MATCH (c:Company {name: $company})
        OPTIONAL MATCH (c)-[:HAS_RISK]->(r:Risk)
        OPTIONAL MATCH (c)-[:MITIGATES_WITH]->(m:Mitigation)
        
        RETURN collect(DISTINCT r.name) AS risks,
               collect(DISTINCT m.name) AS mitigations
        """, company=company).single()

    risks = data["risks"]
    mitigations = data["mitigations"]

    for risk in risks:
        for mitigation in mitigations:

            # simple keyword overlap logic
            if any(word in mitigation.lower() for word in risk.lower().split()):
                with driver.session() as session:
                    session.run("""
                    MATCH (r:Risk {name: $risk})
                    MATCH (m:Mitigation {name: $mitigation})
                    MERGE (r)-[:MITIGATED_BY]->(m)
                    """, risk=risk, mitigation=mitigation)
'''
if __name__ == "__main__":
    # Get project root
    current_dir = os.path.dirname(__file__)
    project_root = os.path.abspath(os.path.join(current_dir, "../"))

    data_path = os.path.join(project_root, "data")

    print("Loading data...")
    docs = load_all_pdfs(data_path)

    print("Chunking...")
    chunks = chunk_documents(docs)

    process_chunks_in_batches(chunks, batch_size = 50)

    companies = ["Alphabet","Apple","Amazon","Microsoft","Tesla"]

    for i in companies:
        link_risk_mitigation(i)

'''