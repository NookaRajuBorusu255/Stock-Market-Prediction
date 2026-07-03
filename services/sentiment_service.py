import random
import numpy as np
from services.data_service import get_stock_data, list_available_symbols

def get_sentiment_analysis(symbol):
    """
    Generates daily synthetic news headlines for the selected stock
    based on its technical signals, calculates an AI sentiment score (-1.0 to +1.0)
    and lists headlines.
    """
    symbol = symbol.upper()
    available = list_available_symbols()
    
    if symbol not in available:
        return {
            'success': False,
            'error': f"Symbol {symbol} not found."
        }
        
    try:
        df = get_stock_data(symbol)
        last_row = df.iloc[-1]
        prev_row = df.iloc[-2]
        
        price_change = last_row['Close'] - prev_row['Close']
        pct_change = (price_change / prev_row['Close']) * 100
        rsi = last_row['RSI']
        
        # Calculate a base sentiment score derived from price action and technicals
        # 1. Price momentum component (-0.5 to +0.5)
        price_score = np.clip(pct_change / 3.0, -0.5, 0.5) # scaled so 3% change maximizes score
        
        # 2. RSI component (-0.3 to +0.3)
        rsi_score = 0.0
        if not np.isnan(rsi):
            if rsi > 70:
                rsi_score = -0.3 # overbought, negative signal for reversion
            elif rsi < 30:
                rsi_score = 0.3 # oversold, positive signal for reversion
                
        # 3. MACD component (-0.2 to +0.2)
        macd_score = 0.0
        if not np.isnan(last_row['MACD']) and not np.isnan(last_row['MACD_Signal']):
            macd_score = 0.2 if last_row['MACD'] > last_row['MACD_Signal'] else -0.2
            
        sentiment_score = float(price_score + rsi_score + macd_score)
        sentiment_score = max(-1.0, min(1.0, sentiment_score))
        
        # Determine signal based on score
        if sentiment_score > 0.15:
            signal = "Bullish"
        elif sentiment_score < -0.15:
            signal = "Bearish"
        else:
            signal = "Neutral"
            
        # Define headline templates
        bullish_headlines = [
            f"Institutional buying ramps up for {symbol} after strong technical breakout.",
            f"Market analysts raise price targets for {symbol} citing stellar performance indices.",
            f"{symbol} leads tech sector gains as retail interest surges to new heights.",
            f"Strategic partnership rumors spark bullish momentum for {symbol}.",
            f"{symbol} options market indicates traders positioning for a major upward breakout."
        ]
        
        bearish_headlines = [
            f"{symbol} faces key overhead resistance; technical indicators point to short-term pullback.",
            f"Profit taking triggers selloff in {symbol} ahead of critical macro economic reviews.",
            f"Supply chain bottlenecks and rising costs raise caution flags for {symbol} growth.",
            f"Analysts downgrade {symbol} to 'Hold' following valuation analysis concerns.",
            f"Heavy volume distribution observed in {symbol} signaling institutional trimming."
        ]
        
        neutral_headlines = [
            f"{symbol} trades in tight consolidation range; consolidation expected to continue.",
            f"Investors stay on sidelines for {symbol} as earnings announcement approaches.",
            f"{symbol} remains steady as sector averages balance out macro pressures.",
            f"Mixed technical signals keep {symbol} trendless in the mid-session.",
            f"Options volume drops for {symbol} indicating wait-and-see market posture."
        ]
        
        # Sample headlines based on signal
        headlines = []
        random.seed(hash(symbol) + int(last_row['Close'])) # deterministic seed based on stock price
        
        if signal == "Bullish":
            chosen = random.sample(bullish_headlines, 2) + random.sample(neutral_headlines, 1)
        elif signal == "Bearish":
            chosen = random.sample(bearish_headlines, 2) + random.sample(neutral_headlines, 1)
        else:
            chosen = [random.choice(bullish_headlines), random.choice(bearish_headlines), random.choice(neutral_headlines)]
            
        for headline in chosen:
            # Random sentiment score for each headline matching its general nature
            if headline in bullish_headlines:
                h_score = random.uniform(0.3, 0.8)
                h_type = "Positive"
            elif headline in bearish_headlines:
                h_score = random.uniform(-0.8, -0.3)
                h_type = "Negative"
            else:
                h_score = random.uniform(-0.2, 0.2)
                h_type = "Neutral"
            headlines.append({
                'text': headline,
                'score': float(h_score),
                'type': h_type
            })
            
        return {
            'success': True,
            'symbol': symbol,
            'sentiment_score': sentiment_score,
            'signal': signal,
            'headlines': headlines
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }
