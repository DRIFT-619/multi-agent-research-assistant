import os
import re
import requests
from pathlib import Path
from dotenv import load_dotenv
from neo4j import GraphDatabase
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.cluster import AgglomerativeClustering

from src.rag_pipeline import llm, db

embedding_model = SentenceTransformer("all-MiniLM-L6-v2", local_files_only=True)

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

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3"

def call_llm(prompt):
    response = requests.post(
        OLLAMA_URL,
        json={
            "model": MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0   # deterministic output
            }
        }
    )

    return response.json()["response"]

def extract_company(query, context=None, llm=None):
    if llm:
        prompt = f"""
    Extract the company name from the query.
    
    Query: {query}
    Context: {context}
    
    Return ONLY the company name.
    If not found, return: None
    """
    
        response = call_llm(prompt)
        company = response.strip()
    
        return company if company != "None" else None
    else:
        companies = ["Alphabet", "Google", "Microsoft", "Tesla", "Apple", "Amazon"]
        
        for c in companies:
            if c.lower() in query.lower():
                # normalize Google → Alphabet
                if "google" in c.lower():
                    return "Alphabet"
                return c

def get_company_data(company_name):
    with driver.session() as session:
        result = session.run("""
        MATCH (c:Company {name: $company})
        OPTIONAL MATCH (c)-[:HAS_RISK]->(r:Risk)
        OPTIONAL MATCH (c)-[:MITIGATES_WITH]->(m:Mitigation)
        
        RETURN collect(DISTINCT r.name) AS risks,
               collect(DISTINCT m.name) AS mitigations
        """, company=company_name)

        data = result.single()
        return data["risks"], data["mitigations"]
    
def filter_by_query(items, query, threshold=0.4):
    if not items:
        return []

    query_emb = embedding_model.encode([query])
    item_embs = embedding_model.encode(items)

    sims = cosine_similarity(query_emb, item_embs)[0]

    filtered = [
        item for item, sim in zip(items, sims)
        if sim > threshold
    ]

    return filtered

def clean_text(text):
    if not text:
        return None

    text = text.strip().lower()

    # Remove junk phrases
    junk_patterns = [
        "not explicitly mentioned",
        "none explicitly mentioned",
        "those discussed",
        "part i",
        "item",
        "see",
    ]

    for pattern in junk_patterns:
        if pattern in text:
            return None

    # Remove very long noisy sentences
    if len(text.split()) > 20:
        return None

    # Remove special chars
    text = re.sub(r"[^a-zA-Z0-9\s]", "", text)

    return text.strip()

def clean_list(items):
    cleaned = []

    for item in items:
        text = clean_text(item)
        if text:
            cleaned.append(text)

    return list(set(cleaned))  # remove duplicates

def deduplicate(items, embedding_model, threshold=0.85):
    if not items:
        return []

    embeddings = embedding_model.encode(items)
    unique_items = []

    for i, item in enumerate(items):
        is_duplicate = False

        for j, u_item in enumerate(unique_items):
            sim = cosine_similarity(
                [embeddings[i]],
                [embedding_model.encode(u_item)]
            )[0][0]

            if sim > threshold:
                is_duplicate = True
                break

        if not is_duplicate:
            unique_items.append(item)

    return unique_items

def group_items(items, embedding_model, similarity_threshold=0.75):
    if len(items) <= 1:
        return {items[0]: items} if items else {}

    embeddings = embedding_model.encode(items)

    clustering = AgglomerativeClustering(
        n_clusters=None,
        distance_threshold=1 - similarity_threshold,
        metric='cosine',
        linkage='average'
    )

    labels = clustering.fit_predict(embeddings)

    grouped = {}

    for label, item in zip(labels, items):
        if label not in grouped:
            grouped[label] = []
        grouped[label].append(item)

    # Convert to readable format
    final_groups = {}

    for group in grouped.values():
        representative = group[0]  # pick first as label
        final_groups[representative] = group

    return final_groups

def process_items(items):
    cleaned = clean_list(items)
    deduped = deduplicate(cleaned, embedding_model)
    grouped = group_items(deduped, embedding_model)
    return grouped

def link_risks_to_mitigations(risks, mitigations, threshold=0.3):
    if not risks or not mitigations:
        return {}

    risk_embs = embedding_model.encode(risks)
    mit_embs = embedding_model.encode(mitigations)

    links = {}

    for i, risk in enumerate(risks):
        similarities = cosine_similarity(
            [risk_embs[i]],
            mit_embs
        )[0]

        matched = [
            mitigations[j]
            for j, sim in enumerate(similarities)
            if sim > threshold
        ]

        # Explicit fallback (NO hallucination later)
        if not matched:
            matched = ["No direct mitigation found"]

        links[risk] = matched

    return links

def link_grouped_risks(risk_groups, mitigation_list):

    final_links = {}

    for group_name, risk_list in risk_groups.items():
        links = link_risks_to_mitigations(risk_list, mitigation_list)
        final_links[group_name] = links

    return final_links

def retrieve_chunks(query, k=3):
    results = db.similarity_search(query, k=k)
    return [doc.page_content for doc in results]

def generate_answer(query, company, context, linked_data):

    structured_text = ""

    for group, risks in linked_data.items():
        structured_text += f"\n### {group}\n"
        for risk, mits in risks.items():
            structured_text += f"- Risk: {risk}\n"
            structured_text += f"  Mitigation: {', '.join(mits) if mits else 'Not specified'}\n"

    prompt = f"""
You are a financial analyst.

Query:
{query}

Company:
{company}

Context:
{context}

Structured Risk-Mitigation Mapping:
{structured_text}

Task:
- Explain risks clearly
- For EACH risk, explain its mitigation
- Do NOT generalize
- Keep mapping accurate
"""

    return call_llm(prompt)

def hybrid_rag_pipeline(query):

    # Retrieving chunks
    chunks = retrieve_chunks(query)
    context = "\n".join(chunks)

    # Extracting company
    company = extract_company(query, context, llm)

    if not company:
        return "Company not found in query."

    # Getting graph data
    risks, mitigations = get_company_data(company)

    # Filtering by query
    risks = filter_by_query(risks, query)
    mitigations = filter_by_query(mitigations, query)

    # Processing
    risk_groups = process_items(risks)
    mitigation_groups = process_items(mitigations)

    # Linking Risk to Mitigation
    linked_data = link_grouped_risks(
        risk_groups,
        mitigations
    )
    
    # Generating answer
    answer = generate_answer(
        query,
        company,
        context,
        linked_data
    )

    return answer

def main():
    query = "What cybersecurity risks does Alphabet face and how do they mitigate them?"

    result = hybrid_rag_pipeline(query)
    print(result)

if __name__ == "__main__":
    main()
