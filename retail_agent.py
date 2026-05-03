import json
import os
import re
from rag_agent import chroma_client, embed_fn, client

# --- 1. PROMPT ENGINEERING ---

PROMPT_PART_1 = """
You are the Alfred Chen Logic Mimicry Engine for Explainable AI (XAI).
Your goal is to deduce the impact of a specific user event on Malaysian stock sectors, strictly using the retrieved rules below.

CRITICAL INSTRUCTIONS (PENALTY FOR VIOLATION):
1. ZERO-INFERENCE RULE: Your ONLY reality is the 'DATASET'. Do not hallucinate external macroeconomic theories. 
   - If a rule explicitly names a specific sector (e.g., "Plantation"), map it to that sector.
   - If a rule explicitly describes a broad impact (e.g., "Market Sentiment", "Dividend Stocks"), you MAY map it to a thematic category like "Broad Market". 
   - You MUST NOT guess specific industries if they are not explicitly mentioned.
2. THE TARGETING DIRECTIVE (STRICT ENFORCEMENT):
   - IF the "Target Industry (if any)" is 'None' -> You MUST extract and map out EVERY DISTINCT SECTOR OR THEME explicitly mentioned in the dataset.
   - IF a "Target Industry" IS PROVIDED (e.g., "Construction") -> You MUST STRICTLY FILTER your output. You are ONLY allowed to map the sector/theme that matches the requested target. You MUST COMPLETELY IGNORE all other sectors and rules that do not apply to the target, even if they appear in the dataset!
3. You must calculate a NET SCORE (-10 to +10) based ONLY on the provided rules.
4. For every impacted sector, pick 1 to 3 proxy stock tickers from the live database below. IF the impacted category is a broad theme and doesn't perfectly fit the database, you may select large-cap blue-chip proxies or leave the array empty `[]`. Do not invent fake tickers!

--- LIVE BURSA MALAYSIA DATABASE ---
"""

PROMPT_PART_2 = """
------------------------------------

Output your response as a valid JSON object matching this EXACT schema:
{
    "raw_rules_established": [
        {
            "rule_id": "Rule 1",
            "rule_text": "The exact logic rule retrieved from the dataset.",
            "quote": "The exact verbatim phrase from the dataset.",
            "video_id": "THE_VIDEO_ID"
        }
    ],
    "thinking_trace": [
        {"step": 1, "thought": "Identifying the primary trigger based on input..."},
        {"step": 2, "thought": "I found Rule 1 linking tariffs to tech, but no rules linking it to banks. I will drop banks to obey the Zero-Inference Rule."}
    ],
    "sectors": [
        {
            "id": "Sector Name (e.g., Technology)",
            "net_score": -5,
            "edge_label_max_5_words": "Short summary max five words",
            "reasoning": "Detailed explanation of why this score was given, explicitly referencing [Rule 1].",
            "citations": ["Rule 1"],
            "proxy_stocks": [
                {"ticker": "0166.KL", "name": "Inari Amertron"}
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
        db_string = "Error: Live database unavailable. Fall back to generic 4-digit Bursa tickers.\n"
        
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
    print(f"\n🌍 Analyzing Event: '{user_event}'")
    if target_industry:
        print(f"🎯 Target Focus: {target_industry}")

    try:
        collection = chroma_client.get_collection(name="financial_knowledge", embedding_function=embed_fn)
    except Exception as e:
        print(f"❌ ChromaDB Error: {e}")
        return {"error": str(e)}

    # 1. Query ChromaDB directly using the user's event
    search_query = f"{user_event} impact on {target_industry}" if target_industry else user_event
    
    print("🧠 Querying Vector Database for historical rules...")
    try:
        results = collection.query(
            query_texts=[search_query], 
            n_results=8, # Increased to 8 to ensure we capture all branches for General mode
            where={"source_type": {"$eq": "retail"}}
        )
        
        retrieved_docs = results['documents'][0] if results.get('documents') and len(results['documents']) > 0 else []
        retrieved_metadatas = results['metadatas'][0] if results.get('metadatas') and len(results['metadatas']) > 0 else []
        
    except Exception as e:
        print(f"⚠️ Vector Search Error: {e}")
        retrieved_docs, retrieved_metadatas = [], []

    if not retrieved_docs:
        return {"error": "No rules found."}

    # 2. Extract rules and build the evidence context explicitly labeled as Rule 1, Rule 2...
    context_blocks = []
    for i, (doc, meta) in enumerate(zip(retrieved_docs, retrieved_metadatas)):
        rule = meta.get('logic_rule', doc)
        quote = meta.get('verbatim_quote', 'N/A')
        v_id = meta.get('video_id', 'UNKNOWN')
        
        context_blocks.append(
            f"[Rule {i+1}]\n"
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