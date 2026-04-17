import streamlit as st
from streamlit_agraph import agraph, Node, Edge, Config
from retail_agent import analyze_event_logic

st.set_page_config(page_title="Alfred Chen Logic Engine", layout="wide")

st.title("Alfred Chen Logic Mimicry Engine 🧠")
st.markdown("Input a macroeconomic event. The AI will retrieve Alfred Chen's past investment rules, resolve any conflicting logic, and map out the expected sector impact with verbatim proof.")

# --- 1. USER INPUT (SIDEBAR) ---
with st.sidebar:
    st.header("1. Define Scenario")
    mode = st.radio(
        "Analysis Mode", 
        ["General Macro Impact", "Specific Industry/Stock Target"],
        help="General mode maps all affected sectors. Specific mode focuses the AI's reasoning on a single target."
    )
    
    event_input = st.text_area(
        "Trigger Event / Scenario", 
        placeholder="e.g., Bank Negara unexpectedly hikes OPR by 25bps...",
        height=100
    )
    
    target_input = None
    if mode == "Specific Industry/Stock Target":
        target_input = st.text_input(
            "Target Industry or Stock", 
            placeholder="e.g., Banking, or Maybank"
        )
        
    analyze_button = st.button("Synthesize Logic Path", type="primary", use_container_width=True)

# --- MAIN EXECUTION ---
if analyze_button:
    if not event_input:
        st.warning("⚠️ Please enter a Trigger Event to proceed.")
        st.stop()
        
    with st.spinner("🧠 Searching vector database and reasoning..."):
        # We pass both the event and the optional target to the agent
        data = analyze_event_logic(event_input, target_input)
        
    if not data or "sectors" not in data:
        st.error("❌ Failed to generate logic. Please try again.")
        st.stop()
        
    # --- 2. THE GRAPH (Top Layer) ---
    st.header("🕸️ Logic Graph Visualizer")
    
    nodes, edges = [], []
    added_nodes = set()
    
    # Center Node (The User's Event)
    event_node_id = "Event"
    nodes.append(Node(id=event_node_id, label="Trigger Event", size=30, shape="diamond", color="#FFD700", title=event_input))
    
    for sector in data.get("sectors", []):
        s_id = sector.get("id", "Unknown Sector")
        net_score = sector.get("net_score", 0)
        
        # Color coding based on impact
        node_color = "#00CC96" if net_score > 0 else ("#FF4B4B" if net_score < 0 else "#D3D3D3")
        
        if s_id not in added_nodes:
            nodes.append(Node(id=s_id, label=f"{s_id}\n(Impact: {net_score})", size=25, shape="box", color=node_color))
            added_nodes.add(s_id)
            
        # Edge from Event to Sector
        edges.append(Edge(source=event_node_id, target=s_id, label=sector.get("logic_path", ""), color=node_color))
        
        # Plot the Proxy Stocks
        for stock in sector.get("proxy_stocks", []):
            ticker = stock.get("ticker", "UNKNOWN")
            name = stock.get("name", "Unknown")
            
            if ticker not in added_nodes:
                nodes.append(Node(id=ticker, label=name, size=15, shape="ellipse", color="#808080", title=ticker))
                added_nodes.add(ticker)
                
            edges.append(Edge(source=s_id, target=ticker, color="#A9A9A9"))
            
    config = Config(width="100%", height=500, directed=True, physics=True, hierarchical=False)
    
    if len(nodes) > 1:
        agraph(nodes=nodes, edges=edges, config=config)
        st.caption("💡 *Tip: Hover over nodes to see details. Green = Positive Impact, Red = Negative Impact.*")
    else:
        st.warning("Not enough data to draw the graph.")

    st.divider()

    # --- 3. CHAIN OF THOUGHT (Middle Layer) ---
    st.header("🧠 Chain of Thought")
    st.markdown("How the AI resolved conflicts and applied Alfred's logic to your specific scenario.")
    
    # st.status creates a great animated "thinking" box
    with st.status("AI Thinking Trace (Resolving Conflicting Logic)...", expanded=True):
        for step in data.get("thinking_trace", []):
            step_num = step.get('step', '?')
            thought = step.get('thought', '...')
            st.markdown(f"**Step {step_num}:** {thought}")
            
    st.divider()
    
    # --- 4. EVIDENCE & PROOF (Bottom Layer) ---
    st.header("🔍 Evidence & Verification")
    st.markdown("Verify the AI's logic directly against Alfred Chen's historical transcripts.")
    
    for sector in data.get("sectors", []):
        net_score = sector.get("net_score", 0)
        emoji = "📈" if net_score > 0 else ("📉" if net_score < 0 else "➖")
        
        with st.expander(f"{emoji} Proof: Impact on {sector.get('id')} (Score: {net_score})", expanded=True):
            st.markdown(f"**Agent's Final Reasoning:** {sector.get('reasoning')}")
            
            proof = sector.get("proof", {})
            quote = proof.get("quote", "No quote provided.")
            video_id = proof.get("video_id", "UNKNOWN")
            
            # Highlight the exact phrase pulled from the vector DB
            st.info(f"**Verbatim Source Quote:**\n> *\"{quote}\"*")
            
            # Construct the clickable YouTube link
            if video_id and video_id != "UNKNOWN" and video_id != "N/A":
                youtube_url = f"https://www.youtube.com/watch?v={video_id}"
                st.link_button("📺 Watch Source Video on YouTube", youtube_url)
            else:
                st.warning("⚠️ Source Video ID not found for this quote.")