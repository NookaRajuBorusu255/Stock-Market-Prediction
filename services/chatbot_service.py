import re
import requests
import pandas as pd
import numpy as np
from config import Config
from services.data_service import get_stock_data, list_available_symbols
from database.models import ModelPerformance
from database.database_helper import get_all_model_performances

def call_gemini_api(prompt, api_key):
    """
    Calls the Google Gemini API via REST POST request.
    """
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }]
    }
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data['candidates'][0]['content']['parts'][0]['text']
        else:
            return f"Error from Gemini API (Status Code {response.status_code}): {response.text}"
    except Exception as e:
        return f"Failed to contact Gemini API: {str(e)}"

def call_openai_api(prompt, api_key):
    """
    Calls the OpenAI API via REST POST request.
    """
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    payload = {
        "model": "gpt-3.5-turbo",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7
    }
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data['choices'][0]['message']['content']
        else:
            return f"Error from OpenAI API (Status Code {response.status_code}): {response.text}"
    except Exception as e:
        return f"Failed to contact OpenAI API: {str(e)}"

def get_chatbot_response(user_message, active_symbol=None, active_model=None):
    """
    Main controller for the AI chatbot.
    Parses prompt for keywords to extract local dataset statistics first,
    then forwards enriched context to external LLMs if API key exists.
    Otherwise, returns local analytical feedback.
    """
    # 1. Look for stock symbol patterns in the message (e.g. AAPL, MSFT, etc.)
    available = list_available_symbols()
    detected_symbol = None
    
    # Common English words that shouldn't be matched as stock symbols
    STOP_WORDS = {
        'IS', 'IT', 'AM', 'OR', 'SO', 'ON', 'ALL', 'CAN', 'GO', 'HE', 'BE', 'AT', 'BY', 
        'AN', 'ME', 'MY', 'UP', 'DO', 'IF', 'IN', 'TO', 'NO', 'US', 'FOR', 'OUT', 'GET',
        'SHOW', 'THE', 'WHAT', 'HOW', 'WHY', 'WHO', 'WHEN', 'AND', 'BUT', 'NOT', 'YOU',
        'ARE', 'HAS', 'HAD', 'WAS', 'NEW', 'NOW', 'OUT'
    }
    
    # Check if any token matches an available symbol, ignoring stop words
    tokens = [w.strip("?,.!-()").upper() for w in user_message.split()]
    for token in tokens:
        if token in available and token not in STOP_WORDS:
            detected_symbol = token
            break
            
    # Fallback to general regex only if the word matches an available symbol and isn't a stop word
    if not detected_symbol:
        symbol_match = re.search(r'\b([A-Za-z]{1,5})\b', user_message)
        if symbol_match:
            potential = symbol_match.group(1).upper()
            if potential in available and potential not in STOP_WORDS:
                detected_symbol = potential
                
    target_symbol = detected_symbol if detected_symbol else active_symbol
    
    # 2. Get local financial summary if symbol is available
    stock_context = ""
    stock_stats = {}
    if target_symbol and target_symbol.upper() in available:
        try:
            df = get_stock_data(target_symbol)
            last_row = df.iloc[-1]
            prev_row = df.iloc[-2]
            
            price_change = last_row['Close'] - prev_row['Close']
            pct_change = (price_change / prev_row['Close']) * 100
            
            # Fetch model performance cached in DB
            performances = get_all_model_performances(target_symbol)
            perf_str = ", ".join([f"{p.model_name} (R2: {p.r2:.3f})" for p in performances])
            
            stock_stats = {
                'symbol': target_symbol,
                'price': last_row['Close'],
                'change': price_change,
                'pct_change': pct_change,
                'rsi': last_row['RSI'],
                'macd': last_row['MACD'],
                'macd_sig': last_row['MACD_Signal'],
                'sma20': last_row['SMA_20'],
                'sma50': last_row['SMA_50'],
                'volatility': last_row['Volatility'],
                'performances': perf_str,
                'high': last_row['High'] if 'High' in last_row else last_row['Close'],
                'low': last_row['Low'] if 'Low' in last_row else last_row['Close']
            }
            
            stock_context = (
                f"Active Stock: {target_symbol}\n"
                f"- Current Price: ${last_row['Close']:.2f} ({pct_change:+.2f}% change)\n"
                f"- Relative Strength Index (RSI): {last_row['RSI']:.2f}\n"
                f"- MACD: {last_row['MACD']:.4f} (Signal: {last_row['MACD_Signal']:.4f})\n"
                f"- Moving Averages: SMA20: ${last_row['SMA_20']:.2f}, SMA50: ${last_row['SMA_50']:.2f}\n"
                f"- Volatility: {last_row['Volatility']:.2f}\n"
                f"- Selected Model: {active_model if active_model else 'None'}\n"
                f"- Trained Models cache: {perf_str if perf_str else 'No models trained yet'}\n"
            )
        except Exception as e:
            stock_context = f"Could not extract stock details for {target_symbol}: {str(e)}\n"
            
    # 3. Check for API keys
    api_key_gemini = Config.GEMINI_API_KEY
    api_key_openai = Config.OPENAI_API_KEY
    
    if api_key_gemini:
        # Enrich prompt with stock statistics
        system_prompt = (
            "You are an expert AI Stock Market Assistant. Assist the user with stock prediction, "
            "technical analysis, and machine learning concepts. Explain equations, models (Linear Regression, "
            "Random Forest, XGBoost, LSTM), or statistics. Respond in clear, neat Markdown format.\n\n"
        )
        full_prompt = f"{system_prompt}Context about active stock data:\n{stock_context}\n\nUser Question:\n{user_message}"
        return call_gemini_api(full_prompt, api_key_gemini)
        
    elif api_key_openai:
        system_prompt = (
            "You are an expert AI Stock Market Assistant. Assist the user with stock prediction, "
            "technical analysis, and machine learning concepts. Explain equations, models (Linear Regression, "
            "Random Forest, XGBoost, LSTM), or statistics. Respond in clear, neat Markdown format.\n\n"
        )
        full_prompt = f"{system_prompt}Context about active stock data:\n{stock_context}\n\nUser Question:\n{user_message}"
        return call_openai_api(full_prompt, api_key_openai)
        
    # 4. Fallback to Local Rule-Based NLP Agent
    else:
        return generate_local_response(user_message, stock_stats, active_model)

