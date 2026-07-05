"""
market_data.py
======================
AlphaEdge Market Data Layer

Purpose:
    Single source of market data for the entire platform.

Future Providers:
    - Yahoo Finance
    - NSE
    - Upstox
    - Angel One
    - Zerodha
    - Local Database

Author: AlphaEdge
"""

import time
import logging
from functools import lru_cache

import pandas as pd
import yfinance as yf

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)


class MarketData:
    """Centralized market data provider."""

    # Yahoo ticker exceptions
    SYMBOL_MAP = {
        # Add exceptions here when required
        # "MOTHERSUMI": "MSUMI.NS",
        # "XYZ": "ABC.NS",
    }

    def __init__(
        self,
        period="6mo",
        interval="1d",
        auto_adjust=True,
        retries=3,
        retry_delay=2,
    ):
        self.period = period
        self.interval = interval
        self.auto_adjust = auto_adjust
        self.retries = retries
        self.retry_delay = retry_delay

    @classmethod
    @lru_cache(maxsize=512)
    def yahoo_symbol(cls, symbol: str) -> str:
        """
        Convert NSE symbol into Yahoo Finance symbol.
        """

        symbol = symbol.strip().upper()

        if symbol in cls.SYMBOL_MAP:
            return cls.SYMBOL_MAP[symbol]

        return f"{symbol}.NS"

    def get_history(
        self,
        symbol: str,
        period=None,
        interval=None,
    ) -> pd.DataFrame:
        """
        Download historical OHLCV data.

        Returns
        -------
        pandas.DataFrame
        """

        ticker = self.yahoo_symbol(symbol)

        period = period or self.period
        interval = interval or self.interval

        last_exception = None

        for attempt in range(1, self.retries + 1):

            try:

                df = yf.download(
                    ticker,
                    period=period,
                    interval=interval,
                    auto_adjust=self.auto_adjust,
                    progress=False,
                    threads=False,
                )

                if df.empty:
                    raise ValueError("No data returned.")

                # Flatten MultiIndex if necessary
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)

                df = df.dropna()

                return df

            except Exception as e:

                last_exception = e

                logging.warning(
                    f"{ticker} | Attempt {attempt}/{self.retries} failed."
                )

                time.sleep(self.retry_delay)

        logging.error(
            f"Failed to download {ticker}: {last_exception}"
        )

        return pd.DataFrame()

    def validate(self, df: pd.DataFrame) -> bool:
        """
        Basic OHLC validation.
        """

        if df.empty:
            return False

        required = [
            "Open",
            "High",
            "Low",
            "Close",
            "Volume",
        ]

        for col in required:
            if col not in df.columns:
                return False

        if len(df) < 50:
            return False

        return True