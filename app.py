import streamlit as st
from streamlit_agraph import agraph, Node, Edge, Config
from retail_agent import analyze_event_logic
import plotly.graph_objects as go
import datetime
from datetime import timedelta
import pandas as pd

st.set_page_config(page_title="Macro Event & Weighting Engine", layout="wide")

st.title("Macro Event & Retail Weighting Visualizer 🕸️")
st.markdown("Select a historical date range. The system will fetch real market news, query Alfred Chen's logic, and visualize the weighted 'tug-of-war' on specific sectors.")

# --- 1. User Input Section ---
st.header("1. Define Macro Environment")

today = datetime.date.today()
default_start = today - timedelta(days=180) # Default to ~6 months ago
default_end = today - timedelta(days=150)

# Date range picker
date_range = st.date_input("Select Historical Period (Start Date - End Date):", value=(default_start, default_end))

if len(date_range) != 2:
    st.warning("Please select both a Start Date and an End Date.")
    st.stop()

start_date, end_date = date_range

if end_date > today:
    st.error("❌ End date cannot be in the future.")
    st.stop()

analyze_button = st.button("Synthesize Macro Impact Graph", type="primary")

st.divider()

if "graph_data" not in st.session_state:
    st.session_state.graph_data = None

# --- 2. Generate Graph Data ---
if analyze_button:
    with st.spinner(f"Fetching news between {start_date} and {end_date} & weighting logic..."):
        st.session_state.graph_data = analyze_macro_period(start_date, end_date)

