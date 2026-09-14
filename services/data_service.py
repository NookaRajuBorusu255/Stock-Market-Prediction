import os
import time
import pandas as pd
import numpy as np
from config import Config

# Cache for symbols to avoid scanning disk repeatedly
_SYMBOL_CACHE = {}

# Simple LRU-style in-memory cache for parsed+computed DataFrames
# Keyed by symbol, stores (dataframe, mtime_of_file, cache_timestamp)
_DATA_CACHE: dict = {}
_CACHE_TTL_SECONDS = 300  # 5 minutes max staleness

def list_available_symbols():
    """
    Scans dataset folder for Stocks and ETFs and caches them.
    Returns a dictionary structure:
    {
       'AAPL': {'path': '/path/to/aapl.us.txt', 'type': 'Stock'},
       'AADR': {'path': '/path/to/aadr.us.txt', 'type': 'ETF'}
    }
    """
    global _SYMBOL_CACHE
    if _SYMBOL_CACHE:
        return _SYMBOL_CACHE
        
    symbols = {}
    
    # 1. Scan Stocks
    stocks_dir = os.path.join(Config.DATASET_PATH, 'Stocks')
    if os.path.exists(stocks_dir):
        for fname in os.listdir(stocks_dir):
            if fname.endswith('.txt'):
                symbol = fname.split('.')[0].upper()
                symbols[symbol] = {
                    'path': os.path.join(stocks_dir, fname),
                    'type': 'Stock',
                    'filename': fname
                }
                
    # 2. Scan ETFs
    etfs_dir = os.path.join(Config.DATASET_PATH, 'ETFs')
    if os.path.exists(etfs_dir):
        for fname in os.listdir(etfs_dir):
            if fname.endswith('.txt'):
                symbol = fname.split('.')[0].upper()
                # If there's a clash, prefix ETF or mark type
                symbols[symbol] = {
                    'path': os.path.join(etfs_dir, fname),
                    'type': 'ETF',
                    'filename': fname
                }
                
    # 3. Scan Uploads
    if os.path.exists(Config.UPLOAD_FOLDER):
        for fname in os.listdir(Config.UPLOAD_FOLDER):
            if fname.endswith('.csv') or fname.endswith('.txt'):
                symbol = fname.split('.')[0].upper()
                symbols[symbol] = {
                    'path': os.path.join(Config.UPLOAD_FOLDER, fname),
                    'type': 'Upload',
                    'filename': fname
                }
                
    _SYMBOL_CACHE = symbols
    return _SYMBOL_CACHE

def refresh_symbol_cache():
    global _SYMBOL_CACHE
    _SYMBOL_CACHE = {}
    return list_available_symbols()

def get_stock_data(symbol):
    """
    Loads stock data from file, parses date, computes technical indicators, and returns a DataFrame.
    Results are cached in-memory for _CACHE_TTL_SECONDS or until the source file changes.
    """
    symbol = symbol.upper()
    symbols = list_available_symbols()

    if symbol not in symbols:
        raise ValueError(f"Symbol '{symbol}' not found in database or uploads.")

    filepath = symbols[symbol]['path']
    now = time.time()

    # Check in-memory cache — invalidate if file changed or TTL expired
    if symbol in _DATA_CACHE:
        cached_df, cached_mtime, cached_at = _DATA_CACHE[symbol]
        try:
            current_mtime = os.path.getmtime(filepath)
        except OSError:
            current_mtime = 0
        if current_mtime == cached_mtime and (now - cached_at) < _CACHE_TTL_SECONDS:
            return cached_df.copy()

    # Parse from disk
    df = parse_and_standardize_csv(filepath)

    if 'Date' in df.columns:
        df['Date'] = pd.to_datetime(df['Date'])
        df = df.sort_values('Date').reset_index(drop=True)
    else:
        raise ValueError("Dataset does not contain a 'Date' column.")

    required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"Dataset missing required column: {col}")

    df = compute_indicators(df)

    # Store in cache
    try:
        file_mtime = os.path.getmtime(filepath)
    except OSError:
        file_mtime = 0
    _DATA_CACHE[symbol] = (df, file_mtime, now)

    return df.copy()


def invalidate_stock_cache(symbol: str | None = None):
    """Clear cached parsed data — call after an upload replaces a symbol's file."""
    global _DATA_CACHE
    if symbol:
        _DATA_CACHE.pop(symbol.upper(), None)
    else:
        _DATA_CACHE.clear()

