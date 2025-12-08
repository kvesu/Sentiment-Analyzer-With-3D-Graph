"""
unified_price_scripts.py

Single place to handle all price fetching, cleaning, and caching.

Used by:
- predict_stock_price.py (live predictions)
- (optional later) train_regressor.py (training)
"""

import os
from datetime import datetime, timedelta

import pandas as pd
import yfinance as yf


# Where we cache price data on disk
DEFAULT_CACHE_DIR = "price_data_cache"


def _ensure_cache_dir(cache_dir: str = DEFAULT_CACHE_DIR) -> str:
    """Make sure the cache directory exists and return its path."""
    if not os.path.isdir(cache_dir):
        os.makedirs(cache_dir, exist_ok=True)
    return cache_dir


def _build_cache_path(
    ticker: str,
    start_date: str,
    end_date: str,
    interval: str,
    cache_dir: str = DEFAULT_CACHE_DIR,
) -> str:
    """
    Build a consistent cache filename for a given ticker/date range/interval.
    Example: price_data_cache/AAPL_1d_2024-01-01_2024-12-31.csv
    """
    _ensure_cache_dir(cache_dir)
    safe_ticker = ticker.replace("/", "_").upper()
    fname = f"{safe_ticker}_{interval}_{start_date}_{end_date}.csv"
    return os.path.join(cache_dir, fname)


def _is_cache_fresh(cache_path: str, max_age_hours: int = 6) -> bool:
    """
    Decide whether to reuse a cached file.
    For live prediction, we don't want super-stale data.
    """
    if not os.path.isfile(cache_path):
        return False

    mtime = datetime.fromtimestamp(os.path.getmtime(cache_path))
    age = datetime.now() - mtime
    return age.total_seconds() < max_age_hours * 3600


def get_price_history(
    ticker: str,
    start_date: str,
    end_date: str,
    interval: str = "1d",
    cache_dir: str = DEFAULT_CACHE_DIR,
    max_cache_age_hours: int = 6,
) -> pd.DataFrame:
    """
    Unified price loader.

    - Checks cache first (if fresh enough)
    - Otherwise downloads from yfinance
    - Cleans columns
    - Returns a DataFrame with standard columns:
      ['date', 'open', 'high', 'low', 'close', 'adj_close', 'volume']

    Parameters
    ----------
    ticker : str
        Stock symbol, e.g. 'AAPL'
    start_date : str
        'YYYY-MM-DD'
    end_date : str
        'YYYY-MM-DD'
    interval : str
        yfinance interval, e.g. '1d', '1h'
    cache_dir : str
        Directory to store cached CSV files
    max_cache_age_hours : int
        How old cache can be before we force a refresh

    Returns
    -------
    pd.DataFrame
    """
    cache_path = _build_cache_path(
        ticker=ticker,
        start_date=start_date,
        end_date=end_date,
        interval=interval,
        cache_dir=cache_dir,
    )

    # 1) Try cache
    if _is_cache_fresh(cache_path, max_cache_age_hours):
        try:
            df = pd.read_csv(cache_path, parse_dates=["date"])
            df = df.sort_values("date").reset_index(drop=True)
            return df
        except Exception:
            # If cache is corrupted, we fall back to download
            pass

    # 2) Download from yfinance
    df = yf.download(
        ticker,
        start=start_date,
        end=end_date,
        interval=interval,
        auto_adjust=False,
        progress=False,
    )

    if df.empty:
        # Return an empty, correctly-shaped DataFrame
        return pd.DataFrame(
            columns=[
                "date",
                "open",
                "high",
                "low",
                "close",
                "adj_close",
                "volume",
            ]
        )

    # 3) Normalize columns
    df = df.rename(
        columns={
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Adj Close": "adj_close",
            "Volume": "volume",
        }
    )

    # Move index (DatetimeIndex) into a 'date' column
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index, errors="coerce")

    df["date"] = df.index
    df = df[["date", "open", "high", "low", "close", "adj_close", "volume"]]
    df = df.sort_values("date").reset_index(drop=True)

    # 4) Save to cache
    try:
        df.to_csv(cache_path, index=False)
    except Exception:
        # If we can't write cache, just ignore - not fatal
        pass

    return df


def get_recent_price_window(
    ticker: str,
    lookback_days: int = 90,
    interval: str = "1d",
    cache_dir: str = DEFAULT_CACHE_DIR,
    max_cache_age_hours: int = 6,
) -> pd.DataFrame:
    """
    Convenience wrapper: ask for the last N days of prices.

    Returns the same standardized DataFrame as get_price_history().
    """
    end = datetime.today().date()
    start = end - timedelta(days=lookback_days)
    return get_price_history(
        ticker=ticker,
        start_date=start.strftime("%Y-%m-%d"),
        end_date=end.strftime("%Y-%m-%d"),
        interval=interval,
        cache_dir=cache_dir,
        max_cache_age_hours=max_cache_age_hours,
    )
