# import pysqlite3
# import sys
# sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')

import streamlit as st
import chromadb
from chromadb.utils import embedding_functions
from google import genai
import os
from dotenv import load_dotenv

# --- SETUP ---
load_dotenv()
st.set_page_config(page_title="FinSight AI", layout="wide")

# Initialize Clients (Cached to prevent reloading on every click)
@st.cache_resource
def get_chroma_collection():
    DB_PATH = "./chroma_db"
    EMBEDDING_MODEL = "all-MiniLM-L6-v2"
    client = chromadb.PersistentClient(path=DB_PATH)
    ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name=EMBEDDING_MODEL)
    return client.get_collection(name="financial_knowledge", embedding_function=ef)

@st.cache_resource
def get_gemini_client():
    api_key = os.environ.get("GEMINI_API_KEY")
    return genai.Client(api_key=api_key)

collection = get_chroma_collection()
client = get_gemini_client()

# --- LOGIC ---
def retrieve_filtered(query, source_type, n=5):
    results = collection.query(
        query_texts=[query],
        n_results=n,
        where={"source_type": source_type}
    )
    documents = results['documents'][0] if results['documents'] else []
    metadatas = results['metadatas'][0] if results['metadatas'] else []
    return documents, metadatas

def format_context_for_llm(documents):
    return "\n".join([f"- {doc}" for doc in documents])

# --- UI LAYOUT ---
st.title("🤖 FinSight: Dual-Source Financial Analysis")
st.markdown("Compare **Institutional Reports** vs. **Retail Sentiment** instantly.")

# Sidebar for controls
with st.sidebar:
    st.header("Configuration")
    model_choice = st.selectbox("AI Model", ["gemini-3-flash-preview", "gemma-3-12b-it"])

# Main Input
query = st.text_input("Enter a financial question or topic (e.g., 'Inflation outlook'):")

if st.button("Analyze") and query:
    with st.spinner("🔍 Retrieving data from Vector DB..."):
        # 1. Retrieve Data
        inst_docs, inst_meta = retrieve_filtered(query, "institutional")
        retail_docs, retail_meta = retrieve_filtered(query, "retail")
        
        inst_ctx = format_context_for_llm(inst_docs)
        retail_ctx = format_context_for_llm(retail_docs)

# 2. Display Retrieved Logic (Expandable)
    with st.expander("🧠 View Retrieved Cognitive Logic (The Brain)"):
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("🏛️ Institutional Logic")
            if not inst_docs: st.write("No institutional rules found (Offline).")
            for doc, meta in zip(inst_docs, inst_meta):
                st.markdown(f"**Asset Class:** {meta.get('asset_class', 'Unknown')}")
                st.markdown(f"**Logic Rule:** `{meta.get('logic_rule', 'None')}`")
                st.caption(f"📄 Source: {meta.get('filename', 'Unknown')}")
                st.divider()
        with col2:
            st.subheader("🗣️ Retail Logic (Alfred's Rules)")
            if not retail_docs: st.write("No retail rules found.")
            for doc, meta in zip(retail_docs, retail_meta):
                st.markdown(f"**Asset Target:** {meta.get('asset_class', 'Unknown')}")
                st.markdown(f"**Rule:** `{meta.get('logic_rule', 'None')}`")
                st.markdown(f"**Key Metrics:** {meta.get('metrics_used', 'None')}")
                st.caption(f"📄 Source: {meta.get('filename', 'Unknown')}")
                st.divider()
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("🏛️ Institutional Sources")
            if not inst_docs: st.write("No data found.")
            for doc, meta in zip(inst_docs, inst_meta):
                st.caption(f"📄 {meta.get('filename', 'Unknown')}")
                st.text(doc[:150] + "...")
        with col2:
            st.subheader("🗣️ Retail Sources")
            if not retail_docs: st.write("No data found.")
            for doc, meta in zip(retail_docs, retail_meta):
                st.caption(f"📄 {meta.get('filename', 'Unknown')}")
                st.text(doc[:150] + "...")

    # 3. Generate Answer
    if not inst_docs and not retail_docs:
        st.error("❌ No relevant data found in the database.")
    else:
        with st.spinner("🤖 Generating Analysis..."):
            prompt = f"""
            You are a Financial Analyst.
            
            USER QUERY: {query}
            
            ### INSTITUTIONAL DATA:
            {inst_ctx}
            
            ### RETAIL DATA:
            {retail_ctx}
            
            OUTPUT FORMAT:
            ## 🏛️ Institutional Perspective
            [Summary]
            
            ## 🗣️ Retail/Market Sentiment
            [Summary]
            
            ## ⚖️ Divergence Analysis
            [Comparison]
            """
            
            try:
                response = client.models.generate_content(
                    model=model_choice,
                    contents=prompt
                )
                st.markdown("---")
                st.markdown(response.text)
            except Exception as e:
                st.error(f"Error communicating with Gemini: {e}")