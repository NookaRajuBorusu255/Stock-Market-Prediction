import os
import pandas as pd
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from services.data_service import (
    list_available_symbols,
    get_stock_data,
    refresh_symbol_cache,
    parse_and_standardize_csv,
    invalidate_stock_cache,
)
from database.database_helper import get_user_predictions
from config import Config

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
@login_required
def index():
    """
    Renders the main analysis dashboard page.
    Passes list of available symbols to stock selector.
    """
    symbols = list_available_symbols()
    sorted_symbols = sorted(symbols.keys())
    return render_template('dashboard.html', symbols=sorted_symbols)

@dashboard_bp.route('/symbols')
@login_required
def get_symbols():
    """
    Returns list of indexed symbols with types.
    """
    symbols = list_available_symbols()
    return jsonify(symbols)

@dashboard_bp.route('/api/stock/<symbol>')
@login_required
def get_stock_json(symbol):
    """
    Returns full historical data and indicators for a given symbol in JSON format.
    """
    try:
        df = get_stock_data(symbol)
        
        # Limit data size to speed up delivery if it's very large (e.g. last 1000 records)
        # But keep it adjustable. Last 1000 trading days is ~4 years, ideal for Plotly.
        if len(df) > 1000:
            df = df.iloc[-1000:]
            
        data_dict = {
            'dates':      df['Date'].dt.strftime('%Y-%m-%d').tolist(),
            'open':       df['Open'].tolist(),
            'high':       df['High'].tolist(),
            'low':        df['Low'].tolist(),
            'close':      df['Close'].tolist(),
            'volume':     df['Volume'].tolist(),
            'sma20':      df['SMA_20'].fillna(0).tolist(),
            'sma50':      df['SMA_50'].fillna(0).tolist(),
            'sma200':     df['SMA_200'].fillna(0).tolist(),
            'macd':       df['MACD'].fillna(0).tolist(),
            'macd_signal':df['MACD_Signal'].fillna(0).tolist(),
            'macd_hist':  df['MACD_Hist'].fillna(0).tolist(),
            'rsi':        df['RSI'].fillna(50).tolist(),
            'volatility': df['Volatility'].fillna(0).tolist(),
            # Bollinger Bands
            'bb_upper':   df['BB_Upper'].fillna(0).tolist(),
            'bb_mid':     df['BB_Mid'].fillna(0).tolist(),
            'bb_lower':   df['BB_Lower'].fillna(0).tolist(),
        }
        return jsonify(data_dict)
    except Exception as e:
        return jsonify({'error': str(e)}), 404


