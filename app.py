import streamlit as st
import pandas as pd
from datetime import datetime
import traceback

# Import your friend's core classes
from unified_trading_system import UnifiedTradingSystem
from market_data import MarketData
from stock_universe import StockUniverse

# Set browser page configuration
st.set_page_config(
    page_title="AlphaEdge Research Platform",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─── CACHING THE UNIVERSE FOR SPEED ───
@st.cache_data
def load_cached_universe():
    """Reads NSE.json once and caches the symbols list in memory."""
    try:
        return StockUniverse().get_fo_stocks()
    except Exception as e:
        st.error(f"Error loading NSE.json: {e}")
        return []

# ─── PATCHED OVERRIDE FOR THE WEB ───
def run_web_scanner(universe_list, swing_rsi_min, swing_rsi_max, positional_rsi_min, positional_rsi_max):
    """
    Executes the exact logic from unified_trading_system.py, 
    but catches results in a structured list for UI presentation.
    """
    system = UnifiedTradingSystem()
    market = MarketData()
    
    # Override standard universe with what's loaded or selected
    system.universe = universe_list
    
    compiled_results = []
    
    # Progress visualization elements
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    total_stocks = len(universe_list)
    
    for idx, ticker in enumerate(universe_list):
        # Update progress bar
        progress_pct = int(((idx + 1) / total_stocks) * 100)
        progress_bar.progress(progress_pct)
        status_text.text(f"Scanning ({idx + 1}/{total_stocks}): {ticker}")
        
        try:
            daily_raw = market.get_history(ticker, period="6mo", interval="1d")
            
            if daily_raw.empty or len(daily_raw) < 60:
                continue
                
            if isinstance(daily_raw.columns, pd.MultiIndex):
                daily_raw.columns = daily_raw.columns.get_level_values(0)
                
            # Compute indicators
            df_daily = system.calculate_indicators(daily_raw.copy())
            latest_d = df_daily.iloc[-1]
            d_close, d_ema20, d_ema50, d_rsi = float(latest_d['Close']), float(latest_d['EMA_20']), float(latest_d['EMA_50']), float(latest_d['RSI'])
            
            df_weekly = daily_raw.resample('W-FRI').agg({'Open':'first','High':'max','Low':'min','Close':'last','Volume':'sum'}).dropna()
            df_weekly = system.calculate_indicators(df_weekly)
            latest_w = df_weekly.iloc[-1]
            w_close, w_ema20, w_ema50, w_rsi = float(latest_w['Close']), float(latest_w['EMA_20']), float(latest_w['EMA_50']), float(latest_w['RSI'])
            
            ticker_display = ticker.replace('.NS','')
            
            # 🚀 1. Check Swing Conditions (Daily Frame)
            swing_uptrend = d_ema20 > d_ema50
            swing_rsi_ok = swing_rsi_min <= d_rsi <= swing_rsi_max
            swing_pullback = abs(d_close - d_ema20) / d_ema20 <= 0.015
            
            # 📈 2. Check Positional Conditions (Weekly Frame)
            positional_uptrend = w_ema20 > w_ema50
            positional_rsi_ok = positional_rsi_min <= w_rsi <= positional_rsi_max
            positional_pullback = abs(w_close - w_ema20) / w_ema20 <= 0.03
            
            if swing_uptrend and swing_rsi_ok and swing_pullback:
                s_sell, s_buy = system.get_option_strikes(d_close, mode="swing")
                compiled_results.append({
                    "Ticker": ticker_display, "Price": round(d_close, 2), "Mode": "🚀 SWING",
                    "Trend Status": "Strong Uptrend", "RSI": round(d_rsi, 1),
                    "Action Trigger": f"BUY EQUITY (+10%/-5%)", "Option Strategy": f"Sell {s_sell} PE / Buy {s_buy} PE"
                })
            elif positional_uptrend and positional_rsi_ok and positional_pullback:
                p_sell, p_buy = system.get_option_strikes(w_close, mode="positional")
                compiled_results.append({
                    "Ticker": ticker_display, "Price": round(w_close, 2), "Mode": "📈 POSITION",
                    "Trend Status": "Structural Run", "RSI": round(w_rsi, 1),
                    "Action Trigger": f"HOLD MACRO (+25%/-8%)", "Option Strategy": f"Sell {p_sell} PE / Buy {p_buy} PE"
                })
            else:
                compiled_results.append({
                    "Ticker": ticker_display, "Price": round(d_close, 2), "Mode": "💤 Idle",
                    "Trend Status": "No Setup", "RSI": round(d_rsi, 1),
                    "Action Trigger": "Watching indicators", "Option Strategy": "None"
                })
                
        except Exception as e:
            logging.error(f"Error scanning {ticker}: {str(e)}")
            continue
            
    # Clean up status items when finished
    progress_bar.empty()
    status_text.empty()
    
    return pd.DataFrame(compiled_results)

# ─── USER INTERFACE DESIGN ───
st.title("🎯 AlphaEdge Research Platform")
st.caption(f"Platform Booted at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Web UI Core")

# Load symbols list via our secure caching setup
full_universe = load_cached_universe()

# Sidebar Settings Framework
st.sidebar.header("🛠️ Strategy Tuning Panel")

st.sidebar.subheader("Swing Setup (Daily)")
swing_rsi_min = st.sidebar.slider("Min Swing RSI", 10, 90, 45)
swing_rsi_max = st.sidebar.slider("Max Swing RSI", 10, 90, 65)

st.sidebar.subheader("Positional Setup (Weekly)")
position_rsi_min = st.sidebar.slider("Min Positional RSI", 10, 90, 40)
position_rsi_max = st.sidebar.slider("Max Positional RSI", 10, 90, 65)

st.sidebar.markdown("---")
# Allow the user to run either a subset or the complete batch
run_mode = st.sidebar.radio("Scanner Batch Size", ["Test Run (5 Stocks)", "Full F&O Universe"])

if run_mode == "Test Run (5 Stocks)":
    active_universe = full_universe[:5] if full_universe else ["RELIANCE", "TCS", "INFY", "HDFCBANK", "SBIN"]
else:
    active_universe = full_universe

st.sidebar.info(f"Loaded {len(full_universe)} tickers from asset data layer.")

# Execution Trigger Hub
if st.button("🚀 Execute System Scan", type="primary"):
    if not active_universe:
        st.error("Universe contains 0 symbols. Please verify your NSE.json placement.")
    else:
        with st.spinner("Processing technical engines & scraping Yahoo market data..."):
            df_final = run_web_scanner(
                active_universe, 
                swing_rsi_min, swing_rsi_max, 
                position_rsi_min, position_rsi_max
            )
            
        if not df_final.empty:
            # Metrics Row display
            m1, m2, m3 = st.columns(3)
            m1.metric("Total Tracked Assets", len(df_final))
            m2.metric("Active Swing/Position Setups", len(df_final[df_final["Mode"] != "💤 Idle"]))
            m3.metric("Scan Competed at", datetime.now().strftime("%H:%M:%S"))
            
            # Interactive Filter Checkboxes
            st.subheader("📊 Core Trading Engine Dashboard")
            show_only_active = st.checkbox("Filter: Show Active Triggers Only", value=False)
            
            if show_only_active:
                display_df = df_final[df_final["Mode"] != "💤 Idle"]
            else:
                display_df = df_final
                
            # Render interactive dataframe
            st.dataframe(
                display_df,
                use_container_width=True,
                column_config={
                    "Price": st.column_config.NumberColumn(format="₹%.2f"),
                    "RSI": st.column_config.NumberColumn(format="%.1f")
                },
                hide_index=True
            )
            
            # Data Export Utility
            csv_data = display_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Export Report to CSV",
                data=csv_data,
                file_name=f"alphaedge_scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
        else:
            st.warning("Scan executed but returned no structured datasets.")