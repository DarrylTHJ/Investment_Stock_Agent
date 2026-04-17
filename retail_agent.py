import json
import os
import re
from rag_agent import chroma_client, embed_fn, client

# --- 1. PROMPT ENGINEERING ---

PROMPT_PART_1 = """
You are the Alfred Chen Logic Mimicry Engine for Explainable AI (XAI).
Your goal is to deduce the impact of a specific user event on Malaysian stock sectors, strictly using the retrieved rules below.

CRITICAL INSTRUCTIONS:
1. Your ONLY reality is the 'DATASET' provided below. Do not hallucinate external financial knowledge. 
2. You must show your Chain of Thought (how you weigh conflicting rules or apply specific conditions).
3. You must calculate a NET SCORE (-10 to +10) for the impacted sectors.
4. For every impacted sector, pick exactly 1 to 3 proxy stock tickers ONLY from the live database below. Do not invent any tickers!

--- LIVE BURSA MALAYSIA DATABASE ---
"""

PROMPT_PART_2 = """
------------------------------------

Output your response as a valid JSON object matching this EXACT schema:
{
    "thinking_trace": [
        {"step": 1, "thought": "Identifying the primary trigger based on input..."},
        {"step": 2, "thought": "Checking for conflicting retail rules in the database..."},
        {"step": 3, "thought": "Resolving contradictions by weighing factors..."}
    ],
    "sectors": [
        {
            "id": "Sector Name (e.g., Banking)",
            "net_score": 5,
            "logic_path": "Event -> Logic -> Sector",
            "reasoning": "Detailed explanation of the thinking process and why this score was given.",
            "proof": {
                "quote": "The exact verbatim phrase from the dataset that proves this.",
                "video_id": "THE_VIDEO_ID"
            },
            "proxy_stocks": [
                {"ticker": "1155.KL", "name": "Maybank"}
            ]
        }
    ]
}
"""

# --- 2. HELPER FUNCTIONS ---

def get_dynamic_prompt():
    """Reads the live JSON database to prevent hallucinated tickers."""
    db_path = os.path.join(os.path.dirname(__file__), "data", "bursa_tickers.json")
    try:
        with open(db_path, "r", encoding="utf-8") as f:
            ticker_db = json.load(f)
            
        db_string = ""
        for sector, stocks in ticker_db.items():
            stock_strings = [f'"{s["ticker"]}" ({s["name"]})' for s in stocks]
            db_string += f"{sector}: {', '.join(stock_strings)}\n"
    except FileNotFoundError:
        db_string = "Error: Live database unavailable. Fall back to generic 4-digit Bursa tickers (e.g., 1155.KL).\n"
        
    return PROMPT_PART_1 + db_string + PROMPT_PART_2


def clean_json_output(text):
    """Bulletproof JSON extractor using Regex to ignore conversational LLM filler."""
    if not text: 
        return "{}"
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        return match.group(0)
    return "{}"


# --- 3. CORE LOGIC ENGINE ---

def analyze_event_logic(user_event, target_industry=None):
    """
    Takes a user event and optionally a target industry.
    Searches ChromaDB, extracts rules/quotes, and synthesizes the CoT.
    """
    print(f"\n🌍 Analyzing Event: '{user_event}'")
    if target_industry:
        print(f"🎯 Target Focus: {target_industry}")

    try:
        collection = chroma_client.get_collection(name="financial_knowledge", embedding_function=embed_fn)
    except Exception as e:
        print(f"❌ ChromaDB Error: {e}")
        return {"error": str(e)}

    # 1. Query ChromaDB directly using the user's event
    # If specific target is provided, we weave it into the search to force the vector DB to find overlaps
    search_query = f"{user_event} impact on {target_industry}" if target_industry else user_event
    
    print("🧠 Querying Vector Database for historical rules...")
    try:
        results = collection.query(
            query_texts=[search_query], 
            n_results=6, # Fetch top 6 rules to allow the AI to find conflicts and build a Chain of Thought
            where={"source_type": {"$eq": "retail"}}
        )
        
        retrieved_docs = results['documents'][0] if results.get('documents') and len(results['documents']) > 0 else []
        retrieved_metadatas = results['metadatas'][0] if results.get('metadatas') and len(results['metadatas']) > 0 else []
        
    except Exception as e:
        print(f"⚠️ Vector Search Error: {e}")
        retrieved_docs, retrieved_metadatas = [], []

    # Handle empty database returns gracefully
    if not retrieved_docs:
        return {
            "thinking_trace": [
                {"step": 1, "thought": f"Searched the database for '{search_query}'."},
                {"step": 2, "thought": "No specific rules from Alfred Chen were found matching this scenario."}
            ],
            "sectors": []
        }

    # 2. Extract rules and build the evidence context for the LLM
    context_blocks = []
    for i, (doc, meta) in enumerate(zip(retrieved_docs, retrieved_metadatas)):
        rule = meta.get('logic_rule', doc)
        quote = meta.get('verbatim_quote', 'N/A')
        v_id = meta.get('video_id', 'UNKNOWN')
        
        context_blocks.append(
            f"[RULE {i+1}]\n"
            f"LOGIC: {rule}\n"
            f"VERBATIM QUOTE: {quote}\n"
            f"VIDEO_ID: {v_id}\n"
        )
    
    final_context = "\n---\n".join(context_blocks)
    
    # 3. Final Prompt Assembly
    user_query_block = f"\n=== USER SCENARIO ===\nEvent: {user_event}\nTarget Industry (if any): {target_industry or 'None'}\n"
    full_prompt = get_dynamic_prompt() + "\n=== DATASET (RETRIEVED RULES) ===\n" + final_context + user_query_block
    
    print("⚖️ Synthesizing Chain of Thought via LLM...")
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=full_prompt
        )
    except Exception as e:
        print(f"❌ LLM API Error: {e}")
        return {"error": str(e)}
    
    # 4. Parse JSON safely
    try:
        cleaned_response = clean_json_output(response.text)
        graph_data = json.loads(cleaned_response)
        return graph_data
    except json.JSONDecodeError as e:
        print(f"❌ Error parsing JSON from LLM: {e}")
        print(f"--- RAW LLM RESPONSE ---\n{response.text}\n------------------------")
        return {"error": "Failed to parse JSON."}