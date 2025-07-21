import streamlit as st
import os
import pandas as pd
import json
from streamlit.components.v1 import html
import hashlib
import yaml
from yaml.loader import SafeLoader
import streamlit_authenticator as stauth

# Set page config first
st.set_page_config(page_title="Unfilled Wick Analysis", layout="wide")

# Load config file for authentication
with open('.streamlit/config.yaml') as file:
    config = yaml.load(file, Loader=SafeLoader)

# Create the authenticator
authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days']
)

# Check authentication
if 'authentication_status' not in st.session_state or not st.session_state['authentication_status']:
    st.switch_page("landing.py")

username = st.session_state['username']

# Add logout button in sidebar
authenticator.logout("Logout", "sidebar")

# Debug information
# Rest of your imports
from binance_utils import get_binance_client, get_binance_futures_pairs, get_historical_klines
from data_processing import identify_unfilled_wicks, prepare_chart_data
from chart_utils import html_content
from config import ALL_TIMEFRAMES, SIDEBAR_MARKDOWN
from db_utils import log_search, get_user_stats

# Custom CSS to improve the app's appearance
st.markdown("""
<style>
    .stApp {
        max-width: 1200px;
        margin: 0 auto;
    }
    .stButton>button {
        width: 100%;
    }
    .stProgress .st-bo {
        background-color: #4CAF50;
    }
</style>
""", unsafe_allow_html=True)

# Initialize Binance client
client = get_binance_client()
if not client:
    st.stop()

# Streamlit App
st.title("Because Wicks Don't Lie")

st.markdown("""
This app analyzes cryptocurrency price data to identify unfilled wick patterns on various timeframes.
Unfilled wicks can potentially indicate areas of interest for traders.

### How to use:
1. Select cryptocurrency pair(s) from the dropdown menu.
2. Choose the timeframes you want to analyze.
3. Adjust the analysis parameters using the sliders.
4. Click the "Analyze Unfilled Wicks" button to start the analysis.
5. Review the aggregated results for each timeframe across all selected pairs.
""")

# Sidebar for user inputs
st.sidebar.header("Analysis Parameters")

binance_futures_pairs = get_binance_futures_pairs()
if not binance_futures_pairs:
    st.stop()

# Multi-select for symbols
selected_symbols = st.sidebar.multiselect("Select Symbol(s)", binance_futures_pairs, default=["BTCUSDT"])

# Multi-select for timeframes
selected_timeframes = st.sidebar.multiselect("Select Timeframe(s)", ALL_TIMEFRAMES,
                                             default=['1m', '2m', '3m', '4m', '5m'])

st.sidebar.markdown("### Wick Ratio")
st.sidebar.markdown("Higher values require longer wicks relative to the candle body.")
wick_ratio = st.sidebar.slider("Wick Ratio", 0.7, 0.95, 0.7, 0.01)

st.sidebar.markdown("### Body Threshold")
st.sidebar.markdown("Lower values allow for smaller candle bodies.")
body_threshold = st.sidebar.slider("Body Threshold", 0.01, 0.2, 0.03, 0.01)

st.sidebar.markdown("### Candle Size Multiplier")
st.sidebar.markdown("Adjusts the minimum candle size considered for analysis.")
candle_size_multiplier = st.sidebar.slider("Candle Size Multiplier", 0.1, 3.0, 1.0, 0.1)

st.sidebar.markdown("### Minimum Unfilled Wick Percentage")
st.sidebar.markdown("Higher values require a larger portion of the wick to remain unfilled.")
min_unfilled_percentage = st.sidebar.slider("Minimum Unfilled Wick %", 0.0, 1.0, 0.6, 0.05)

st.sidebar.markdown("### Analysis Settings")
top_n = st.sidebar.number_input("Number of top wicks to display per timeframe", 5, 50, 10, 1)
candle_limit = st.sidebar.number_input("Number of candles to analyze per timeframe", 100, 40000, 20000, 50)


