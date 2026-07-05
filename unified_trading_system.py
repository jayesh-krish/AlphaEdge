import datetime
import warnings
import pandas as pd
import yfinance as yf


warnings.filterwarnings("ignore")

from scan_result import ScanResult
from market_data import MarketData

class UnifiedTradingSystem:

    def __init__(self):
        from stock_universe import StockUniverse

        self.universe = StockUniverse().get_fo_stocks()
        self.market = MarketData()
        print("MarketData initialized successfully")

    def calculate_indicators(self, df):
        df['EMA_20'] = df['Close'].ewm(span=20, adjust=False).mean()
        df['EMA_50'] = df['Close'].ewm(span=50, adjust=False).mean()
        
        delta = df['Close'].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        avg_gain = gain.ewm(com=13, adjust=False).mean()
        avg_loss = loss.ewm(com=13, adjust=False).mean()
        rs = avg_gain / avg_loss
        df['RSI'] = 100 - (100 / (1 + rs))
        return df

    def get_option_strikes(self, current_price, mode="swing"):
        """Calculates precise strikes for a Margin-Optimized Bull Put Spread"""
        # Rounding off to nearest standard NSE strike intervals
        base_strike = round(current_price / 50) * 50 if current_price < 5000 else round(current_price / 100) * 100
        
        if mode == "swing":
            sell_put_strike = base_strike
            buy_put_strike = sell_put_strike - (base_strike * 0.03)  # Hedged 3% lower
        else:  # Positional mode
            sell_put_strike = base_strike - (base_strike * 0.02)     # Margin cushion OTM entry
            buy_put_strike = sell_put_strike - (base_strike * 0.05)  # Structural protection hedge
            
        # Clear out rounding anomalies
        buy_put_strike = round(buy_put_strike / 50) * 50 if current_price < 5000 else round(buy_put_strike / 100) * 100
        return int(sell_put_strike), int(buy_put_strike)

    def scan_all_strategies(self):
        print("=" * 105)
        print(" 🎯 UNIFIED STRATEGY MULTI-TIMEFRAME DASHBOARD (EQUITY SWING + OPTION SPREAD ENGINE)")
        print("=" * 105)
        print(f"{'Ticker':<12} | {'Price':<10} | {'Mode':<11} | {'Trend Status':<14} | {'RSI':<6} | {'ACTION TRIGGER / OPTIONS ACTION'}")
        print("-" * 105)

        for ticker in self.universe:
            results = (f"Scanning: {ticker}")
            
            try:

                # Fetch raw data
                daily_raw = self.market.get_history(ticker, period="6mo", interval="1d")

                if daily_raw.empty:
                    print(f"{ticker} -> EMPTY DATA")
                    continue

                if len(daily_raw) < 60:
                   print(f"{ticker} -> ONLY {len(daily_raw)} ROWS")
                   continue

                print(f"{ticker} -> {len(daily_raw)} rows downloaded")

                if isinstance(daily_raw.columns, pd.MultiIndex):
                    daily_raw.columns = daily_raw.columns.get_level_values(0)

                # Process Daily (Swing Execution)
                df_daily = self.calculate_indicators(daily_raw.copy())
                latest_d = df_daily.iloc[-1]
                d_close, d_ema20, d_ema50, d_rsi = float(latest_d['Close']), float(latest_d['EMA_20']), float(latest_d['EMA_50']), float(latest_d['RSI'])

                # Process Weekly (Positional Execution)
                df_weekly = daily_raw.resample('W-FRI').agg({'Open':'first','High':'max','Low':'min','Close':'last','Volume':'sum'}).dropna()
                df_weekly = self.calculate_indicators(df_weekly)
                latest_w = df_weekly.iloc[-1]
                w_close, w_ema20, w_ema50, w_rsi = float(latest_w['Close']), float(latest_w['EMA_20']), float(latest_w['EMA_50']), float(latest_w['RSI'])

                ticker_display = ticker.replace('.NS','')

                # 🚀 1. Check Swing Conditions (Daily Frame)
                swing_uptrend = d_ema20 > d_ema50
                swing_rsi_ok = 45 <= d_rsi <= 65
                swing_pullback = abs(d_close - d_ema20) / d_ema20 <= 0.015

                if swing_uptrend and swing_rsi_ok and swing_pullback:
                    s_sell, s_buy = self.get_option_strikes(d_close, mode="swing")
                    results.append(f"{ticker_display:<12} | ₹{d_close:<9.2f} | 🚀 SWING    | Strong Uptrend | {d_rsi:<4.1f} | 🔥 BUY EQUITY (+10%/-5%) or Sell {s_sell} PE / Buy {s_buy} PE Spread")
                    continue

                # 📈 2. Check Positional Conditions (Weekly Frame)
                positional_uptrend = w_ema20 > w_ema50
                positional_rsi_ok = 40 <= w_rsi <= 65
                positional_pullback = abs(w_close - w_ema20) / w_ema20 <= 0.03

                if positional_uptrend and positional_rsi_ok and positional_pullback:
                    p_sell, p_buy = self.get_option_strikes(w_close, mode="positional")
                    results.append(f"{ticker_display:<12} | ₹{w_close:<9.2f} | 📈 POSITION | Structural Run | {w_rsi:<4.1f} | 💎 HOLD MACRO (+25%/-8%) or Sell {p_sell} PE / Buy {p_buy} PE Spread")
                    continue

                # 💤 3. No Setup Available
                results.append(f"{ticker_display:<12} | ₹{d_close:<9.2f} | Idle        | No Setup       | {d_rsi:<4.1f} | Watching structural indicators...")

            except Exception as e:
                print(f"\nERROR in {ticker}")
                print(type(e).__name__)
                print(e)
        print("=" * 105)
        return results

if __name__ == "__main__":
    system = UnifiedTradingSystem()
    system.scan_all_strategies()