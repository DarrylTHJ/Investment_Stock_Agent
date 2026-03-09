import json
from rag_agent import query_agent

RETAIL_SYSTEM_PROMPT = """
You are the Retail Logic Synthesizer (based on Alfred Chen's investment logic).
You will be given a market event and a set of retrieved logical rules from your database.
Your task is to predict the ripple effects of this event on various sectors based ONLY on the provided rules.
If the retrieved rules do not cover this specific event, do your best to extrapolate based on his general principles.

You MUST output your response as a valid JSON object. 
Do NOT include any markdown formatting like triple backticks.

Expected JSON Schema:
{
    "event_name": "Short name of the trigger event (e.g., 'Vape Ban', 'OPR Cut')",
    "nodes": [
        {
            "id": "Sector Name (e.g., Tobacco, Banking)",
            "impact": "POSITIVE or NEGATIVE",
            "reasoning": "1-sentence explanation connecting the event to this sector based on the logic rules."
        }
    ]
}
"""

def clean_json_output(text):
    """Helper to strip markdown in case the LLM disobeys the prompt."""
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
    """
    Takes a news event, queries the RAG system for retail logic, 
    and returns a JSON structure for the Streamlit network graph, including sources.
    """
    print(f"🧠 Synthesizing impact for event: '{event_query}'...")
    
    # Call the updated query_agent which now returns a dict with sources
    rag_result = query_agent(
        collection_name="financial_knowledge", 
        user_query=event_query, 
        system_prompt=RETAIL_SYSTEM_PROMPT,
        source_filter="retail"
    )
    
    raw_json_string = rag_result.get("llm_response", "{}")
    sources_list = rag_result.get("sources", [])
    
    try:
        # Clean and parse the LLM's output
        cleaned_response = clean_json_output(raw_json_string)
        graph_data = json.loads(cleaned_response)
        
        # Inject the retrieved sources into the final JSON output
        graph_data["sources"] = sources_list
        return graph_data
        
    except json.JSONDecodeError as e:
        print(f"❌ Error parsing JSON from LLM: {e}")
        return {
            "event_name": "Processing Error",
            "nodes": [
                {
                    "id": "Error Node",
                    "impact": "NEGATIVE",
                    "reasoning": "The LLM failed to return a valid JSON structure."
                }
            ],
            "sources": []
        }

if __name__ == "__main__":
    test_event = "Malaysia announces a complete ban on vapes."
    print("Running local test for Retail Agent...")
    result = analyze_event_impact(test_event)
    print(json.dumps(result, indent=4))