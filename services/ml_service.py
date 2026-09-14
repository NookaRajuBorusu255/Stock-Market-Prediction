import os
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from xgboost import XGBRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import joblib

from config import Config
from services.data_service import get_stock_data
from database.database_helper import save_model_performance
from database.models import ModelPerformance

def prepare_ml_data(df):
    """
    Creates lag features and aligns target variables for forecasting tomorrow's close.
    Features used: Close lags (1-5), Open/High/Low/Volume lags (1-5), and technical indicator lags.
    Target: Tomorrow's close price.
    """
    df = df.copy()
    features = []
    
    # Lag primary pricing and volume by 1 to 5 days
    for lag in range(1, 6):
        df[f'Close_lag_{lag}'] = df['Close'].shift(lag)
        df[f'Open_lag_{lag}'] = df['Open'].shift(lag)
        df[f'High_lag_{lag}'] = df['High'].shift(lag)
        df[f'Low_lag_{lag}'] = df['Low'].shift(lag)
        df[f'Volume_lag_{lag}'] = df['Volume'].shift(lag)
        features.extend([
            f'Close_lag_{lag}', 
            f'Open_lag_{lag}', 
            f'High_lag_{lag}', 
            f'Low_lag_{lag}', 
            f'Volume_lag_{lag}'
        ])
        
    # Lag technical indicators by 1 day (using today's indicator to predict tomorrow)
    indicator_cols = ['SMA_20', 'SMA_50', 'SMA_200', 'MACD', 'MACD_Signal', 'RSI', 'Volatility']
    for col in indicator_cols:
        if col in df.columns:
            df[f'{col}_lag_1'] = df[col].shift(1)
            features.append(f'{col}_lag_1')
            
    # Target is tomorrow's Close (since features are t-1 relative to Close t)
    df['Target'] = df['Close']
    
    # Drop rows with NaNs from shifts/rolling window
    df_clean = df.dropna(subset=features + ['Target']).reset_index(drop=True)
    
    X = df_clean[features]
    y = df_clean['Target']
    
    return X, y, df_clean

def train_and_evaluate_models(symbol):
    """
    Loads stock data, trains Linear Regression, Random Forest, and XGBoost,
    evaluates them sequentially (chronologically), caches performance in DB,
    and returns performance summaries.
    """
    # 1. Load data
    df = get_stock_data(symbol)
    
    # 2. Extract features and target
    X, y, df_clean = prepare_ml_data(df)
    
    if len(X) < 100:
        raise ValueError(f"Insufficient stock data for symbol '{symbol}'. Minimum 100 records required.")
        
    # 3. Sequential Chronological Split (80% train, 20% test)
    split_idx = int(len(X) * 0.8)
    X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
    y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]
    
    # Ensure models directory exists
    os.makedirs(Config.MODELS_FOLDER, exist_ok=True)
    
    results = {}
    
    # 4. Models Configuration
    models = {
        'Linear Regression': LinearRegression(),
        'Random Forest': RandomForestRegressor(n_estimators=100, random_state=42, max_depth=10),
        'XGBoost': XGBRegressor(n_estimators=100, learning_rate=0.05, max_depth=6, random_state=42)
    }
    
    # 5. Loop through models, fit, predict, evaluate, and save
    for name, model in models.items():
        # Fit
        model.fit(X_train, y_train)
        
        # Predict on test set
        preds = model.predict(X_test)
        
        # Calculate Metrics
        mae = float(mean_absolute_error(y_test, preds))
        rmse = float(np.sqrt(mean_squared_error(y_test, preds)))
        r2 = float(r2_score(y_test, preds))
        
        # Avoid division by zero in MAPE
        y_test_np = y_test.to_numpy()
        mape = float(np.mean(np.abs((y_test_np - preds) / (y_test_np + 1e-10))) * 100)
        
        # Save model file
        model_filename = f"{symbol.lower()}_{name.lower().replace(' ', '_')}.joblib"
        model_path = os.path.join(Config.MODELS_FOLDER, model_filename)
        joblib.dump(model, model_path)
        
        # Cache performance details in SQLite
        save_model_performance(symbol, name, mae, rmse, r2, mape)
        
        results[name] = {
            'mae': mae,
            'rmse': rmse,
            'r2': r2,
            'mape': mape,
            'test_actuals': y_test.tolist(),
            'test_predictions': preds.tolist(),
            'test_dates': df_clean['Date'].iloc[split_idx:].dt.strftime('%Y-%m-%d').tolist()
        }
        
    return results

def load_ml_model_and_predict(symbol, model_name):
    """
    Loads a saved classical model and predicts the NEXT trading day's price.
    Returns: (predicted_price, confidence_score)
    """
    symbol = symbol.upper()
    model_filename = f"{symbol.lower()}_{model_name.lower().replace(' ', '_')}.joblib"
    model_path = os.path.join(Config.MODELS_FOLDER, model_filename)
    
    if not os.path.exists(model_path):
        # Model not trained yet, train it now
        train_and_evaluate_models(symbol)
        
    model = joblib.load(model_path)
    
    # Fetch data and prepare last row for next-day prediction
    df = get_stock_data(symbol)
    X, _, df_clean = prepare_ml_data(df)
    
    # The last row of df_clean contains the t-1 features aligned for predicting tomorrow (t)
    last_features = X.iloc[-1:]
    
    # Predict
    predicted_val = float(model.predict(last_features)[0])
    
    # Calculate confidence score based on performance metrics cached
    perf = ModelPerformance.query.filter_by(stock_symbol=symbol, model_name=model_name).first()
    
    # Baseline confidence formula using R2
    if perf:
        r2_conf = max(0, min(100, perf.r2 * 100))
        mape_conf = max(0, min(100, 100 - perf.mape))
        confidence = (r2_conf * 0.4) + (mape_conf * 0.6)
    else:
        confidence = 75.0  # Default fallback if performance record is missing
        
    return predicted_val, float(confidence)
