import streamlit as st
from streamlit_agraph import agraph, Node, Edge, Config
from retail_agent import analyze_event_logic

st.set_page_config(page_title="Alfred Chen Logic Engine", layout="wide")

st.title("Alfred Chen Logic Mimicry Engine 🧠")
st.markdown("Input a macroeconomic event. The AI will retrieve past investment rules, resolve conflicting logic, and map out sector impacts strictly using verbatim proof.")

# --- 1. USER INPUT (SIDEBAR) ---
with st.sidebar:
    st.header("1. Define Scenario")
    mode = st.radio(
        "Analysis Mode", 
        ["General Macro Impact", "Specific Industry/Stock Target"],
        help="General mode maps all affected sectors. Specific mode focuses the AI's reasoning on a single target."
    )
    
    event_input = st.text_area("Trigger Event / Scenario", placeholder="e.g., Donald Trump imposes 60% tariffs on China", height=100)
    
    target_input = None
    if mode == "Specific Industry/Stock Target":
        target_input = st.text_input("Target Industry or Stock", placeholder="e.g., Technology")
        
    analyze_button = st.button("Synthesize Logic Path", type="primary", use_container_width=True)

# --- MAIN EXECUTION ---
if analyze_button:
    if not event_input:
        st.warning("⚠️ Please enter a Trigger Event to proceed.")
        st.stop()
        
    with st.spinner("🧠 Searching vector database and reasoning..."):
        data = analyze_event_logic(event_input, target_input)
        
    if not data or "error" in data:
        st.error(data.get("error", "❌ Failed to generate logic. Please try again."))
        st.stop()
        
    # --- 2. THE GRAPH (Top Layer) ---
    st.header("🕸️ Logic Graph Visualizer")
    
    nodes, edges = [], []
    added_nodes = set()
    
    event_short = event_input[:30] + "..." if len(event_input) > 30 else event_input
    event_node_id = "Event"
    nodes.append(Node(id=event_node_id, label=event_short, size=30, shape="diamond", color="#FFD700", title=event_input))
    
    for sector in data.get("sectors", []):
        s_id = sector.get("id", "Unknown Sector")
        net_score = sector.get("net_score", 0)
        # Force the label to use the new strict max-5-words key
        edge_label = sector.get("edge_label_max_5_words", "Impact") 
        
        node_color = "#00CC96" if net_score > 0 else ("#FF4B4B" if net_score < 0 else "#D3D3D3")
        
        if s_id not in added_nodes:
            nodes.append(Node(id=s_id, label=f"{s_id}\n(Score: {net_score})", size=25, shape="box", color=node_color))
            added_nodes.add(s_id)
            
        edges.append(Edge(source=event_node_id, target=s_id, label=edge_label, title=sector.get("reasoning", ""), color=node_color))
        
        for stock in sector.get("proxy_stocks", []):
            ticker = stock.get("ticker", "UNKNOWN")
            name = stock.get("name", "Unknown")
            
            if ticker not in added_nodes:
                nodes.append(Node(id=ticker, label=name, size=15, shape="ellipse", color="#808080", title=f"{name} ({ticker})"))
                added_nodes.add(ticker)
                
            edges.append(Edge(source=s_id, target=ticker, color="#A9A9A9"))
            
    config = Config(width="100%", height=450, directed=True, physics=True, hierarchical=False)
    
    if len(nodes) > 1:
        agraph(nodes=nodes, edges=edges, config=config)
    else:
        st.warning("Not enough data to draw the graph.")

    st.divider()

    # --- 3. CHAIN OF THOUGHT (Middle Layer) ---
    st.header("🧠 Chain of Thought")
    with st.status("AI Thinking Trace (Resolving Conflicting Logic)...", expanded=True):
        for step in data.get("thinking_trace", []):
            step_num = step.get('step', '?')
            thought = step.get('thought', '...')
            st.markdown(f"**Step {step_num}:** {thought}")
            
    st.divider()
    
    # --- 4. SECTOR IMPACTS (Cleaned Up) ---
    st.header("🏢 Sector Impacts")
    
    for sector in data.get("sectors", []):
        net_score = sector.get("net_score", 0)
        emoji = "📈" if net_score > 0 else ("📉" if net_score < 0 else "➖")
        
        with st.container(border=True):
            st.subheader(f"{emoji} {sector.get('id')} (Score: {net_score})")
            st.markdown(f"**Agent's Reasoning:** {sector.get('reasoning')}")
            
            citations = sector.get("citations", [])
            if citations:
                st.caption(f"**Based on:** {', '.join(citations)} *(See Reference Library below)*")

    st.divider()

    # --- 5. THE REFERENCE LIBRARY (Bottom Layer) ---
    st.header("📚 Verbatim Source Library")
    st.markdown("These are the exact rules the AI retrieved and was forced to strictly obey.")

    for rule in data.get("raw_rules_established", []):
        with st.expander(f"📖 {rule.get('rule_id')} Documentation", expanded=False):
            st.markdown(f"**Extracted Logic:** {rule.get('rule_text')}")
            st.info(f"**Verbatim Transcript Quote:**\n> *\"{rule.get('quote')}\"*")
            
            video_id = rule.get("video_id", "UNKNOWN")
            if video_id and video_id != "UNKNOWN" and video_id != "N/A":
                youtube_url = f"https://www.youtube.com/watch?v={video_id}"
                st.link_button(f"📺 Watch Source Video on YouTube", youtube_url, key=f"btn_{rule.get('rule_id')}")