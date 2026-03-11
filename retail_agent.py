import json
import os
import re
import datetime
from gnews import GNews
from rag_agent import chroma_client, embed_fn, client

# We split the prompt so we can inject the live ticker database in the middle
PROMPT_PART_1 = """
You are the Macro Retail Logic Synthesizer (based on Alfred Chen's investment logic).
You will receive multiple news headlines from a specific macro period, and Alfred's retrieved logic rules for EACH headline.

CRITICAL INSTRUCTIONS:
1. Your ONLY reality is the 'RETRIEVED RULES' provided below. Do not hallucinate external financial knowledge.
2. You must calculate the NET IMPACT of these combined forces on Malaysian economic sectors.

SCORING PROTOCOL (-10 to +10):
You MUST assign a score to each news event's impact on a sector based ONLY on the urgency/adjectives in Alfred's retrieved rules:
- Score +/- 8 to 10: Alfred uses absolute terms ('massive', 'always', 'guaranteed', 'crash', 'skyrocket').
- Score +/- 4 to 7: Standard causative words ('leads to', 'causes', 'hurts', 'benefits').
- Score +/- 1 to 3: Weak words ('might', 'slight headwind', 'could impact').
- Score 0: If the rule does not explicitly link the event to the sector. Do not guess.

NEW REQUIREMENT (STOCK PROXIES):
For every impacted sector, pick exactly 3 proxy stock tickers ONLY from the live database below. Do not invent any tickers!

--- LIVE BURSA MALAYSIA DATABASE ---
"""

PROMPT_PART_2 = """
------------------------------------

Output your response as a valid JSON object matching this exact schema:
{
    "period_summary": "1-sentence summary of the macro period",
    "news_events": [
        {"id": "news_1", "headline": "Exact headline text here"}
    ],
    "sectors": [
        {
            "id": "Sector Name (e.g., Banking)",
            "net_score": 5,
            "final_verdict": "POSITIVE",
            "reasoning": "Overall positive because factor A outweighed factor B.",
            "competing_forces": [
                {"news_id": "news_1", "score": 8, "reasoning": "Alfred explicitly states this causes massive growth."}
            ],
            "proxy_stocks": [
                {"ticker": "1155.KL", "name": "Maybank", "description": "1-sentence description."}
            ]
        }
    ]
}

=== USER'S MACRO NEWS EVENTS & RETRIEVED RULES ===
"""

def get_dynamic_prompt():
    """Reads the live JSON database to prevent hallucinated tickers."""
    # Ensure it maps to the correct data folder structure
    db_path = os.path.join(os.path.dirname(__file__), "data", "bursa_tickers.json")
    try:
        with open(db_path, "r", encoding="utf-8") as f:
            ticker_db = json.load(f)
            
        db_string = ""
        for sector, stocks in ticker_db.items():
            stock_strings = [f'"{s["ticker"]}" ({s["name"]})' for s in stocks]
            db_string += f"{sector}: {', '.join(stock_strings)}\n"
    except FileNotFoundError:
        db_string = "Error: Live database unavailable. Please fall back to generic 4-digit Bursa tickers (e.g., 1155.KL).\n"
        
    return PROMPT_PART_1 + db_string + PROMPT_PART_2

def clean_json_output(text):
    """Bulletproof JSON extractor using Regex to ignore conversational LLM filler."""
    if not text: 
        return "{}"
    
    # Hunt for the first '{' and the last '}' across multiple lines
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        return match.group(0)
    
    return "{}"

def fetch_macro_news(start_date, end_date):
    """Fetches real historical headlines using GNews."""
    gnews = GNews(language='en', country='MY', max_results=3) # Top 3 major events to prevent context bloat
    gnews.start_date = (start_date.year, start_date.month, start_date.day)
    gnews.end_date = (end_date.year, end_date.month, end_date.day)
    query = "Malaysia economy OR Bursa Malaysia OR Bank Negara"
    return gnews.get_news(query)

def analyze_macro_period(start_date, end_date):
    print(f"🌍 Fetching Macro News between {start_date} and {end_date}...")
    news_articles = fetch_macro_news(start_date, end_date)
    
    if not news_articles:
        return {"period_summary": "Error: No news found for this period. Try a different date range.", "news_events": [], "sectors": [], "sources_retrieved": []}

    print("🧠 Querying ChromaDB for each historical headline...")
    
    try:
        collection = chroma_client.get_collection(name="retail_collection", embedding_function=embed_fn)
    except Exception as e:
        print(f"❌ ChromaDB Error: {e}")
        return {"period_summary": f"Database Error: {e}", "news_events": [], "sectors": [], "sources_retrieved": []}

    context_blocks = []
    all_sources = []
    
    # 1. Loop through each piece of news and fetch Alfred's specific rules for it
    for i, article in enumerate(news_articles):
        news_id = f"news_{i+1}"
        headline = article.get('title', 'Unknown Event')
        
        # Query the vector DB using the actual headline text
        try:
            results = collection.query(
                query_texts=[headline], 
                n_results=2, # Get top 2 rules per headline
                where={"source_type": {"$eq": "retail"}}
            )
            
            # Safely handle empty ChromaDB returns
            retrieved_docs = results['documents'][0] if results.get('documents') and len(results['documents']) > 0 else []
            retrieved_metadatas = results['metadatas'][0] if results.get('metadatas') and len(results['metadatas']) > 0 else []
            
        except Exception as e:
            print(f"⚠️ Warning: Failed to query headline '{headline}': {e}")
            retrieved_docs, retrieved_metadatas = [], []

        rule_texts = []
        for doc, meta in zip(retrieved_docs, retrieved_metadatas):
            all_sources.append(meta) # Save for UI citations
            rule_texts.append(f"- SOURCE: {meta.get('filename', 'Unknown')} | RULE: {meta.get('logic_rule', doc)}")
            
        rules_string = "\n".join(rule_texts) if rule_texts else "- No explicit rules found for this event."
        
        context_blocks.append(f"NEWS EVENT ID [{news_id}]: {headline}\nALFRED's RETRIEVED RULES:\n{rules_string}\n")

    # 2. Build the final prompt
    final_context = "\n".join(context_blocks)
    full_prompt = get_dynamic_prompt() + final_context
    
    print("⚖️ Calculating Net Weighting via LLM...")
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=full_prompt
        )
    except Exception as e:
        print(f"❌ LLM API Error: {e}")
        return {"period_summary": f"API Error: {e}", "news_events": [], "sectors": [], "sources_retrieved": []}
    
    # 3. Parse JSON safely
    try:
        cleaned_response = clean_json_output(response.text)
        graph_data = json.loads(cleaned_response)
        graph_data["sources_retrieved"] = all_sources # Attach raw metadata for the Streamlit Expander
        return graph_data
    except json.JSONDecodeError as e:
        print(f"❌ Error parsing JSON from LLM: {e}")
        print(f"--- RAW LLM RESPONSE ---\n{response.text}\n------------------------")
        return {"period_summary": "Error: The AI failed to format its response as JSON.", "news_events": [], "sectors": [], "sources_retrieved": []}

if __name__ == "__main__":
    test_start = datetime.date(2023, 11, 1)
    test_end = datetime.date(2023, 11, 30)
    result = analyze_macro_period(test_start, test_end)
    print(json.dumps(result, indent=4))