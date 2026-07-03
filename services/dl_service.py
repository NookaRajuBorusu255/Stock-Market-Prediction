import os
import numpy as np
import pandas as pd
import joblib

from config import Config
from services.data_service import get_stock_data
from database.database_helper import save_model_performance


# Check if TensorFlow is available (prevents DLL import crash)
HAS_TENSORFLOW = True
try:
    from tensorflow.keras.models import Sequential, load_model
    from tensorflow.keras.layers import LSTM, Dense, Dropout
    from tensorflow.keras.callbacks import Callback
except (ImportError, OSError):
    HAS_TENSORFLOW = False

class EpochHistoryCallback:
    """Captures per-epoch loss values during training."""
    def __init__(self):
        self.losses = []
        self.val_losses = []


def _get_keras():
    """
    Lazy import of TensorFlow/Keras — deferred to first LSTM call.
    This prevents the server from crashing at startup if the VC++ DLL is missing.
    """
    try:
        from tensorflow.keras.models import Sequential, load_model
        from tensorflow.keras.layers import LSTM, Dense, Dropout
        from tensorflow.keras.callbacks import Callback
        return Sequential, load_model, LSTM, Dense, Dropout, Callback
    except ImportError as e:
        raise RuntimeError(
            f"TensorFlow could not be loaded: {e}\n"
            "Please install the Microsoft C++ Redistributable from:\n"
            "https://support.microsoft.com/help/2977003/the-latest-supported-visual-c-downloads"
        )


