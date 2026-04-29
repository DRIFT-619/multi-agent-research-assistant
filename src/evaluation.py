import json
import os
import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer

from src.hybrid_pipeline import call_llm, OLLAMA_URL, MODEL

model = SentenceTransformer("all-MiniLM-L6-v2")

def generate_ground_truth(question, contexts):
    prompt = f"""
You are a financial analyst.

Based ONLY on the context below, write a concise and correct answer.

Context:
{contexts}

Question:
{question}

Answer:
"""

    return call_llm(prompt)

def context_relevance(question, contexts):
    q_emb = model.encode(question)
    ctx_embs = model.encode(contexts)
    
    sims = cosine_similarity([q_emb], ctx_embs)[0]
    return float(np.mean(sims))

def answer_relevance(question, answer):
    q_emb = model.encode(question)
    a_emb = model.encode(answer)
    
    sim = cosine_similarity([q_emb], [a_emb])[0][0]
    return float(sim)

def groundedness(answer, contexts):
    a_emb = model.encode(answer)
    ctx_embs = model.encode(contexts)
    
    sims = cosine_similarity([a_emb], ctx_embs)[0]
    return float(np.max(sims))  # best supporting chunk

def evaluate_system(data, answer_key):
    results = []
    
    for item in data:
        q = item["question"]
        contexts = item["contexts"]
        ans = item[answer_key]
        
        results.append({
            "context_score": context_relevance(q, contexts),
            "answer_score": answer_relevance(q, ans),
            "groundedness": groundedness(ans, contexts)
        })
    
    return results

def average_scores(scores):
    return {
        "context": np.mean([s["context_score"] for s in scores]),
        "answer": np.mean([s["answer_score"] for s in scores]),
        "groundedness": np.mean([s["groundedness"] for s in scores])
    }

def main():
    # Get project root dynamically
    current_dir = os.path.dirname(__file__)
    project_root = os.path.abspath(os.path.join(current_dir, "../"))

    data_path = os.path.join(project_root, "eval_data/eval_dataset.json")
    
    with open(data_path) as f:
        data = json.load(f)

    for item in data:
        if not item["ground_truth"]:
            item["ground_truth"] = generate_ground_truth(
                item["question"],
                "\n".join(item["contexts"])
            )

    rag_scores = evaluate_system(data, "rag_answer")
    hybrid_scores = evaluate_system(data, "hybrid_answer")

    rag_avg = average_scores(rag_scores)
    hybrid_avg = average_scores(hybrid_scores)

    print("RAG:", rag_avg)
    print("HYBRID:", hybrid_avg)

if __name__ == "__main__":
    main()
