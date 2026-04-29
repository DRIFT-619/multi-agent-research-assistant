import requests
import json
import re

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3"

def extract_entities(text):
    prompt = f"""
You are an expert financial analyst.

Task:
1. Determine if this text contains information about business risks.
2. If YES, extract:
   - company (if mentioned)
   - risks (clear descriptions)
   - mitigation (if mentioned)
   
3. Ignore references to sections, items, or document structure.

5. If NO, return exactly: {{}}

Rules:
- Do NOT guess
- - Do NOT use placeholders like "..." or "N/A" or "" or "Not Explicitly Mentioned" or something similar
- Only extract clearly stated information
- Be concise and accurate

Output format (only include fields that exist):
{{
  "company": "Actual company name",
  "risks": ["Real risk 1", "Real risk 2"],
  "mitigation": ["Real mitigation 1", "Real mitigation 2"]
}}

Text:
{text}
"""
    
    response = requests.post(
        OLLAMA_URL,
        json={
            "model": MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {
            "temperature": 0  # Lower Randomness
        }
        }
    )

    output = response.json()["response"]

    try:
        # Extract JSON block
        match = re.search(r"\{[\s\S]*?\}", output)

        if not match:
            return None

        json_str = match.group()

        return json.loads(json_str)

    except Exception as e:
        print("Parsing error:", e)
        print("Raw output:\n", output)
        return None
