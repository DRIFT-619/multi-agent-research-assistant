import os
import json
from pathlib import Path
from src.rag_pipeline import rag_query, db, llm
from src.multi_agent_pipeline import graph_app

def main():
    questions = [
        "What risks does Alphabet face?",
        "How does Alphabet mitigate cybersecurity risks?",
        "What are the major regulatory risks for Alphabet?",
        "What risks affect Alphabet's advertising business?"
    ]

    eval_data = []

    for q in questions:
        # RAG only
        rag_answer, rag_docs = rag_query(db, llm, q)

        # Hybrid (your multi-agent)
        hybrid_result = graph_app.invoke({"question": q})
        hybrid_answer = hybrid_result["answer"]

        eval_data.append({
            "question": q,
            "rag_answer": rag_answer,
            "hybrid_answer": hybrid_answer,
            "contexts": [doc.page_content for doc in rag_docs],
            "ground_truth": ""
        })

    #  Build path to project root -> data folder
    project_root = Path(__file__).resolve().parent.parent
    data_path = project_root / "eval_data"

    # Create folder if it doesn't exist
    data_path.mkdir(exist_ok=True)

    # Final file path
    file_path = data_path / "eval_dataset.json"

    # Saving
    with open(file_path, "w") as f:
        json.dump(eval_data, f, indent=2)

    print(f"Saved at: {file_path}")

if __name__ == "__main__"():
    main()
