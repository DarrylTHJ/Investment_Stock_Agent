import os
import json
import time
import random
from google import genai
from dotenv import load_dotenv

# --- SETUP ---
load_dotenv()
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

RETAIL_INPUT_DIR = "data/retail/scraped"
INSTITUTIONAL_INPUT_DIR = "data/institutional/scraped"
RETAIL_OUTPUT_DIR = "data/retail/processed"
INSTITUTIONAL_OUTPUT_DIR = "data/institutional/processed"

# --- YOUR MODEL ROSTER ---
MODEL_ROSTER = [
    #"gemini-3-flash-preview",  # Newest Speed (Corrected name)
    #"gemini-2.5-flash",        # Reliable
    "gemma-3-27b-it",          # Strong Open Model (Corrected name)
    "gemma-3-12b-it",          # Good Mid-range
    #"gemini-2.5-flash-lite",   # Fast (might be busy/503)
]

def clean_json_string(text):
    if not text: return ""
    clean = text.strip()
    if clean.startswith("```json"): clean = clean[7:]
    elif clean.startswith("```"): clean = clean[3:]
    if clean.endswith("```"): clean = clean[:-3]
    return clean

# --- YOUR CORE LOGIC (Retained) ---
def process_file(filepath, category, model_name, output_dir):
    filename = os.path.basename(filepath)
    # Handle extensions safely (.txt/.pdf -> .json)
    base_name = os.path.splitext(filename)[0]
    new_filename = f"{base_name}_processed.json"
    output_filename = os.path.join(output_dir, new_filename)

    if os.path.exists(output_filename):
        print(f"⏭️ Skipping: {new_filename}")
        return

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            raw_text = f.read()
        if not raw_text.strip(): return
    except Exception as e:
        print(f"❌ Read Error: {e}")
        return

    print(f"🔹 Processing [{category}] with 🤖 {model_name}...")

    # prompt = f"""
    # You are a Financial Analyst. Extract logical units from this {category} text.
    # Output JSON list only.
    # Schema: {{ "text": "quote", "type": "FACT/PRINCIPLE/OPINION", "reasoning": "string" }}
    # TEXT: {raw_text[:30000]}
    # """

    print(f"🔹 Processing [{category}] with 🤖 {model_name}...")

    prompt = f"""
    You are a financial logic extractor for Explainable AI. 
    Read this {category} transcript. Deduce underlying market triggers.
    
    Output STRICTLY a JSON list of objects:
    [
      {{
        "trigger_event": "Macro event (e.g., 'OPR Rate Cut')",
        "impacted_sector": "Specific sector affected",
        "impact_direction": "POSITIVE or NEGATIVE",
        "logic_rule": "IF [event] THEN [impact] statement.",
        "verbatim_quote": "THE EXACT CHINESE/ENGLISH PHRASE FROM THE TEXT THAT PROVES THIS.",
        "embedding_summary": "Natural language summary for vector search."
      }}
    ]
    TEXT:
    {raw_text[:30000]}
    """

    # Retry Logic
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt
            )
            
            if not response.text:
                print(f"⚠️ Empty response from {model_name}")
                return

            data = json.loads(clean_json_string(response.text))
            
            final_output = {
                "meta": {"source": filename, "model": model_name, "time": time.time()},
                "data": data
            }
            
            # Ensure output dir exists
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)

            with open(output_filename, "w", encoding="utf-8") as f:
                json.dump(final_output, f, indent=4)
            
            print(f"✅ Saved: {new_filename}")
            return 

        except Exception as e:
            err_msg = str(e)
            if "404" in err_msg or "NOT_FOUND" in err_msg:
                print(f"❌ Model {model_name} NOT FOUND.")
                return 
            if "503" in err_msg or "UNAVAILABLE" in err_msg:
                wait_time = (attempt + 1) * 5 
                print(f"⏳ Server Busy ({model_name}). Sleeping {wait_time}s...")
                time.sleep(wait_time)
                continue
            if "429" in err_msg:
                print(f"⏳ Rate Limit. Sleeping 30s...")
                time.sleep(30)
                continue
            print(f"❌ Error on {filename}: {err_msg}")
            return

# --- NEW: The Bridge for the Watcher ---
def process_single_file(input_path, output_dir):
    """
    This function is called by pipeline_watcher.py.
    It picks a random model from your roster to keep the variety.
    """
    # 1. Guess Category from path
    category = "RETAIL" if "retail" in input_path.lower() else "INSTITUTIONAL"
    
    # 2. Pick a Model (Randomly to utilize your roster)
    selected_model = random.choice(MODEL_ROSTER)
    
    # 3. Call your original logic
    process_file(input_path, category, selected_model, output_dir)


# --- BATCH LOGIC (Retained) ---
def run_batch(input_dir, output_dir, category):
    if not os.path.exists(input_dir):
        print(f"❌ Missing Dir: {input_dir}")
        return

    files = [f for f in os.listdir(input_dir) if f.endswith(".txt") or f.endswith(".pdf")]
    print(f"\n🚀 Batch: {category} ({len(files)} files)")
    
    model_index = 0
    for i, filename in enumerate(files):
        filepath = os.path.join(input_dir, filename)
        
        # Rotate Models
        current_model = MODEL_ROSTER[model_index % len(MODEL_ROSTER)]
        
        process_file(filepath, category, current_model, output_dir)
        
        model_index += 1
        if i < len(files) - 1: 
            time.sleep(10) # Your preferred sleep time

if __name__ == "__main__":
    run_batch(RETAIL_INPUT_DIR, RETAIL_OUTPUT_DIR, "RETAIL")
    run_batch(INSTITUTIONAL_INPUT_DIR, INSTITUTIONAL_OUTPUT_DIR, "INSTITUTIONAL")