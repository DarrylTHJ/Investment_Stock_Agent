import streamlit as st
from streamlit_agraph import agraph, Node, Edge, Config

# Set up the page layout
st.set_page_config(page_title="Event-Driven Impact Visualizer", layout="wide")

st.title("Event-Driven Market Impact Visualizer 🕸️")
st.markdown("Analyze macroeconomic events and news to visualize the ripple effects on various industries based on extracted investment logic.")

# --- 1. User Input Section ---
st.header("1. Input Market Context")
input_type = st.radio("Select Input Mode:", ["Text Description", "News Article URL"])

if input_type == "Text Description":
    user_input = st.text_area("Describe the event:", "Malaysia announces a complete ban on vapes starting next month.")
else:
    user_input = st.text_input("Paste URL:", "https://www.thestar.com.my/news/nation/vape-ban")

analyze_button = st.button("Synthesize Impact Graph", type="primary")

st.divider()

# --- 2. Network Graph Section (Mock Demo) ---
if analyze_button:
    st.header("2. Impact Visualization (Retail Logic)")
    
    with st.spinner("Retrieving logic rules from Vector DB and synthesizing impact..."):
        
        # Define the Nodes
        nodes = []
        edges = []

        # Central Node (The Trigger Event)
        nodes.append(Node(
            id="Event", 
            label="Event: Vape Ban", 
            size=35, 
            shape="diamond",
            color="#2B7CE9" # Blue
        ))

        # Node 1: Tobacco Industry (Negative)
        nodes.append(Node(
            id="Tobacco", 
            label="Tobacco Sector\n(e.g., BAT)", 
            size=25, 
            color="#FF4B4B", # Red
            title="NEGATIVE: Loss of alternative revenue streams and signals tighter overall regulatory sentiment." # Hover text!
        ))
        edges.append(Edge(source="Event", target="Tobacco", label="Regulatory Risk"))

        # Node 2: Convenience Stores (Negative)
        nodes.append(Node(
            id="ConvStores", 
            label="Convenience Stores\n(e.g., MyNews, 7-Eleven)", 
            size=25, 
            color="#FF4B4B", # Red
            title="NEGATIVE: Vapes are a high-margin item driving significant counter sales and foot traffic."
        ))
        edges.append(Edge(source="Event", target="ConvStores", label="Margin Compression"))

        # Node 3: Pharmaceutical/Nicotine Replacements (Positive)
        nodes.append(Node(
            id="Pharma", 
            label="Healthcare / Pharma\n(Nicotine Gums/Patches)", 
            size=25, 
            color="#00CC96", # Green
            title="POSITIVE: Consumer spending redirects to regulated cessation tools."
        ))
        edges.append(Edge(source="Event", target="Pharma", label="Demand Shift"))

        # Graph Configuration
        config = Config(
            width="100%",
            height=500,
            directed=True, 
            physics=True, # Enables the bouncy, interactive physics
            hierarchical=False,
            nodeHighlightBehavior=True,
            highlightColor="#F7A7A6",
            collapsible=True
        )

        # Render the graph in Streamlit
        return_value = agraph(nodes=nodes, edges=edges, config=config)
        
    # --- 3. Text Breakdown Section ---
    st.subheader("Extracted Reasoning Framework")
    st.markdown("""
    **Logic Source:** YouTube Retail Persona (Alfred Chen)
    
    * **Tobacco Industry [Negative]:** According to past analysis on regulatory crackdowns, when a substitute product is banned, regulators often follow up with tighter rules on the primary product. 
    * **Convenience Stores [Negative]:** Retailers like MyNews rely heavily on high-margin counter items. Losing vape sales directly hits bottom-line margins.
    * **Pharma/Healthcare [Positive]:** Historical precedent shows that health-driven bans redirect consumer spending to officially approved cessation tools.
    """)