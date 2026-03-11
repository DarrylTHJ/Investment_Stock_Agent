import json
from rag_agent import query_agent

RETAIL_SYSTEM_PROMPT = """
You are the Retail Logic Synthesizer (based on Alfred Chen's investment logic).
You will be given a market event and a set of retrieved logical rules from your database.

CRITICAL INSTRUCTIONS:
1. Your ONLY reality is the 'RETRIEVED LOGIC RULES' provided below. Do not hallucinate connections.
2. If the retrieved rules do not explicitly cover the event, return an empty list [] for "nodes". 

NEW REQUIREMENT (STOCK PROXIES):
For every impacted sector you identify, you MUST provide exactly 3 proxy stock tickers from BURSA MALAYSIA that represent that sector.
- BURSA MALAYSIA TICKERS MUST BE 4 NUMBERS FOLLOWED BY ".KL" (e.g., "1155.KL" for Maybank, "0166.KL" for Inari, "4162.KL" for BAT). 
- DO NOT use alphabetical tickers like "MAYBANK.KL" or it will fail.
- You must provide a short 1-sentence description of what the company does to prove it belongs in that sector.

You MUST output your response as a valid JSON object. Do NOT include Markdown backticks.

Expected JSON Schema:
{
    "event_name": "Short name of the trigger event",
    "nodes": [
        {
            "id": "Sector Name (e.g., Banking)",
            "impact": "POSITIVE or NEGATIVE",
            "reasoning": "1-sentence explanation connecting the event to this sector.",
            "source_cited": "The exact SOURCE_FILE filename used",
            "proxy_stocks": [
                {
                    "ticker": "1155.KL",
                    "name": "Malayan Banking Berhad",
                    "description": "The largest bank in Malaysia, highly sensitive to interest rate changes."
                },
                // ... 2 more stocks
            ]
        }
    ]
}
"""

def clean_json_output(text):
    if not text:
        return "{}"
    clean = text.strip()
    if clean.startswith("```json"): 
        clean = clean[7:]
    elif clean.startswith("```"): 
        clean = clean[3:]
    if clean.endswith("```"): 
        clean = clean[:-3]
    return clean.strip()

def analyze_event_impact(event_query):
    print(f"🧠 Synthesizing impact for event: '{event_query}'...")
    
    rag_result = query_agent(
        collection_name="financial_knowledge", 
        user_query=event_query, 
        system_prompt=RETAIL_SYSTEM_PROMPT,
        source_filter="retail"
    )
    
    raw_json_string = rag_result.get("llm_response", "{}")
    sources_list = rag_result.get("sources", [])
    
    try:
        cleaned_response = clean_json_output(raw_json_string)
        graph_data = json.loads(cleaned_response)
        graph_data["sources_retrieved"] = sources_list
        return graph_data
    except json.JSONDecodeError as e:
        print(f"❌ Error parsing JSON from LLM: {e}")
        return {"event_name": "Error", "nodes": [], "sources_retrieved": []}

if __name__ == "__main__":
    test_event = "Malaysia announces an OPR rate hike."
    print("Running local test for Retail Agent...")
    result = analyze_event_impact(test_event)
    print(json.dumps(result, indent=4))