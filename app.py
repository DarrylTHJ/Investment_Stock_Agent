import streamlit as st
from streamlit_agraph import agraph, Node, Edge, Config
from retail_agent import analyze_event_impact
import pdfplumber
import yfinance as yf
import plotly.graph_objects as go
import datetime
from datetime import timedelta

st.set_page_config(page_title="Event-Driven Impact Visualizer", layout="wide")

st.title("Event-Driven Market Impact Visualizer 🕸️")
st.markdown("Analyze macroeconomic events and news to visualize the ripple effects on various industries, then backtest against reality.")

# --- 1. User Input Section ---
st.header("1. Input Market Context")

col_input1, col_input2 = st.columns([2, 1])

with col_input1:
    input_type = st.radio("Select Input Mode:", ["Text Description", "Upload PDF Document"], horizontal=True)
    user_input = ""
    if input_type == "Text Description":
        user_input = st.text_area("Describe the event:", "Malaysia announces a complete ban on vapes.")
    else:
        uploaded_file = st.file_uploader("Upload a News Article (PDF)", type="pdf")
        if uploaded_file is not None:
            with st.spinner("Extracting text..."):
                with pdfplumber.open(uploaded_file) as pdf:
                    pages_text = [page.extract_text() for page in pdf.pages[:3] if page.extract_text()]
                    user_input = "\n".join(pages_text)
                st.success("✅ Extracted from PDF!")

with col_input2:
    st.markdown("**Reality Check Setup**")
    # Date picker for backtesting
    event_date = st.date_input("When did this happen? (Required for Backtesting)", value=None)

analyze_button = st.button("Synthesize Impact Graph", type="primary")

st.divider()

# We need session state to hold the graph data so it survives the "Verify" button click
if "graph_data" not in st.session_state:
    st.session_state.graph_data = None

# --- 2. Generate Graph Data ---
if analyze_button and user_input.strip():
    with st.spinner("Retrieving logic rules from Vector DB and synthesizing impact..."):
        st.session_state.graph_data = analyze_event_impact(user_input)