@st.cache_data
def analyze_symbol_timeframe(symbol, tf, wick_ratio, body_threshold, candle_size_multiplier, min_unfilled_percentage,
                             candle_limit):
    df = get_historical_klines(symbol, tf, limit=candle_limit)
    if not df.empty:
        unfilled_wicks = identify_unfilled_wicks(df, wick_ratio, body_threshold, candle_size_multiplier,
                                                 min_unfilled_percentage)
        if not unfilled_wicks.empty:
            unfilled_wicks['symbol'] = symbol
            return unfilled_wicks
    return pd.DataFrame()


if st.button("Analyze Unfilled Wicks"):
    if not selected_symbols:
        st.warning("Please select at least one symbol to analyze.")
    elif not selected_timeframes:
        st.warning("Please select at least one timeframe to analyze.")
    else:
        # Log the search
        log_search(username, selected_symbols, selected_timeframes)
        
        # Get and display user stats
        stats = get_user_stats(username)
        with st.sidebar:
            st.markdown("### Your Stats")
            st.metric("Total Searches", stats['total_searches'])
            if stats['top_symbols']:
                st.markdown("#### Most Searched Symbols")
                for symbol, count in stats['top_symbols']:
                    st.text(f"{symbol}: {count} searches")

        # Initialize a dictionary to store aggregated results for each timeframe
        aggregated_results = {tf: [] for tf in selected_timeframes}
        no_patterns_found = []

        progress_bar = st.progress(0)
        status_text = st.empty()

        total_iterations = len(selected_symbols) * len(selected_timeframes)
        current_iteration = 0

        for symbol in selected_symbols:
            for tf in selected_timeframes:
                status_text.text(f"Analyzing {symbol} on {tf} timeframe...")

                result = analyze_symbol_timeframe(symbol, tf, wick_ratio, body_threshold, candle_size_multiplier,
                                                  min_unfilled_percentage, candle_limit)

                if not result.empty:
                    aggregated_results[tf].append(result)
                else:
                    no_patterns_found.append(f"{symbol} on {tf} timeframe")

                current_iteration += 1
                progress_bar.progress(current_iteration / total_iterations)

        status_text.text("Analysis complete!")
        progress_bar.empty()

        # Display summary of pairs and timeframes with no patterns found
        if no_patterns_found:
            with st.expander("Pairs and timeframes with no unfilled wick patterns", expanded=False):
                st.write("No unfilled wick patterns were found for the following:")
                for item in no_patterns_found:
                    st.write(f"- {item}")
        else:
            st.success("Unfilled wick patterns were found for all analyzed pairs and timeframes.")

        # Display aggregated results for each timeframe
        for tf in selected_timeframes:
            if aggregated_results[tf]:
                st.subheader(f"Aggregated Results for {tf} Timeframe")
                combined_df = pd.concat(aggregated_results[tf], ignore_index=True)
                combined_df = combined_df.nlargest(top_n, 'score')
                st.dataframe(combined_df)

                # Add an expander for individual symbol charts
                with st.expander(f"View Individual Charts for {tf} Timeframe", expanded=False):
                    for symbol in selected_symbols:
                        symbol_df = combined_df[combined_df['symbol'] == symbol]
                        if not symbol_df.empty:
                            st.write(f"Candlestick Chart for {symbol}")
                            df = get_historical_klines(symbol, tf, limit=candle_limit)
                            chart_data, wick_lines = prepare_chart_data(df, symbol_df)

                            # Render TradingView Lite chart
                            chart_html = html_content.replace('{{ data }}', json.dumps(chart_data)).replace(
                                '{{ wick_lines }}', json.dumps(wick_lines))
                            html(chart_html, height=600)

st.markdown("""
### Interpretation Guide:
- **Score**: Higher scores indicate potentially more significant unfilled wicks.
- **Wick Type**: 'Upper' wicks may indicate resistance, while 'Lower' wicks may indicate support.
- **Volume**: Higher volume can add more weight to the pattern's significance.
- **Symbol**: The cryptocurrency pair where the pattern was identified.
- **Unfilled Percentage**: The percentage of the wick that remains unfilled. Higher values may indicate stronger potential for the wick to be filled in the future.

Remember that this analysis is based on historical data and should not be used as the sole basis for trading decisions. Always combine technical analysis with fundamental analysis and proper risk management.
""")

st.sidebar.markdown(SIDEBAR_MARKDOWN)