from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime, timedelta

from services.ml_service import (
    train_and_evaluate_models, 
    load_ml_model_and_predict
)
from services.dl_service import (
    train_lstm_model, 
    forecast_future_lstm
)
from database.database_helper import (
    get_all_model_performances, 
    save_prediction,
    get_model_performance
)
from services.data_service import list_available_symbols

ml_bp = Blueprint('ml', __name__)

@ml_bp.route('/models')
@login_required
def models_panel():
    """
    Renders the ML Control Panel where users can train models
    and compare cached metrics.
    """
    symbols = list_available_symbols()
    sorted_symbols = sorted(symbols.keys())
    return render_template('ml_models.html', symbols=sorted_symbols)

@ml_bp.route('/api/train/ml/<symbol>', methods=['POST'])
@login_required
def train_classical_models(symbol):
    """
    Triggers classical ML models training (Linear Regression, Random Forest, XGBoost)
    on the specified stock. Caches scores and returns summary.
    """
    try:
        results = train_and_evaluate_models(symbol)

        # Include backtest arrays so the frontend can render an Actual vs Predicted chart
        response_data = {}
        for name, metrics in results.items():
            response_data[name] = {
                'mae':              metrics['mae'],
                'rmse':             metrics['rmse'],
                'r2':               metrics['r2'],
                'mape':             metrics['mape'],
                'test_dates':       metrics.get('test_dates', []),
                'test_actuals':     metrics.get('test_actuals', []),
                'test_predictions': metrics.get('test_predictions', []),
            }
        return jsonify({'success': True, 'results': response_data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@ml_bp.route('/api/train/lstm/<symbol>', methods=['POST'])
@login_required
def train_lstm(symbol):
    """
    Triggers LSTM Deep Learning network training.
    Supports input parameter for customized epochs.
    """
    try:
        body = request.get_json(silent=True) or {}
        epochs = int(body.get('epochs', 5))
        lookback = int(body.get('lookback', 60))
        batch_size = int(body.get('batch_size', 32))
        
        results = train_lstm_model(symbol, lookback=lookback, epochs=epochs, batch_size=batch_size)
        
        return jsonify({
            'success': True,
            'mae': results['mae'],
            'rmse': results['rmse'],
            'r2': results['r2'],
            'mape': results['mape'],
            'loss_history': results['loss_history'],
            'val_loss_history': results['val_loss_history']
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@ml_bp.route('/api/predict/<symbol>', methods=['POST'])
@login_required
def predict_price(symbol):
    """
    Predicts next-day close price using selected model
    and saves prediction log inside User profile.
    """
    try:
        body = request.get_json(silent=True) or {}
        model_name = body.get('model', 'XGBoost')
        
        if model_name == 'LSTM':
            # Forecast next day Close
            forecasts = forecast_future_lstm(symbol, forecast_steps=1)
            pred_price = forecasts[0]
            # Get confidence based on LSTM evaluation cache
            perf = get_model_performance(symbol, 'LSTM')
            if perf:
                r2_conf = max(0, min(100, perf.r2 * 100))
                mape_conf = max(0, min(100, 100 - perf.mape))
                confidence = (r2_conf * 0.4) + (mape_conf * 0.6)
            else:
                confidence = 80.0
        else:
            # Predict classical ML
            pred_price, confidence = load_ml_model_and_predict(symbol, model_name)
            
        # Target Date is tomorrow
        prediction_date = datetime.now() + timedelta(days=1)
        
        # Save log in database
        save_prediction(
            user_id=current_user.id,
            stock_symbol=symbol,
            model_name=model_name,
            prediction_date=prediction_date,
            predicted_price=pred_price,
            confidence_score=confidence
        )
        
        return jsonify({
            'success': True,
            'predicted_price': pred_price,
            'confidence': confidence,
            'prediction_date': prediction_date.strftime('%Y-%m-%d')
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@ml_bp.route('/api/forecast/lstm/<symbol>', methods=['GET'])
@login_required
def get_lstm_forecast(symbol):
    """
    Returns next 30-day forecasted prices for visual overlay.
    """
    try:
        steps = int(request.args.get('steps', 30))
        forecasts = forecast_future_lstm(symbol, forecast_steps=steps)
        
        # Generate target dates
        start_date = datetime.now()
        dates = []
        for i in range(1, steps + 1):
            dates.append((start_date + timedelta(days=i)).strftime('%Y-%m-%d'))
            
        return jsonify({
            'success': True,
            'dates': dates,
            'forecast': forecasts
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@ml_bp.route('/api/performance/<symbol>', methods=['GET'])
@login_required
def get_performance_comparison(symbol):
    """
    Returns performance cached table for UI dashboard display.
    """
    try:
        performances = get_all_model_performances(symbol)
        res = []
        for p in performances:
            res.append({
                'model_name': p.model_name,
                'mae': p.mae,
                'rmse': p.rmse,
                'r2': p.r2,
                'mape': p.mape,
                'trained_at': p.trained_at.strftime('%Y-%m-%d %H:%M:%S')
            })
        return jsonify({'success': True, 'performance': res})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@ml_bp.route('/api/feature_importance/<symbol>', methods=['GET'])
@login_required
def get_feature_importance(symbol):
    """
    Returns sorted feature importances for Random Forest or XGBoost models.
    """
    import os
    import joblib
    from config import Config
    from services.ml_service import prepare_ml_data
    from services.data_service import get_stock_data
    
    symbol = symbol.upper()
    model_name = request.args.get('model', 'Random Forest')
    
    # Map model name to filename suffix
    suffix = "random_forest" if model_name == 'Random Forest' else "xgboost"
    model_filename = f"{symbol.lower()}_{suffix}.joblib"
    model_path = os.path.join(Config.MODELS_FOLDER, model_filename)
    
    # If the model does not exist, let's train it first
    if not os.path.exists(model_path):
        try:
            from services.ml_service import train_and_evaluate_models
            train_and_evaluate_models(symbol)
        except Exception as e:
            return jsonify({'success': False, 'error': f"Failed to train models: {str(e)}"}), 400
            
    try:
        model = joblib.load(model_path)
        
        # Get feature names from prepare_ml_data
        df = get_stock_data(symbol)
        X, _, _ = prepare_ml_data(df)
        feature_names = list(X.columns)
        
        # Retrieve feature importances
        if hasattr(model, 'feature_importances_'):
            importances = model.feature_importances_
        else:
            return jsonify({'success': False, 'error': f"Model '{model_name}' does not support feature importance metrics."}), 400
            
        # Map feature names to clean readable labels
        clean_names = {
            'Close_lag_1': 'Close Price (t-1)',
            'Close_lag_2': 'Close Price (t-2)',
            'Close_lag_3': 'Close Price (t-3)',
            'Close_lag_4': 'Close Price (t-4)',
            'Close_lag_5': 'Close Price (t-5)',
            'Open_lag_1': 'Open Price (t-1)',
            'Open_lag_2': 'Open Price (t-2)',
            'Open_lag_3': 'Open Price (t-3)',
            'Open_lag_4': 'Open Price (t-4)',
            'Open_lag_5': 'Open Price (t-5)',
            'High_lag_1': 'High Price (t-1)',
            'High_lag_2': 'High Price (t-2)',
            'High_lag_3': 'High Price (t-3)',
            'High_lag_4': 'High Price (t-4)',
            'High_lag_5': 'High Price (t-5)',
            'Low_lag_1': 'Low Price (t-1)',
            'Low_lag_2': 'Low Price (t-2)',
            'Low_lag_3': 'Low Price (t-3)',
            'Low_lag_4': 'Low Price (t-4)',
            'Low_lag_5': 'Low Price (t-5)',
            'Volume_lag_1': 'Volume Traded (t-1)',
            'Volume_lag_2': 'Volume Traded (t-2)',
            'Volume_lag_3': 'Volume Traded (t-3)',
            'Volume_lag_4': 'Volume Traded (t-4)',
            'Volume_lag_5': 'Volume Traded (t-5)',
            'SMA_20_lag_1': '20-day SMA (t-1)',
            'SMA_50_lag_1': '50-day SMA (t-1)',
            'SMA_200_lag_1': '200-day SMA (t-1)',
            'MACD_lag_1': 'MACD (t-1)',
            'MACD_Signal_lag_1': 'MACD Signal (t-1)',
            'RSI_lag_1': 'RSI Indicator (t-1)',
            'Volatility_lag_1': 'Annual Volatility (t-1)'
        }
        
        # Build features list
        features_list = []
        for name, val in zip(feature_names, importances):
            features_list.append({
                'name': clean_names.get(name, name),
                'importance': float(val)
            })
            
        # Sort by importance descending and take top 10
        features_list = sorted(features_list, key=lambda x: x['importance'], reverse=True)[:10]
        
        return jsonify({
            'success': True,
            'model': model_name,
            'features': features_list
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400
