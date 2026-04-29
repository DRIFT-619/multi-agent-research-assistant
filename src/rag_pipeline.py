import os
from langchain_chroma import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from transformers import pipeline

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(PROJECT_ROOT, "chroma_db")

embedding_function = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

db = Chroma(
    # persist_directory=DB_PATH,
    embedding_function=embedding_function
)

# Loading LLM
def load_llm():
    print("\nLoading LLM...")

    llm = pipeline(
        "text2text-generation",
        model="google/flan-t5-base",
        max_length=512,
        temperature=0.2,      # reduces randomness
        repetition_penalty=1.2,
        do_sample=True
    )

    print("LLM Loaded")
    return llm

llm = load_llm()

# MAP Step
def map_step(docs, question, llm):
    summaries = []

    for doc in docs:
        prompt = f"""You are a financial analyst.

Extract ONLY the information relevant to the question.

Rules:
- Do NOT repeat the question
- Keep answer short (1-2 sentences)
- Do NOT generate full explanations
- If nothing relevant, return "NONE"
- Don't return "NONE" unless absolutely nothing relevant exist

Text:
{doc.page_content}

Question:
{question}

Relevant Information:
"""

        response = llm(prompt)
        summary = response[0]['generated_text'].replace(prompt, "").strip()

        if summary != "NONE":
            summaries.append(summary)

    return summaries

# REDUCE Step
def reduce_step(summaries, question, llm):
    combined = "\n".join(summaries)

    prompt = f"""You are a financial analyst.

From the information below, generate a structured final answer.

Rules:
- Provide clear bullet points
- Each bullet must be UNIQUE
- Avoid repetition
- Do NOT repeat the question
- Maximum 6 bullet points

Information:
{combined}

Question:
{question}

Final Answer:
- 
"""

    response = llm(prompt)
    return response[0]['generated_text'].replace(prompt, "").strip()

# RAG Pipeline
def rag_query(db, llm, question):
    retriever = db.as_retriever(search_kwargs={"k": 5})

    docs = retriever.invoke(question)

    summaries = map_step(docs, question, llm)

    final_answer = reduce_step(summaries, question, llm)

    return final_answer, docs

def main():
    # Testing Query
    question = "What are the main risks faced by Tesla?"

    answer, docs = rag_query(db, llm, question)

    print("\n--- ANSWER ---\n")
    print(answer)

    print("\n--- SOURCES ---\n")
    for doc in docs:
        print(doc.metadata)

if __name__ == "__main__":
    main()