@dashboard_bp.route('/api/stock/<symbol>/summary')
@login_required
def get_stock_summary(symbol):
    """
    Returns a compact latest-row summary for fast metric card refresh.
    Includes price, change, RSI, MACD state, SMA positions, volatility, BB width.
    """
    try:
        df = get_stock_data(symbol)
        last  = df.iloc[-1]
        prev  = df.iloc[-2]

        price       = float(last['Close'])
        change      = float(last['Close'] - prev['Close'])
        pct_change  = float(change / prev['Close'] * 100)
        rsi         = float(last['RSI']) if not pd.isna(last['RSI']) else None
        macd        = float(last['MACD']) if not pd.isna(last['MACD']) else None
        macd_sig    = float(last['MACD_Signal']) if not pd.isna(last['MACD_Signal']) else None
        sma20       = float(last['SMA_20']) if not pd.isna(last['SMA_20']) else None
        sma50       = float(last['SMA_50']) if not pd.isna(last['SMA_50']) else None
        volatility  = float(last['Volatility']) if not pd.isna(last['Volatility']) else None
        bb_upper    = float(last['BB_Upper']) if not pd.isna(last['BB_Upper']) else None
        bb_lower    = float(last['BB_Lower']) if not pd.isna(last['BB_Lower']) else None
        bb_width    = float(last['BB_Width']) if not pd.isna(last['BB_Width']) else None

        return jsonify({
            'symbol':     symbol.upper(),
            'price':      price,
            'change':     change,
            'pct_change': pct_change,
            'rsi':        rsi,
            'macd':       macd,
            'macd_sig':   macd_sig,
            'sma20':      sma20,
            'sma50':      sma50,
            'volatility': volatility,
            'bb_upper':   bb_upper,
            'bb_lower':   bb_lower,
            'bb_width':   bb_width,
            'last_date':  last['Date'].strftime('%Y-%m-%d'),
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 404

@dashboard_bp.route('/upload', methods=['POST'])
@login_required
def upload_file():
    """
    Allows user to upload a custom CSV dataset.
    The file name becomes the stock symbol.
    """
    if 'file' not in request.files:
        flash('No file part in upload request.', 'danger')
        return redirect(url_for('dashboard.index'))
        
    file = request.files['file']
    if file.filename == '':
        flash('No selected file.', 'danger')
        return redirect(url_for('dashboard.index'))
        
    if file and (file.filename.endswith('.csv') or file.filename.endswith('.txt')):
        filename = secure_filename(file.filename)
        os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
        filepath = os.path.join(Config.UPLOAD_FOLDER, filename)
        
        try:
            file.save(filepath)
            # Parse and standardize file robustly
            df = parse_and_standardize_csv(filepath)
            
            required = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']
            missing = [r for r in required if r not in df.columns]
            
            if missing:
                os.remove(filepath)
                flash(f"Upload failed: File structure missing columns {missing}.", "danger")
                return redirect(url_for('dashboard.index'))
                
            # Overwrite the uploaded file with standardized comma-separated CSV format
            df.to_csv(filepath, index=False)

            # Refresh symbol index + invalidate parsed data cache
            refresh_symbol_cache()
            symbol_key = filename.split('.')[0].upper()
            invalidate_stock_cache(symbol_key)
            symbol = filename.split('.')[0].upper()
            flash(f"File uploaded successfully! Symbol '{symbol}' is now active.", "success")
        except Exception as e:
            if os.path.exists(filepath):
                os.remove(filepath)
            flash(f"Error parsing uploaded file: {str(e)}", "danger")
            
    else:
        flash("Invalid file format. Upload only .csv or .txt files.", "danger")
        
    return redirect(url_for('dashboard.index'))

@dashboard_bp.route('/profile')
@login_required
def profile():
    """Renders user profile with prediction history."""
    predictions = get_user_predictions(current_user.id)
    return render_template('profile.html', predictions=predictions)


@dashboard_bp.route('/profile/export/csv')
@login_required
def export_predictions_csv():
    """Streams user prediction history as a downloadable CSV."""
    import io
    import csv
    from flask import Response

    predictions = get_user_predictions(current_user.id)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Symbol', 'Model', 'Target Date', 'Predicted Price',
                     'Actual Price', 'Confidence %', 'Created At'])
    for p in predictions:
        writer.writerow([
            p.stock_symbol,
            p.model_name,
            p.prediction_date.strftime('%Y-%m-%d'),
            f'{p.predicted_price:.4f}',
            f'{p.actual_price:.4f}' if p.actual_price is not None else '',
            f'{p.confidence_score:.2f}',
            p.created_at.strftime('%Y-%m-%d %H:%M:%S'),
        ])
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition':
                 f'attachment; filename=predictions_{current_user.username}.csv'}
    )


@dashboard_bp.route('/profile/prediction/<int:pred_id>/delete', methods=['POST'])
@login_required
def delete_prediction(pred_id):
    """Deletes a single prediction row owned by the current user."""
    from database.models import PredictionHistory
    from database import db
    pred = db.session.get(PredictionHistory, pred_id)
    if pred is None or pred.user_id != current_user.id:
        return jsonify({'success': False, 'error': 'Not found'}), 404
    db.session.delete(pred)
    db.session.commit()
    return jsonify({'success': True})

@dashboard_bp.route('/api/sentiment/<symbol>')
@login_required
def get_sentiment(symbol):
    """
    Returns AI generated stock news and sentiment signals for the active stock.
    """
    from services.sentiment_service import get_sentiment_analysis
    res = get_sentiment_analysis(symbol)
    if not res.get('success', False):
        return jsonify({'error': res.get('error', 'Failed to fetch sentiment')}), 404
    return jsonify(res)

@dashboard_bp.route('/api/stock/<symbol>/heatmap')
@login_required
def get_stock_heatmap(symbol):
    """
    Generates and returns a base64 encoded Seaborn correlation heatmap.
    Accepts an optional 'theme' query parameter.
    """
    theme = request.args.get('theme', 'dark')
    try:
        df = get_stock_data(symbol)
        from services.visualization_service import generate_correlation_heatmap
        img_data = generate_correlation_heatmap(df, theme=theme)
        return jsonify({'success': True, 'image': img_data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 404