# --- 3. Render Main View OR Split Screen ---
if st.session_state.graph_data:
    graph_data = st.session_state.graph_data
    
    if "period_summary" in graph_data and "Error" in graph_data["period_summary"]:
        st.error(graph_data["period_summary"])
        st.stop()
        
    st.markdown(f"**Period Summary:** {graph_data.get('period_summary', 'N/A')}")
    
    verify_clicked = st.button("🔍 Verify against Historical Data", type="secondary")
    
    if verify_clicked:
        col_left, col_right = st.columns([1, 1])
    else:
        col_left = st.container()
        col_right = None

    # --- LEFT COLUMN: The Graph ---
    with col_left:
        st.header("Weighted Logic Graph")
        nodes = []
        edges = []
        added_node_ids = set()

        news_events = graph_data.get("news_events", [])
        sector_nodes = graph_data.get("sectors", [])

        # Layer 1: Macro Period (Center)
        nodes.append(Node(id="Macro", label=f"Period:\n{start_date}\nto\n{end_date}", size=35, shape="diamond", color="#2B7CE9"))
        added_node_ids.add("Macro")

        # Layer 2: News Events
        for news in news_events:
            n_id = news.get("id")
            n_title = news.get("headline")
            
            nodes.append(Node(id=n_id, label=n_title[:30]+"...", title=n_title, size=20, shape="ellipse", color="#FFD700")) # Yellow for news
            added_node_ids.add(n_id)
            edges.append(Edge(source="Macro", target=n_id))

        stocks_to_verify = [] 

        # Layer 3 & 4: Sectors & Stocks
        for sector in sector_nodes:
            sector_id = sector.get("id", "Unknown Sector")
            net_score = sector.get("net_score", 0)
            
            # Color Sector based on NET Score
            node_color = "#00CC96" if net_score > 0 else ("#FF4B4B" if net_score < 0 else "#D3D3D3")
            
            if sector_id not in added_node_ids:
                nodes.append(Node(id=sector_id, label=f"{sector_id}\n(Net: {net_score})", size=25, shape="box", color=node_color))
                added_node_ids.add(sector_id)
            
            # Draw Weighted Edges from News to Sector (The Tug of War)
            competing_forces = sector.get("competing_forces", [])
            for force in competing_forces:
                force_news_id = force.get("news_id")
                force_score = force.get("score", 0)
                
                if force_score != 0:
                    edge_color = "#00CC96" if force_score > 0 else "#FF4B4B"
                    is_dashed = abs(force_score) <= 4 # Weak scores are dashed
                    
                    edges.append(Edge(
                        source=force_news_id, 
                        target=sector_id, 
                        label=f"Score: {force_score}", 
                        color=edge_color,
                        dashes=is_dashed,
                        width=max(1, min(abs(force_score), 5)) # Thickness correlates to score strength
                    ))
            
            # Layer 4: Stocks
            proxy_stocks = sector.get("proxy_stocks", [])
            for stock in proxy_stocks:
                ticker = stock.get("ticker")
                name = stock.get("name")
                
                stocks_to_verify.append({
                    "ticker": ticker, "name": name, 
                    "net_score": net_score, "sector": sector_id
                })
                
                if ticker not in added_node_ids:
                    nodes.append(Node(id=ticker, label=name, size=15, shape="square", color="#808080", title=ticker))
                    added_node_ids.add(ticker)
                
                edges.append(Edge(source=sector_id, target=ticker))

        config = Config(width="100%", height=600, directed=True)
        
        if len(nodes) > 1:
            agraph(nodes=nodes, edges=edges, config=config)
            st.caption("💡 *Tip: Arrow thickness indicates the strength of the logic score. Green = Positive Force, Red = Negative Force.*")
        else:
            st.warning("Graph could not be generated.")

        # Show reasoning Expander
        if sector_nodes:
            with st.expander("View Agent Weighting Reasoning", expanded=False):
                for sector in sector_nodes:
                    st.markdown(f"### **{sector.get('id')} (Net Score: {sector.get('net_score')})**")
                    st.write(f"**Final Verdict:** {sector.get('final_verdict')}")
                    st.write(f"**Reasoning:** {sector.get('reasoning')}")
                    st.markdown("#### Competing Forces:")
                    for force in sector.get('competing_forces', []):
                        st.write(f"- News [{force.get('news_id')}]: Score **{force.get('score')}** -> {force.get('reasoning')}")
                    st.markdown("---")
                    
        # Raw Rules Section
        retrieved_sources = graph_data.get("sources_retrieved", [])
        with st.expander("📚 Raw Rules Retrieved from Database", expanded=False):
            if retrieved_sources:
                seen_rules = set()
                for meta in retrieved_sources:
                    if isinstance(meta, dict):
                        logic_rule = meta.get('logic_rule', 'N/A')
                        if logic_rule not in seen_rules:
                            st.info(f"**Source:** `{meta.get('filename')}`\n\n**Logic Rule:** {logic_rule}")
                            seen_rules.add(logic_rule)

    # --- RIGHT COLUMN: The Reality Check (Backtesting) ---
    if col_right and stocks_to_verify:
        with col_right:
            st.header("Empirical Reality Check")
            
            # We fetch data starting 7 days before the period, and ending 30 days AFTER the period
            fetch_start = start_date - timedelta(days=7)
            ideal_end = end_date + timedelta(days=30)
            fetch_end = min(ideal_end, today)
            
            fetch_start_str = fetch_start.strftime('%Y-%m-%d')
            fetch_end_str = fetch_end.strftime('%Y-%m-%d')
            
            correct_predictions = 0
            total_stocks = len(stocks_to_verify)
            
            with st.spinner("Downloading historical market data..."):
                for stock in stocks_to_verify:
                    ticker = stock["ticker"].strip().upper()
                    if not ticker.endswith(".KL"): ticker += ".KL"
                        
                    predicted_net = stock["net_score"]
                    predicted_direction = "POSITIVE" if predicted_net > 0 else ("NEGATIVE" if predicted_net < 0 else "NEUTRAL")
                    
                    with st.container(border=True):
                        st.subheader(f"{stock['name']} (`{ticker}`)")
                        
                        try:
                            df = yf.download(ticker, start=fetch_start_str, end=fetch_end_str, progress=False)
                            if df.empty:
                                st.warning(f"⚠️ No data found.")
                                continue
                                
                            if isinstance(df.columns, pd.MultiIndex):
                                df.columns = df.columns.get_level_values(0)
                            
                            # Safely strip timezone if it exists
                            if getattr(df.index, 'tz', None) is not None:
                                df.index = df.index.tz_localize(None)
                            
                            close_prices = df['Close'].dropna()
                            if len(close_prices) < 2: continue
                                
                            # Calculate Reality vs Prediction
                            price_start = float(close_prices.iloc[0]) 
                            price_end = float(close_prices.iloc[-1])
                            pct_change = float(((price_end - price_start) / price_start) * 100)
                            
                            actually_went_up = pct_change > 0
                            
                            # A Neutral (0) prediction is counted as a failure if the stock moved significantly
                            is_correct = (actually_went_up and predicted_net > 0) or (not actually_went_up and predicted_net < 0)
                            if is_correct: correct_predictions += 1
                                
                            # Plotting with Plotly
                            fig = go.Figure()
                            dates = df.index.tolist()
                            prices = close_prices.values.tolist()
                            
                            fig.add_trace(go.Scatter(x=dates, y=prices, mode='lines', name='Price', line=dict(color='#2B7CE9')))
                            
                            # BULLETPROOF RECTANGLE HIGHLIGHTING THE MACRO PERIOD
                            # We use pure numeric datetimes to avoid Plotly string conversion bugs
                            start_ms = pd.to_datetime(start_date).timestamp() * 1000
                            end_ms = pd.to_datetime(end_date).timestamp() * 1000
                            
                            fig.add_vrect(
                                x0=start_ms, x1=end_ms, 
                                fillcolor="rgba(255, 215, 0, 0.2)", # Transparent Yellow
                                line_width=0, 
                                annotation_text="News Window", 
                                annotation_position="top left"
                            )
                            
                            fig.update_layout(height=250, margin=dict(l=0, r=0, t=30, b=0), xaxis_title="Date", yaxis_title="Price (MYR)")
                            st.plotly_chart(fig, use_container_width=True)
                            
                            verdict_color = "green" if is_correct else "red"
                            st.markdown(f"**Net Prediction:** {predicted_direction} ({predicted_net}) | **Actual:** {pct_change:.2f}% | <span style='color:{verdict_color}'>**Verdict: {'Correct' if is_correct else 'Wrong'}**</span>", unsafe_allow_html=True)
                            
                        except Exception as e:
                            st.error(f"Failed to load chart for {ticker}: {e}")
            
            st.divider()
            st.subheader(f"🧠 Retail Logic Accuracy: {correct_predictions} / {total_stocks}")