def generate_local_response(msg, stats, active_model=None):
    """
    Fires rule-based local summaries and explanations for stock metrics and ML.
    """
    msg = msg.lower()
    
    # 0.25. Check for active/selected model queries
    if any(kw in msg for kw in ['selected model', 'which model', 'active model', 'current model']):
        if active_model:
            if stats and 'symbol' in stats:
                symbol = stats['symbol']
                from database.database_helper import get_model_performance
                perf = get_model_performance(symbol, active_model)
                if perf:
                    report = f"### Selected Model: **{active_model}**\n\n"
                    report += f"The currently selected forecasting model on the dashboard is **{active_model}**.\n\n"
                    report += f"**Database Training Metrics for {symbol}**:\n"
                    report += f"- **R² Coefficient of Determination**: `{perf.r2:.4f}`\n"
                    report += f"- **Mean Absolute Error (MAE)**: `${perf.mae:.4f}`\n"
                    report += f"- **Mean Absolute Percentage Error (MAPE)**: `{perf.mape:.2f}%`\n"
                    report += f"- **Root Mean Squared Error (RMSE)**: `${perf.rmse:.4f}`\n\n"
                    report += f"When you click **Generate Prediction** on the dashboard, this model configuration is loaded to run inference."
                    report += "\n\n*Note: Running in Local Fallback Mode. Configure `GEMINI_API_KEY` in your `.env` for generative AI context.*"
                    return report
                else:
                    report = f"The currently selected model is **{active_model}**.\n\n"
                    report += f"However, it has not been trained yet for {symbol}. Go to the ML Control Panel to train it!"
                    report += "\n\n*Note: Running in Local Fallback Mode. Configure `GEMINI_API_KEY` in your `.env` for generative AI context.*"
                    return report
            else:
                return f"The currently selected model is **{active_model}**."
        else:
            return "No predictive model has been selected yet. Select a model from the dashboard Predict tab."

    # 0. Check for prediction/forecasting requests
    if any(kw in msg for kw in ['predict', 'forecast', 'prediction', 'tomorrow']):
        if stats and 'symbol' in stats:
            symbol = stats['symbol']
            report = f"### AI Forecasting Report for **{symbol}**\n\n"
            report += f"Analyzing tomorrow's target close price using trained AI pipelines:\n\n"
            report += "| Model Name | Target Prediction | Expected Direction | Confidence |\n"
            report += "| :--- | :--- | :--- | :--- |\n"
            
            models_list = ['Linear Regression', 'Random Forest', 'XGBoost', 'LSTM']
            has_any = False
            for name in models_list:
                try:
                    if name == 'LSTM':
                        from services.dl_service import forecast_future_lstm
                        pred_val = forecast_future_lstm(symbol, forecast_steps=1)[0]
                        perf = ModelPerformance.query.filter_by(stock_symbol=symbol, model_name='LSTM').first()
                        if perf:
                            r2_conf = max(0, min(100, perf.r2 * 100))
                            mape_conf = max(0, min(100, 100 - perf.mape))
                            conf = (r2_conf * 0.4) + (mape_conf * 0.6)
                        else:
                            conf = 80.0
                    else:
                        from services.ml_service import load_ml_model_and_predict
                        pred_val, conf = load_ml_model_and_predict(symbol, name)
                        
                    direction = "▲ Bullish" if pred_val > stats['price'] else "▼ Bearish"
                    report += f"| **{name}** | `${pred_val:.2f}` | {direction} | `{conf:.1f}%` |\n"
                    has_any = True
                except Exception:
                    report += f"| **{name}** | *N/A (needs training)* | - | `0.0%` |\n"
                    
            report += f"\n*Current close: ${stats['price']:.2f}. Targets predict tomorrow's expected closing price.*"
            report += "\n\n*Note: Running in Local Fallback Mode. Configure `GEMINI_API_KEY` in your `.env` for generative AI context.*"
            return report
        else:
            return "Please select or mention an active stock symbol (e.g. 'AAPL') to generate next-day AI price predictions."

    # 0.5. Check for news and sentiment analysis requests
    if any(kw in msg for kw in ['news', 'sentiment', 'headline']):
        if stats and 'symbol' in stats:
            symbol = stats['symbol']
            from services.sentiment_service import get_sentiment_analysis
            res = get_sentiment_analysis(symbol)
            if res.get('success', False):
                report = f"### AI News & Sentiment Report for **{symbol}**\n\n"
                report += f"- **Overall Market Signal**: `{res['signal']}`\n"
                report += f"- **AI Sentiment Score**: `{res['sentiment_score']:.2f}` (ranging from -1.0 to +1.0)\n\n"
                report += "#### Generated Headline Highlights:\n"
                for hl in res['headlines']:
                    report += f"- **{hl['type']}**: {hl['text']} *(Sentiment score: {hl['score']:.2f})*\n"
                    
                report += "\n*Note: Running in Local Fallback Mode. Configure `GEMINI_API_KEY` in your `.env` for generative AI context.*"
                return report
            else:
                return f"Failed to retrieve news and sentiment for {symbol}: {res.get('error', 'Unknown error')}"
        else:
            return "Please select or mention a stock symbol (e.g. 'AAPL') to analyze news and sentiment signals."

    # 0.75. Check for dataset / dataframe description requests
    if any(kw in msg for kw in ['dataset', 'data set', 'dataframe', 'columns', 'shape', 'records', 'size', 'start date', 'end date']):
        if stats and 'symbol' in stats:
            symbol = stats['symbol']
            try:
                df = get_stock_data(symbol)
                start_date = df['Date'].min().strftime('%Y-%m-%d')
                end_date = df['Date'].max().strftime('%Y-%m-%d')
                cols_list = ", ".join([f"`{c}`" for c in df.columns])
                
                report = f"### Dataset Profile for **{symbol}**\n\n"
                report += f"Here is the database profile of the active dataset loaded for **{symbol}**:\n\n"
                report += f"- **Total Records**: `{len(df)}` trading days (rows)\n"
                report += f"- **Start Date**: `{start_date}`\n"
                report += f"- **End Date**: `{end_date}`\n"
                report += f"- **Columns List ({len(df.columns)})**: {cols_list}\n"
                report += f"- **Memory Footprint**: Approximately `{df.memory_usage(deep=True).sum() / 1024:.1f} KB`\n\n"
                
                report += "#### Key Technical Statistics (Descriptive Summary):\n"
                report += f"- **Lowest Close Price**: `${df['Close'].min():.2f}`\n"
                report += f"- **Highest Close Price**: `${df['Close'].max():.2f}`\n"
                report += f"- **Average Daily Trading Volume**: `{df['Volume'].mean():,.0f}` shares\n\n"
                
                report += "*Note: Running in Local Fallback Mode. Configure `GEMINI_API_KEY` in your `.env` for generative AI context.*"
                return report
            except Exception as e:
                return f"Failed to extract dataset profile for {symbol}: {str(e)}"
        else:
            return "Please select or mention a stock symbol (e.g. 'AAPL') to retrieve dataset details."

    # 1. If stock information was requested
    if stats and any(kw in msg for kw in ['price', 'rsi', 'macd', 'sma', 'volatility', 'status', 'analyze', 'summary']):
        summary = f"### Quantitative Report for **{stats['symbol']}**\n\n"
        summary += f"- **Last Close**: `${stats['price']:.2f}` ({stats['change']:+.2f} / {stats['pct_change']:+.2f}%)\n"
        
        # RSI explanation
        rsi = stats['rsi']
        if np.isnan(rsi):
            summary += "- **RSI (14)**: `N/A` (needs more data points)\n"
        else:
            status = "Neutral"
            if rsi < 30: status = "Oversold (Potential Buy/Rebound trigger)"
            elif rsi > 70: status = "Overbought (Potential Sell/Pullback trigger)"
            summary += f"- **RSI (14)**: `{rsi:.2f}` ({status})\n"
            
        # Moving Averages explanation
        sma20 = stats['sma20']
        sma50 = stats['sma50']
        if not np.isnan(sma20) and not np.isnan(sma50):
            relation = "above" if stats['price'] > sma50 else "below"
            summary += f"- **Moving Averages**: 20-day SMA `${sma20:.2f}`, 50-day SMA `${sma50:.2f}`. Currently trading **{relation}** the 50-day SMA.\n"
            
        # MACD explanation
        macd = stats['macd']
        macd_sig = stats['macd_sig']
        if not np.isnan(macd) and not np.isnan(macd_sig):
            cross = "Bullish Crossover" if macd > macd_sig else "Bearish Crossunder"
            summary += f"- **MACD**: `{macd:.4f}` (Signal Line: `{macd_sig:.4f}`). Crossover state indicates a **{cross}**.\n"
            
        # Volatility
        vol = stats['volatility']
        if not np.isnan(vol):
            summary += f"- **Annualized Volatility**: `{vol * 100:.1f}%`\n"
            
        # Pivot Points Calculations
        try:
            high = stats.get('high', stats['price'])
            low = stats.get('low', stats['price'])
            close = stats['price']
            
            p = (high + low + close) / 3.0
            r1 = (2.0 * p) - low
            s1 = (2.0 * p) - high
            r2 = p + (high - low)
            s2 = p - (high - low)
            
            summary += "\n#### Pivot Points & Trading Ranges\n"
            summary += "| Level | Price Target | Description |\n"
            summary += "| :--- | :--- | :--- |\n"
            summary += f"| **Resistance 2 (R2)** | `${r2:.2f}` | Major resistance zone |\n"
            summary += f"| **Resistance 1 (R1)** | `${r1:.2f}` | Moderate resistance zone |\n"
            summary += f"| **Pivot Point (P)** | `${p:.2f}` | Balance/Pivot price level |\n"
            summary += f"| **Support 1 (S1)** | `${s1:.2f}` | Moderate support zone |\n"
            summary += f"| **Support 2 (S2)** | `${s2:.2f}` | Major support zone |\n\n"
        except Exception:
            pass
            
        # Model cache
        summary += f"- **Model Database status**: `{stats['performances'] if stats['performances'] else 'No models trained for this symbol yet. Please train models in the ML Control Panel.'}`\n"
        summary += "\n*Note: Running in Local Fallback Mode. Configure `GEMINI_API_KEY` in your `.env` for generative AI context.*"
        return summary
        
    # 2. General machine learning explanations
    elif 'lstm' in msg:
        return (
            "### Long Short-Term Memory (LSTM) Networks\n\n"
            "An **LSTM** is a specialized recurrent neural network (RNN) capable of learning long-term dependencies. "
            "Standard RNNs suffer from the vanishing gradient problem when sequences are long. LSTMs solve this "
            "by introducing a **cell state** and three gates:\n\n"
            "1. **Forget Gate**: Decides what information from the cell state to discard.\n"
            "2. **Input Gate**: Decides which new values will update the cell state.\n"
            "3. **Output Gate**: Decides the next hidden state based on the current cell state.\n\n"
            "In stock market prediction, we feed a window of historical prices (e.g. 60 days) to predict the next day's close price."
        )
    elif 'xgboost' in msg:
        return (
            "### XGBoost (Extreme Gradient Boosting)\n\n"
            "**XGBoost** is an optimized distributed gradient boosting library designed to be highly efficient, flexible, and portable. "
            "It implements machine learning algorithms under the Gradient Boosting framework. "
            "Instead of training independent trees in parallel (like Random Forest), XGBoost builds decision trees **sequentially**, "
            "where each new tree corrects the errors (residuals) of the prior trees.\n\n"
            "In our stock prediction platform, XGBoost is fed tabular lag features (prior prices) and technical indicators "
            "to perform fast regression and rank performance metrics."
        )
    elif 'random forest' in msg or re.search(r'\brf\b', msg):
        return (
            "### Random Forest Regressor\n\n"
            "**Random Forest** is an ensemble learning method that fits multiple decision trees on various sub-samples "
            "of the dataset and uses averaging to improve prediction accuracy and control over-fitting.\n\n"
            "Unlike simple Decision Trees, Random Forest introduces random selection of features at split points to "
            "ensure trees are decorrelated. The final price prediction is the average of predictions from all individual trees."
        )
    elif 'linear regression' in msg:
        return (
            "### Linear Regression\n\n"
            "**Linear Regression** is a simple, classical statistical model that establishes a linear relationship between "
            "independent input features ($X$) and a continuous target variable ($y$). The model fits a straight line/hyperplane "
            "that minimizes the sum of squared differences (residuals) between predicted and actual values.\n\n"
            "Equation: $y = \beta_0 + \beta_1 x_1 + \beta_2 x_2 + ... + \beta_n x_n$\n\n"
            "We use Linear Regression as our predictive baseline."
        )
    elif 'indicator' in msg or 'rsi' in msg or 'macd' in msg:
        return (
            "### Technical Indicators Definitions\n\n"
            "- **RSI (Relative Strength Index)**: A momentum oscillator that measures the speed and change of price movements "
            "on a scale of 0 to 100. Traditionally, values $>70$ indicate overbought conditions, while values $<30$ indicate oversold.\n"
            "- **MACD (Moving Average Convergence Divergence)**: A trend-following momentum indicator showing the relationship between "
            "two moving averages of a stock's price. It is calculated as 12-period EMA minus 26-period EMA. A 9-period EMA of the MACD "
            "acts as a signal line for crossover analysis.\n"
            "- **SMA (Simple Moving Average)**: The average close price over a specific window (e.g. 20, 50, or 200 days). "
            "Helps filter out daily noise to highlight primary trends."
        )
    elif 'overfit' in msg or 'validation' in msg or 'loss' in msg:
        return (
            "### Machine Learning Overfitting & Loss Metrics\n\n"
            "**Overfitting** occurs when a model learns noise and details in the training dataset to the extent "
            "that it negatively impacts the performance of the model on new data. This is typically observed when "
            "**Training Loss** continues to decrease while **Validation Loss** starts to increase.\n\n"
            "#### How to Diagnose Overfitting:\n"
            "- **Training Loss vs Validation Loss**: In our ML control panel, you can monitor the loss history chart. "
            "If the validation loss curve separates upwards from the training loss, the model is overfitting.\n"
            "- **R² Score on Test Set**: A very high training accuracy but negative or low R² score on the test set is a classic sign.\n\n"
            "#### Solutions:\n"
            "1. **Early Stopping**: Stop training when validation loss stops improving (as our LSTM/MLP training loop checks).\n"
            "2. **Reduce Complexity**: Reduce the number of hidden layers or neurons.\n"
            "3. **Regularization**: Add Dropout layers or L1/L2 penalties to constrain weights."
        )
    elif 'epoch' in msg or 'lookback' in msg or 'hyperparameter' in msg:
        return (
            "### Hyperparameters: Lookback Windows and Epochs\n\n"
            "Machine learning models require fine-tuning hyperparameters to predict stock trends successfully:\n\n"
            "- **Lookback Window (Sequence Length)**: The number of prior trading days fed as input to the sequence model. "
            "A lookback of `60` means the model uses the last 60 days of prices to predict day 61. Too short (e.g. 5) might ignore historical "
            "trends, while too long (e.g. 200) might introduce stale history and delay calculations.\n"
            "- **Epochs**: The number of complete passes the training algorithm makes through the training dataset. "
            "For deep learning, too few epochs (e.g. 1) result in **underfitting** (insufficient learning), while too many (e.g. 100) result in **overfitting**."
        )
    elif 'feature' in msg or 'lag' in msg:
        return (
            "### Feature Engineering: Lag Features & Technical Columns\n\n"
            "Stock close prices are highly auto-correlated. To train regression algorithms, we engineer features to provide predictive context:\n\n"
            "1. **Lag Features**: Shifted close prices (e.g. `Close_lag_1` represents yesterday's close, `Close_lag_2` represents the day before). "
            "This converts sequential time-series data into standard tabular features.\n"
            "2. **Momentum Features**: Technical indicators like **RSI** and **MACD** represent velocity and convergence trends.\n"
            "3. **Volatility Features**: Annualized standard deviation of returns that captures market risk over a rolling window."
        )
    elif any(kw in msg for kw in ['hello', 'hi', 'hey', 'greetings', 'morning', 'afternoon', 'evening']):
        return (
            "### Hello there!\n\n"
            "Welcome to the **Stock Market Prediction** platform. I am your Intelligent Stock Assistant.\n\n"
            "I'm ready to help you analyze stock indicators, train machine learning models, and interpret forecasting outputs. "
            "How can I assist your market analysis today?"
        )
    elif 'how are you' in msg:
        return (
            "### How Are You?\n\n"
            "I am doing excellent, thank you! I've been busy indexing stock symbols and calculating technical indicator averages. "
            "I'm fully synchronized and ready to process price charts or answer machine learning questions!"
        )
    elif 'who are you' in msg or 'what do you do' in msg or 'who made you' in msg or 'creator' in msg:
        return (
            "### About Me\n\n"
            "I am the **Intelligent Stock Assistant**, an AI agent built to support traders and analysts on the "
            "**Stock Market Prediction** platform.\n\n"
            "#### My Capabilities:\n"
            "- **Technical Level Analysis**: I calculate moving averages (SMA20/50), momentum oscillators (RSI), MACD crossovers, and standard Pivot Point support/resistance targets.\n"
            "- **Machine Learning Guide**: I explain core prediction models like LSTM neural networks, XGBoost decision trees, Random Forest, and Linear Regression.\n"
            "- **News & Sentiment Summarizer**: I compile dynamic financial headlines and evaluate general market signals."
        )
    elif 'what is a stock' in msg or 'what is stock' in msg:
        return (
            "### What is a Stock?\n\n"
            "A **stock** (also known as equity) is a security that represents fractional ownership of a corporation. "
            "When you buy a share of stock, you are buying a tiny piece of the company. Companies issue stock to raise "
            "capital to grow their business.\n\n"
            "Stock prices fluctuate based on supply and demand, company performance, economic indicators, and general market sentiment."
        )
    elif 'stock market' in msg:
        return (
            "### What is the Stock Market?\n\n"
            "The **stock market** refers to the collection of exchanges and other venues where buying, selling, and issuance of "
            "shares of publicly held companies take place.\n\n"
            "#### How it works:\n"
            "- **Exchanges**: Platforms like the NYSE (New York Stock Exchange) or NASDAQ match buyers with sellers.\n"
            "- **Trading**: Investors trade shares of stock, driving prices up or down based on earnings reports, news, and technical trends.\n"
            "- **Index**: Aggregations like the S&P 500 or Dow Jones track the collective performance of major company stocks."
        )
    else:
        return (
            "Hello! I am your AI-Powered Stock Assistant. I can:\n\n"
            "1. **Analyze Stocks**: Type a stock name (e.g. 'AAPL' or 'AADR') to get moving averages, MACD, and RSI summaries.\n"
            "2. **Explain Models**: Ask me about 'LSTM', 'XGBoost', 'Random Forest', or 'Linear Regression'.\n"
            "3. **Discuss Concepts**: Ask me about technical indicators like 'RSI' or 'MACD'.\n\n"
            "*Note: Set `GEMINI_API_KEY` in a `.env` file in the root folder to unlock full generative AI insights.*"
        )