def train_lstm_model(symbol, lookback=60, epochs=5, batch_size=32):
    """
    Trains an LSTM network (or MLP Neural Net fallback) on historical Close prices.
    Uses only the last 1000 days of data for computational efficiency on local CPU.
    Returns training history (loss/val_loss), test metrics, and evaluation data.
    """
    if not HAS_TENSORFLOW:
        from sklearn.neural_network import MLPRegressor
        from sklearn.preprocessing import MinMaxScaler

        df = get_stock_data(symbol)
        if len(df) > 1000:
            df = df.iloc[-1000:].reset_index(drop=True)

        close_prices = df['Close'].values.reshape(-1, 1)

        # Scale data
        scaler = MinMaxScaler(feature_range=(0, 1))
        scaled_data = scaler.fit_transform(close_prices)

        # Save the fitted scaler
        os.makedirs(Config.MODELS_FOLDER, exist_ok=True)
        scaler_path = os.path.join(Config.MODELS_FOLDER, f"{symbol.lower()}_lstm_scaler.joblib")
        joblib.dump(scaler, scaler_path)

        # Prepare sequence data
        X, y = [], []
        for i in range(lookback, len(scaled_data)):
            X.append(scaled_data[i - lookback:i, 0])
            y.append(scaled_data[i, 0])

        X, y = np.array(X), np.array(y)

        if len(X) < 50:
            raise ValueError(f"Insufficient data for {symbol} after applying {lookback}-day window.")

        # Sequential chronological split (80/20)
        split_idx = int(len(X) * 0.8)
        X_train, X_test = X[:split_idx], X[split_idx:]
        y_train, y_test = y[:split_idx], y[split_idx:]

        # MLP fallback model simulating LSTM layers with hidden sizes
        model = MLPRegressor(
            hidden_layer_sizes=(30, 15), 
            random_state=42, 
            warm_start=True
        )

        losses = []
        val_losses = []

        # Run training loop for epochs to track loss trajectory
        for epoch in range(epochs):
            model.partial_fit(X_train, y_train)
            train_loss = float(np.mean((y_train - model.predict(X_train)) ** 2))
            val_loss = float(np.mean((y_test - model.predict(X_test)) ** 2))
            losses.append(train_loss)
            val_losses.append(val_loss)

        # Save trained MLP model
        model_path = os.path.join(Config.MODELS_FOLDER, f"{symbol.lower()}_lstm_model.joblib")
        joblib.dump(model, model_path)

        # Evaluate on test set
        scaled_predictions = model.predict(X_test)
        actuals = scaler.inverse_transform(y_test.reshape(-1, 1)).flatten().tolist()
        predictions = scaler.inverse_transform(scaled_predictions.reshape(-1, 1)).flatten().tolist()

        actuals_np = np.array(actuals)
        predictions_np = np.array(predictions)

        mae = float(np.mean(np.abs(actuals_np - predictions_np)))
        rmse = float(np.sqrt(np.mean((actuals_np - predictions_np) ** 2)))
        ss_res = np.sum((actuals_np - predictions_np) ** 2)
        ss_tot = np.sum((actuals_np - np.mean(actuals_np)) ** 2)
        r2 = float(1 - (ss_res / (ss_tot + 1e-10)))
        mape = float(np.mean(np.abs((actuals_np - predictions_np) / (actuals_np + 1e-10))) * 100)

        save_model_performance(symbol, 'LSTM', mae, rmse, r2, mape)

        # Align test dates
        test_dates = df['Date'].iloc[lookback + split_idx:].dt.strftime('%Y-%m-%d').tolist()

        return {
            'loss_history': losses,
            'val_loss_history': val_losses,
            'mae': mae,
            'rmse': rmse,
            'r2': r2,
            'mape': mape,
            'test_actuals': actuals,
            'test_predictions': predictions,
            'test_dates': test_dates
        }

    # Standard TensorFlow LSTM Pipeline
    Sequential, load_model, LSTM, Dense, Dropout, Callback = _get_keras()
    from sklearn.preprocessing import MinMaxScaler

    class _EpochTracker(Callback):
        def __init__(self):
            super().__init__()
            self.losses = []
            self.val_losses = []
        def on_epoch_end(self, epoch, logs=None):
            logs = logs or {}
            self.losses.append(float(logs.get('loss', 0.0)))
            if 'val_loss' in logs:
                self.val_losses.append(float(logs.get('val_loss', 0.0)))

    df = get_stock_data(symbol)

    if len(df) > 1000:
        df = df.iloc[-1000:].reset_index(drop=True)

    close_prices = df['Close'].values.reshape(-1, 1)
    scaler = MinMaxScaler(feature_range=(0, 1))
    scaled_data = scaler.fit_transform(close_prices)

    os.makedirs(Config.MODELS_FOLDER, exist_ok=True)
    scaler_path = os.path.join(Config.MODELS_FOLDER, f"{symbol.lower()}_lstm_scaler.joblib")
    joblib.dump(scaler, scaler_path)

    X, y = [], []
    for i in range(lookback, len(scaled_data)):
        X.append(scaled_data[i - lookback:i, 0])
        y.append(scaled_data[i, 0])

    X, y = np.array(X), np.array(y)

    if len(X) < 50:
        raise ValueError(f"Insufficient data for {symbol} after applying {lookback}-day window.")

    X = np.reshape(X, (X.shape[0], X.shape[1], 1))
    split_idx = int(len(X) * 0.8)
    X_train, X_test = X[:split_idx], X[split_idx:]
    y_train, y_test = y[:split_idx], y[split_idx:]

    model = Sequential([
        LSTM(units=30, return_sequences=True, input_shape=(lookback, 1)),
        Dropout(0.1),
        LSTM(units=30, return_sequences=False),
        Dropout(0.1),
        Dense(units=15),
        Dense(units=1)
    ])
    model.compile(optimizer='adam', loss='mean_squared_error')

    epoch_tracker = _EpochTracker()
    model.fit(
        X_train, y_train,
        validation_data=(X_test, y_test),
        epochs=epochs,
        batch_size=batch_size,
        callbacks=[epoch_tracker],
        verbose=0
    )

    model_path = os.path.join(Config.MODELS_FOLDER, f"{symbol.lower()}_lstm_model.h5")
    model.save(model_path)

    scaled_predictions = model.predict(X_test, verbose=0)
    actuals = scaler.inverse_transform(y_test.reshape(-1, 1)).flatten().tolist()
    predictions = scaler.inverse_transform(scaled_predictions).flatten().tolist()

    actuals_np = np.array(actuals)
    predictions_np = np.array(predictions)

    mae = float(np.mean(np.abs(actuals_np - predictions_np)))
    rmse = float(np.sqrt(np.mean((actuals_np - predictions_np) ** 2)))
    ss_res = np.sum((actuals_np - predictions_np) ** 2)
    ss_tot = np.sum((actuals_np - np.mean(actuals_np)) ** 2)
    r2 = float(1 - (ss_res / (ss_tot + 1e-10)))
    mape = float(np.mean(np.abs((actuals_np - predictions_np) / (actuals_np + 1e-10))) * 100)

    save_model_performance(symbol, 'LSTM', mae, rmse, r2, mape)
    test_dates = df['Date'].iloc[lookback + split_idx:].dt.strftime('%Y-%m-%d').tolist()

    return {
        'loss_history': epoch_tracker.losses,
        'val_loss_history': epoch_tracker.val_losses,
        'mae': mae,
        'rmse': rmse,
        'r2': r2,
        'mape': mape,
        'test_actuals': actuals,
        'test_predictions': predictions,
        'test_dates': test_dates
    }


