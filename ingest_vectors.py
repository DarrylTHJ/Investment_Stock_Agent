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
    
    # In the new schema, the JSON is a direct list of rule objects
    items = json_content.get("data", [])
    
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
        # Chroma requires metadata values to be strings, ints, or floats (no lists)
        metrics_used_str = ", ".join(item.get("metrics_used", []))
        metrics_ignored_str = ", ".join(item.get("metrics_ignored", []))

        documents.append(text_content)
        metadatas.append({
            "source_type": source_type,
            "filename": filename,
            "asset_class": item.get("asset_class", "UNKNOWN"),
            "logic_rule": item.get("logic_rule", "UNKNOWN"),
            "metrics_used": metrics_used_str,
            "metrics_ignored": metrics_ignored_str
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