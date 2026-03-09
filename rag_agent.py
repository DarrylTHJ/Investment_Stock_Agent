import os
import chromadb
from chromadb.utils import embedding_functions
from google import genai
from dotenv import load_dotenv

# --- Setup API ---
load_dotenv()
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

# --- Setup ChromaDB ---
db_path = os.path.join(os.path.dirname(__file__), "chroma_db")
chroma_client = chromadb.PersistentClient(path=db_path)

embed_fn = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")

def query_agent(collection_name, user_query, system_prompt, source_filter=None):
    """
    Searches ChromaDB for relevant rules, extracts metadata for fact-checking,
    then passes them to Gemini to synthesize. Returns both the LLM answer AND the sources.
    """
    try:
        collection = chroma_client.get_collection(
            name=collection_name, 
            embedding_function=embed_fn
        )
        
        query_params = {
            "query_texts": [user_query],
            "n_results": 5
        }
        
        # Explicit $eq operator for ChromaDB string filtering
        if source_filter:
            query_params["where"] = {"source_type": {"$eq": source_filter}}
        
        results = collection.query(**query_params)
        
        retrieved_docs = results['documents'][0] if results['documents'] else []
        retrieved_metadatas = results['metadatas'][0] if results['metadatas'] else []
        
        if not retrieved_docs:
            context = "No specific rules found for this event in the database."
            unique_sources = [] 
        else:
            # Build the context string AND pass the filename so the LLM can cite it
            context_blocks = []
            for doc, meta in zip(retrieved_docs, retrieved_metadatas):
                filename = meta.get('filename', 'Unknown Source')
                rule_text = meta.get('logic_rule', doc) # Grab the strict rule if available
                context_blocks.append(f"SOURCE_FILE: {filename}\nRULE: {rule_text}")
                
            context = "\n\n---\n\n".join(context_blocks)
            
            # Pass the actual metadata dicts back to Streamlit for display!
            unique_sources = retrieved_metadatas
            
        full_prompt = f"""
        {system_prompt}
        
        === RETRIEVED LOGIC RULES ===
        {context}
        
        === USER TRIGGER EVENT ===
        Event: {user_query}
        
        Now, analyze the event based strictly on the rules above and output the required JSON.
        """
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=full_prompt
        )
        
        # Return a dictionary containing both the LLM's text AND the source list
        return {
            "llm_response": response.text,
            "sources": unique_sources
        }

    except Exception as e:
        print(f"❌ Error in query_agent: {e}")
        return {"llm_response": "{}", "sources": []}