def compute_indicators(df):
    """
    Computes all standard technical indicators on a stock DataFrame.
    Assumes df has 'Close', 'Open', 'High', 'Low', 'Volume' and is sorted chronologically.
    """
    df = df.copy()

    # 1. Simple Moving Averages (SMA)
    df['SMA_20']  = df['Close'].rolling(window=20).mean()
    df['SMA_50']  = df['Close'].rolling(window=50).mean()
    df['SMA_200'] = df['Close'].rolling(window=200).mean()

    # 2. Exponential Moving Averages (EMA)
    df['EMA_12'] = df['Close'].ewm(span=12, adjust=False).mean()
    df['EMA_26'] = df['Close'].ewm(span=26, adjust=False).mean()

    # 3. MACD
    df['MACD']        = df['EMA_12'] - df['EMA_26']
    df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    df['MACD_Hist']   = df['MACD'] - df['MACD_Signal']

    # 4. RSI (14-day Wilder smoothing)
    delta    = df['Close'].diff()
    gain     = delta.where(delta > 0, 0.0)
    loss     = (-delta.where(delta < 0, 0.0))
    avg_gain = gain.rolling(window=14).mean()
    avg_loss = loss.rolling(window=14).mean()
    rs       = avg_gain / (avg_loss + 1e-10)
    df['RSI'] = 100 - (100 / (1 + rs))

    # 5. Annualized Volatility (20-day rolling σ of daily returns)
    daily_returns  = df['Close'].pct_change()
    df['Volatility'] = daily_returns.rolling(window=20).std() * np.sqrt(252)

    # 6. Bollinger Bands (20-day, 2σ)
    bb_mid          = df['Close'].rolling(window=20).mean()
    bb_std          = df['Close'].rolling(window=20).std()
    df['BB_Mid']    = bb_mid
    df['BB_Upper']  = bb_mid + 2 * bb_std
    df['BB_Lower']  = bb_mid - 2 * bb_std
    df['BB_Width']  = (df['BB_Upper'] - df['BB_Lower']) / (bb_mid + 1e-10)  # normalised band width

    return df


def parse_and_standardize_csv(filepath):
    """
    Parses a CSV/TXT file robustly by detecting the delimiter, identifying
    the header row (skipping metadata/empty lines), mapping column synonyms,
    and returning a standardized DataFrame.
    """
    import csv
    
    required_keywords = {'date', 'open', 'high', 'low', 'close', 'volume'}
    synonyms = {
        'Date': ['Date', 'Timestamp', 'Datetime', 'Time', 'Date (gmt)', 'Date(utc)'],
        'Open': ['Open', 'Open price', 'Opening price'],
        'High': ['High', 'High price'],
        'Low': ['Low', 'Low price'],
        'Close': ['Close', 'Close price', 'Last', 'Last price', 'Adj close'],
        'Volume': ['Volume', 'Vol', 'Volume traded', 'Turnover']
    }
    
    header_idx = 0
    delim = ','
    
    # Step 1: Detect header row and delimiter
    try:
        with open(filepath, 'r', encoding='utf-8-sig', errors='ignore') as f:
            sample = ""
            for _ in range(15):
                line = f.readline()
                if not line:
                    break
                sample += line
            f.seek(0)
            
            # Detect delimiter
            if sample.strip():
                try:
                    dialect = csv.Sniffer().sniff(sample)
                    delim = dialect.delimiter
                except Exception:
                    # Fallback sniff
                    first_line = sample.split('\n')[0]
                    for d in [';', '\t', ',']:
                        if d in first_line:
                            delim = d
                            break
            
            # Find the header row (scan up to 20 lines)
            reader = csv.reader(f, delimiter=delim)
            non_blank_idx = 0
            for row in reader:
                if not row or not any(c.strip() for c in row):
                    continue
                if non_blank_idx >= 20:
                    break
                normalized_cols = {str(c).strip().lstrip('\ufeff').lower() for c in row if c}
                if len(required_keywords.intersection(normalized_cols)) >= 4:
                    header_idx = non_blank_idx
                    break
                non_blank_idx += 1
    except Exception:
        pass
        
    # Step 2: Read file using the detected header row and delimiter
    try:
        df = pd.read_csv(filepath, encoding='utf-8-sig', sep=delim, header=header_idx, engine='python')
    except Exception:
        try:
            df = pd.read_csv(filepath, encoding='utf-8-sig', header=header_idx)
        except Exception:
            df = pd.read_csv(filepath, encoding='utf-8-sig')
            
    # Step 3: Clean and standardize column names
    df.columns = [str(c).strip().lstrip('\ufeff').title() for c in df.columns]
    
    # Map synonyms to required names
    rename_dict = {}
    for col in df.columns:
        for target, syn_list in synonyms.items():
            if col in syn_list or col.lower() in [s.lower() for s in syn_list]:
                if target not in df.columns or col == target:
                    rename_dict[col] = target
                    break
                    
    if rename_dict:
        df.rename(columns=rename_dict, inplace=True)
        
    # Keep only the standardized columns and verify (check lowercase synonyms just in case)
    required = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']
    for req in required:
        if req not in df.columns:
            lower_cols = {c.lower(): c for c in df.columns}
            if req.lower() in lower_cols:
                df.rename(columns={lower_cols[req.lower()]: req}, inplace=True)
                
    return df