# --- 3. Render Main View OR Split Screen ---
if st.session_state.graph_data:
    graph_data = st.session_state.graph_data
    
    # Check if user clicked Verify
    verify_clicked = st.button("🔍 Verify against Historical Data", type="secondary")
    
    if verify_clicked and event_date:
        # --- SPLIT SCREEN MODE ---
        col_left, col_right = st.columns([1, 1])
    elif verify_clicked and not event_date:
        st.warning("⚠️ Please provide an 'Event Date' at the top to run a Reality Check.")
        col_left = st.container()
        col_right = None
    else:
        # --- DEFAULT FULL SCREEN MODE ---
        col_left = st.container()
        col_right = None

    # --- LEFT COLUMN: The Graph ---
    with col_left:
        st.header("Retail Logic Graph")
        nodes = []
        edges = []
        added_node_ids = set()

        event_name = graph_data.get("event_name", "Trigger Event")
        sector_nodes = graph_data.get("nodes", [])

        # Layer 1: Event
        nodes.append(Node(id="Event", label=f"Event:\n{event_name}", size=35, shape="diamond", color="#2B7CE9"))
        added_node_ids.add("Event")

        stocks_to_verify = [] # Collect stocks for the right column

        for sector in sector_nodes:
            # Layer 2: Sector
            sector_id = sector.get("id", "Unknown Sector")
            impact = sector.get("impact", "POSITIVE").upper()
            
            node_color = "#00CC96" if "POSITIVE" in impact else "#FF4B4B"
            
            if sector_id not in added_node_ids:
                nodes.append(Node(id=sector_id, label=sector_id, size=25, color=node_color))
                added_node_ids.add(sector_id)
            
            edges.append(Edge(source="Event", target=sector_id, label=impact))
            
            # Layer 3: Stocks
            proxy_stocks = sector.get("proxy_stocks", [])
            for stock in proxy_stocks:
                ticker = stock.get("ticker")
                name = stock.get("name")
                desc = stock.get("description")
                
                # Keep track for the Reality Check
                stocks_to_verify.append({
                    "ticker": ticker, "name": name, "desc": desc, 
                    "predicted_impact": impact, "sector": sector_id
                })
                
                if ticker not in added_node_ids:
                    # Draw stocks as smaller, gray squares
                    nodes.append(Node(
                        id=ticker, label=name, size=15, shape="square", color="#808080",
                        title=f"{desc} ({ticker})" # Hover text
                    ))
                    added_node_ids.add(ticker)
                
                edges.append(Edge(source=sector_id, target=ticker))

        config = Config(width="100%", height=500, directed=True, physics=True, collapsible=True)
        
        if len(nodes) > 1:
            agraph(nodes=nodes, edges=edges, config=config)
        else:
            st.warning("No relevant historical rules found to map an impact.")

        # Show reasoning
        if sector_nodes:
            with st.expander("View Agent Reasoning", expanded=False):
                for sector in sector_nodes:
                    impact_icon = "🟢" if "POSITIVE" in sector.get("impact", "").upper() else "🔴"
                    st.markdown(f"{impact_icon} **{sector.get('id')}**: {sector.get('reasoning')}")

    # --- RIGHT COLUMN: The Reality Check (Backtesting) ---
    if col_right and stocks_to_verify:
        with col_right:
            st.header("Empirical Reality Check")
            
            # Calculate dates: 14 days before, 30 days after
            start_date = event_date - timedelta(days=14)
            end_date = event_date + timedelta(days=30)
            
            correct_predictions = 0
            total_stocks = len(stocks_to_verify)
            
            with st.spinner("Downloading historical market data..."):
                for stock in stocks_to_verify:
                    ticker = stock["ticker"]
                    prediction = stock["predicted_impact"]
                    
                    with st.container(border=True):
                        st.subheader(f"{stock['name']} (`{ticker}`)")
                        st.caption(stock['desc'])
                        
                        try:
                            # Fetch yfinance data
                            df = yf.download(ticker, start=start_date, end=end_date, progress=False)
                            
                            if df.empty:
                                st.warning("No data found for this ticker on these dates.")
                                continue
                                
                            # Flatten MultiIndex columns if necessary (yfinance bug workaround)
                            if isinstance(df.columns, pd.MultiIndex):
                                df.columns = df.columns.get_level_values(0)
                            
                            # Calculate accuracy
                            close_prices = df['Close'].dropna()
                            if len(close_prices) < 2:
                                continue
                                
                            price_at_event = close_prices.iloc[0] # Approx starting price
                            price_end = close_prices.iloc[-1]
                            pct_change = ((price_end - price_at_event) / price_at_event) * 100
                            
                            # Did reality match the prediction?
                            actually_went_up = pct_change > 0
                            predicted_up = "POSITIVE" in prediction
                            
                            is_correct = (actually_went_up and predicted_up) or (not actually_went_up and not predicted_up)
                            if is_correct: correct_predictions += 1
                                
                            # Plotting with Plotly
                            fig = go.Figure()
                            fig.add_trace(go.Scatter(x=df.index, y=df['Close'], mode='lines', name='Price'))
                            # Add vertical line for the Event Date
                            fig.add_vline(x=event_date, line_dash="dash", line_color="red", annotation_text="Event Occurred")
                            
                            fig.update_layout(height=250, margin=dict(l=0, r=0, t=30, b=0))
                            st.plotly_chart(fig, use_container_width=True)
                            
                            # Print Verdict
                            verdict_color = "green" if is_correct else "red"
                            st.markdown(f"**Predicted:** {prediction} | **Actual:** {pct_change:.2f}% | <span style='color:{verdict_color}'>**Verdict: {'Correct' if is_correct else 'Wrong'}**</span>", unsafe_allow_html=True)
                            
                        except Exception as e:
                            st.error(f"Failed to load chart: {e}")
            
            # --- FINAL SCORE ---
            st.divider()
            st.subheader(f"🧠 Retail Logic Accuracy: {correct_predictions} / {total_stocks}")