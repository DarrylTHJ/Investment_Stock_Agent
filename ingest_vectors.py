import os
import json
import chromadb
from chromadb.utils import embedding_functions
import uuid

# --- CONFIGURATION ---
DB_PATH = "./chroma_db"
COLLECTION_NAME = "financial_knowledge"
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"

# Global Client (Initialize once)
client = chromadb.PersistentClient(path=DB_PATH)
ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name=EMBEDDING_MODEL_NAME)
collection = client.get_or_create_collection(name=COLLECTION_NAME, embedding_function=ef)

def ingest_single_file(file_path, source_type):
    """
    Process ONE specific JSON file and add it to the DB.
    """
    print(f"⚡ Ingesting file: {file_path}")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            json_content = json.load(f)
    except Exception as e:
        print(f"❌ Error reading JSON: {e}")
        return

    documents = []
    metadatas = []
    ids = []
    
    # In the new schema, the JSON might be a direct list, or nested under "data"
    if isinstance(json_content, list):
        items = json_content
    elif isinstance(json_content, dict):
        items = json_content.get("data", [])
    else:
        items = []
    
    if not items:
        print(f"⚠️ Warning: No rule objects found in {file_path}")
        return

    filename = os.path.basename(file_path)

    for item in items:
        # We embed the natural language summary
        text_content = item.get("embedding_summary", "")
        
        if not text_content:
            continue

        # We store the strict logic elements as metadata
        # Safely convert to strings (ChromaDB requirement)
        metrics_used = item.get("metrics_used", [])
        metrics_ignored = item.get("metrics_ignored", [])
        
        metrics_used_str = ", ".join(metrics_used) if isinstance(metrics_used, list) else str(metrics_used)
        metrics_ignored_str = ", ".join(metrics_ignored) if isinstance(metrics_ignored, list) else str(metrics_ignored)

        documents.append(text_content)
        metadatas.append({
            "source_type": source_type,
            "filename": filename,
            "trigger_event": str(item.get("trigger_event", "UNKNOWN")),
            "impacted_sector": str(item.get("impacted_sector", "UNKNOWN")),
            "impact_direction": str(item.get("impact_direction", "UNKNOWN")),
            "logic_rule": str(item.get("logic_rule", "UNKNOWN")),
            "embedding_summary": str(item.get("embedding_summary", "UNKNOWN"))
        })
        ids.append(f"{filename}-{uuid.uuid4()}")

    if documents:
        collection.upsert(documents=documents, metadatas=metadatas, ids=ids)
        print(f"✅ Successfully added {len(documents)} logic rules from {filename}")
    else:
        print(f"⚠️ No valid logic rules found in {filename}")

def process_all_folders():
    # UPDATED PATHS to match your actual directory structure
    DATA_DIRS = {
        "retail": "./data/retail/processed",
        "institutional": "./data/institutional/processed"
    }
    for source, directory in DATA_DIRS.items():
        if os.path.exists(directory):
            for f in os.listdir(directory):
                if f.endswith(".json"):
                    ingest_single_file(os.path.join(directory, f), source)
        else:
            print(f"⚠️ Directory not found: {directory}")

if __name__ == "__main__":
    process_all_folders()