def forecast_future_lstm(symbol, lookback=60, forecast_steps=30):
    """
    Loads saved LSTM (or MLP fallback) and Scaler to predict future close prices.
    Uses recursive forecast where each predicted value feeds the next input window.
    """
    if not HAS_TENSORFLOW:
        symbol = symbol.upper()
        model_path = os.path.join(Config.MODELS_FOLDER, f"{symbol.lower()}_lstm_model.joblib")
        scaler_path = os.path.join(Config.MODELS_FOLDER, f"{symbol.lower()}_lstm_scaler.joblib")

        if not os.path.exists(model_path) or not os.path.exists(scaler_path):
            train_lstm_model(symbol, lookback=lookback, epochs=3)

        model = joblib.load(model_path)
        scaler = joblib.load(scaler_path)

        df = get_stock_data(symbol)
        close_prices = df['Close'].values.reshape(-1, 1)

        last_window = close_prices[-lookback:]
        scaled_window = scaler.transform(last_window).flatten().tolist()

        forecast = []
        for _ in range(forecast_steps):
            x_in = np.array([scaled_window[-lookback:]])
            scaled_pred = float(model.predict(x_in)[0])
            scaled_window.append(scaled_pred)
            actual_pred = float(scaler.inverse_transform([[scaled_pred]])[0, 0])
            forecast.append(actual_pred)

        return forecast

    # Standard TensorFlow LSTM Forecasting
    Sequential, load_model, LSTM, Dense, Dropout, Callback = _get_keras()

    symbol = symbol.upper()
    model_path = os.path.join(Config.MODELS_FOLDER, f"{symbol.lower()}_lstm_model.h5")
    scaler_path = os.path.join(Config.MODELS_FOLDER, f"{symbol.lower()}_lstm_scaler.joblib")

    if not os.path.exists(model_path) or not os.path.exists(scaler_path):
        train_lstm_model(symbol, lookback=lookback, epochs=3)

    model = load_model(model_path)
    scaler = joblib.load(scaler_path)

    df = get_stock_data(symbol)
    close_prices = df['Close'].values.reshape(-1, 1)

    last_window = close_prices[-lookback:]
    scaled_window = scaler.transform(last_window).flatten().tolist()

    forecast = []
    for _ in range(forecast_steps):
        x_in = np.array([scaled_window[-lookback:]]).reshape(1, lookback, 1)
        scaled_pred = float(model.predict(x_in, verbose=0)[0, 0])
        scaled_window.append(scaled_pred)
        actual_pred = float(scaler.inverse_transform([[scaled_pred]])[0, 0])
        forecast.append(actual_pred)

    return forecast
