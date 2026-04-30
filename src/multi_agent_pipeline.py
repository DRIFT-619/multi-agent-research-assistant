import os
import re
import json
from typing import TypedDict
from langsmith import traceable
from langgraph.graph import StateGraph

from src.rag_pipeline import llm, rag_query, db
from src.hybrid_pipeline import extract_company, get_company_data, link_risks_to_mitigations
from src.hybrid_pipeline import call_llm, OLLAMA_URL, MODEL

class GraphState(TypedDict):
    question: str
    
    # planner outputs
    decision: str
    reasoning: str
    
    # agent outputs
    rag_context: str
    graph_context: str
    
    # final
    answer: str

def safe_parse_json(text):
    try:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return json.loads(match.group())
    except:
        pass
    return None

@traceable(name="Planner Agent")
def planner_agent(state):
    question = state["question"]

    prompt = f"""
You are a routing agent.

Decide how to answer the question.

Options:
- rag_only
- graph_only
- hybrid

Return ONLY valid JSON.
DO NOT write anything else.

Format:
{{
  "decision": "Placeholder",
  "reason": "Y"
}}

Replace "Placeholder" with any one of the options mentioned above you feel is the best.
Replace "Y" by infering some reasons based on the decision field.

Question:
{question}
"""

    response = call_llm(prompt)

    parsed = safe_parse_json(response)

    if parsed:
        decision = parsed.get("decision", "hybrid")
        reasoning = parsed.get("reason", "")
    else:
        decision = "hybrid"
        reasoning = "Fallback due to parsing error"

    return {
        "decision": decision,
        "reasoning": reasoning
    }

@traceable(name="RAG Agent")
def rag_agent(state):
    if state["decision"] not in ["rag_only", "hybrid"]:
        return {"rag_context": ""}

    question = state["question"]

    answer, docs = rag_query(db, llm, question)

    context = "\n".join([doc.page_content for doc in docs])

    return {
        "rag_context": context
    }

def get_structured_graph_data(company):
    risks, mitigations = get_company_data(company)

    risk_map = link_risks_to_mitigations(risks, mitigations)

    return risk_map

@traceable(name="Graph Agent")
def graph_agent(state):
    if state["decision"] not in ["graph_only", "hybrid"]:
        return {"graph_context": ""}

    question = state["question"]

    company = extract_company(question)

    if not company:
        return {"graph_context": ""}

    risk_map = get_structured_graph_data(company)

    # Convert to structured text
    formatted = ""
    for risk, mitigations in risk_map.items():
        formatted += f"\nRisk: {risk}\n"
        for m in mitigations:
            formatted += f"  - Mitigation: {m}\n"

    return {
        "graph_context": f"Company: {company}\n{formatted}"
    }

@traceable(name="Final Answer Generator")
def final_agent(state):
    question = state["question"]

    rag_context = state.get("rag_context", "")
    graph_context = state.get("graph_context", "")
    reasoning = state.get("reasoning", "")

    prompt = f"""
You are a financial analyst.

Use ONLY the provided data.

STRICT RULES:
1. Do NOT invent mitigations
2. If mitigation is "No direct mitigation found" then:
    - infer a reasonable mitigation from available context
    - or say: "No explicit mitigation mentioned, but likely addressed through..."
    - NEVER say "No mitigation found"
    - Never say generic mitigations like "Enhancing these efforts over time"

3. Do NOT generalize or guess
4. Keep answer structured and precise
5. Use phrases directly grounded in context

Your job:
1. Group risks into high-level categories
2. Use professional financial categories like:
    - Cybersecurity Risk
    - Regulatory Risk
    - Advertising Revenue Risk
    - Product & Innovation Risk
    - Market Competition Risk
3. For each category:
   - summarize the risk
   - list key mitigations
4. DO NOT list raw risks
5. DO NOT say "no mitigation found"
6. Be concise and structured
7. Avoid vague terms like "technology", "brand" unless explicitly mentioned
8. Each summary MUST include specific details from context (e.g., advertising dependency, data privacy laws, cyber attacks)
9. Avoid generic phrases like "risks related to..." or "issues with..."
10. Use concrete business language
11. Avoid repeating the same mitigation across multiple categories unless explicitly stated in context
12. If mitigation is not clearly present, infer carefully or explain absence
13. Each category should have distinct, context-specific mitigations.

Planner Reasoning:
{reasoning}

Graph Data:
{graph_context}

Additional Context:
{rag_context}

Question:
{question}

Answer:
"""

    response = call_llm(prompt)

    return {"answer": response}

def build_app():
    builder = StateGraph(GraphState)

    builder.add_node("planner", planner_agent)
    builder.add_node("rag", rag_agent)
    builder.add_node("graph", graph_agent)
    builder.add_node("final", final_agent)

    # ENTRY
    builder.set_entry_point("planner")

    # FLOW
    builder.add_edge("planner", "rag")
    builder.add_edge("planner", "graph")

    builder.add_edge("rag", "final")
    builder.add_edge("graph", "final")

    return builder.compile()

# Global Compiled App
graph_app = build_app()

def get_answer(question: str):
    result = graph_app.invoke({
        "question": question
    })

    return {
        "decision": result.get("decision"),
        "reasoning": result.get("reasoning"),
        "answer": result.get("answer")
    }

def main():
    question = "What risks does Alphabet face and how do they mitigate them?"

    result = get_answer(question)

    print("Decision:", result["decision"])
    print("Reason:", result["reasoning"])
    print("Answer:\n", result["answer"])

if __name__ == "__main__":
    main()
