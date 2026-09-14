# EquityAI — Stock Market Prediction Platform

A full-stack Flask web application for stock market technical analysis and machine learning-based price forecasting. The platform supports classical ML models (Linear Regression, Random Forest, XGBoost) and deep learning (LSTM / MLP fallback), interactive Plotly charts, a local AI chatbot assistant, PDF report generation, and user authentication.

> ⚠️ **Disclaimer**: This platform is for academic and demonstration purposes only. Predictions are highly experimental and subject to market volatility. Nothing in this application constitutes professional financial, investment, or legal advice.

---

## Features

| Feature | Description |
|---|---|
| 📊 **Interactive Dashboard** | Candlestick charts, volume, SMA/EMA, Bollinger Bands, MACD, RSI via Plotly |
| 🤖 **ML Studio** | Train Linear Regression, Random Forest, XGBoost, and LSTM models on any symbol |
| 🧠 **LSTM / MLP Forecasting** | Deep learning 30-day future price forecasting with epoch loss curves |
| 💬 **AI Chatbot** | Local rule-based NLP assistant; upgrades to Gemini or OpenAI when API keys are set |
| 📄 **PDF Reports** | One-click downloadable analysis reports with model metrics and predictions |
| 🔒 **Auth System** | Secure user registration, login, and session management via Flask-Login |
| 📁 **Custom CSV Upload** | Upload your own OHLCV datasets (`.csv` or `.txt`) |
| 🌙 **4 Themes** | Glass Dark, Glass Light, Cyberpunk Neon, Forest Mint |

---

## Tech Stack

- **Backend**: Python 3.10+, Flask 3, SQLAlchemy, Flask-Login
- **ML/DL**: scikit-learn, XGBoost, TensorFlow/Keras (LSTM), joblib
- **Data**: pandas, NumPy
- **Visualization**: Plotly.js (frontend), Matplotlib + Seaborn (backend heatmaps), ReportLab (PDF)
- **Database**: SQLite (default) — configurable to PostgreSQL via `DATABASE_URL`
- **Frontend**: Bootstrap 5, Bootstrap Icons, NProgress

---

## Project Structure

```
Stock_Market_Prediction/
├── app.py                     # Flask application factory + entry point
├── config.py                  # Configuration class (reads from .env)
├── requirements.txt           # Python dependencies
├── .env.example               # Environment variable template
│
├── controllers/               # Flask blueprints (routes)
│   ├── auth_controller.py     # Register, login, logout
│   ├── dashboard_controller.py# Main dashboard, stock API, upload, profile
│   ├── ml_controller.py       # Train models, predict, forecast, performance
│   ├── chatbot_controller.py  # Chatbot message, history, clear
│   └── report_controller.py  # PDF report download
│
├── services/                  # Business logic
│   ├── data_service.py        # Symbol indexing, CSV parsing, indicator computation
│   ├── ml_service.py          # Classical ML train/evaluate/predict
│   ├── dl_service.py          # LSTM / MLP fallback train/forecast
│   ├── chatbot_service.py     # AI response routing (Gemini / OpenAI / local NLP)
│   ├── report_service.py      # ReportLab PDF generation
│   ├── sentiment_service.py   # Technical-signal-based sentiment scoring
│   └── visualization_service.py  # Seaborn correlation heatmap
│
├── database/
│   ├── __init__.py            # SQLAlchemy instance
│   ├── models.py              # User, PredictionHistory, ModelPerformance, ChatMessage
│   └── database_helper.py    # CRUD helpers
│
├── templates/                 # Jinja2 HTML templates
│   ├── base.html              # Shared layout (navbar, flash messages, theme)
│   ├── dashboard.html         # Main analysis dashboard
│   ├── ml_models.html         # ML Studio (training + leaderboard)
│   ├── chatbot.html           # AI Chatbot interface
│   ├── profile.html           # User prediction history
│   ├── login.html             # Sign in
│   └── register.html         # Sign up
│
├── static/
│   ├── css/style.css          # Global styles, themes, component styles
│   └── js/
│       ├── chart_renderer.js  # Plotly chart rendering + dashboard logic
│       ├── ml_trainer.js      # ML training triggers + leaderboard
│       └── chatbot.js         # Chatbot UI + Markdown renderer
│
├── dataset/
│   └── archive/Data/
│       ├── Stocks/            # 7,195 US stock historical files (.txt, OHLCV)
│       └── ETFs/              # 1,344 ETF historical files (.txt, OHLCV)
│
├── uploads/                   # User-uploaded custom CSV datasets (auto-created)
├── models/                    # Saved trained model files (.joblib / .h5) (auto-created)
└── instance/                  # SQLite database file (auto-created)
```

---

## Quick Start

### 1. Clone the repository

```bash
git clone <your-repo-url>
cd Stock_Market_Prediction
```

### 2. Create and activate a virtual environment

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

> **Note on TensorFlow**: TensorFlow requires the Microsoft Visual C++ Redistributable on Windows. If TensorFlow fails to import, the platform will automatically fall back to a scikit-learn MLP model for LSTM functionality.

### 4. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` and set at minimum a strong `SECRET_KEY`. All other variables are optional.

### 5. Run the application

```bash
python app.py
```

The app will print the local and network URLs on startup. Open `http://127.0.0.1:5000` in your browser.

To enable debug mode for development:

```bash
FLASK_DEBUG=true python app.py
```

---

## Environment Variables

See [`.env.example`](.env.example) for all available options.

| Variable | Required | Description |
|---|---|---|
| `SECRET_KEY` | **Yes** (production) | Flask session signing key — use a long random string |
| `DATABASE_URL` | No | Full SQLAlchemy database URI. Defaults to SQLite at `instance/stock_platform.db` |
| `GEMINI_API_KEY` | No | Google Gemini API key — enables generative AI chatbot responses |
| `OPENAI_API_KEY` | No | OpenAI API key — fallback if Gemini key is not set |
| `FLASK_DEBUG` | No | Set to `true` to enable Werkzeug debug mode (development only) |

---

## Dataset

The platform ships with the [Huge Stock Market Dataset](https://www.kaggle.com/datasets/borismarjanovic/price-volume-data-for-all-us-stocks-etfs) by Boris Marjanovic (Kaggle).

- **7,195 US Stocks** in `dataset/archive/Data/Stocks/`
- **1,344 US ETFs** in `dataset/archive/Data/ETFs/`
- Format: `Date, Open, High, Low, Close, Volume, OpenInt` (comma-separated)
- Date range: varies per symbol, majority from 1970–2017

Custom datasets can be uploaded via the dashboard Upload button. Supported formats: `.csv`, `.txt` with standard OHLCV columns.

---

## ML Models

| Model | Type | Library | Notes |
|---|---|---|---|
| Linear Regression | Classical | scikit-learn | Baseline; fast, interpretable |
| Random Forest | Classical | scikit-learn | Ensemble; supports feature importance |
| XGBoost | Classical | xgboost | Gradient boosting; top performer on tabular data |
| LSTM | Deep Learning | TensorFlow/Keras | Sequential; 30-day autoregressive forecast |
| MLP (fallback) | Deep Learning | scikit-learn | Used when TensorFlow is unavailable |

All classical models use a **chronological 80/20 train/test split** on lag features (Close, Open, High, Low, Volume lags 1–5 + technical indicator lags). LSTM models use the same split applied **before** scaler fitting to prevent data leakage.

---

## API Endpoints

| Method | Route | Description |
|---|---|---|
| `GET` | `/api/stock/<symbol>` | Full OHLCV + indicators (last 1000 rows) |
| `GET` | `/api/stock/<symbol>/summary` | Latest metrics (price, RSI, MACD, etc.) |
| `POST` | `/api/train/ml/<symbol>` | Train classical ML models |
| `POST` | `/api/train/lstm/<symbol>` | Train LSTM model |
| `POST` | `/api/predict/<symbol>` | Generate next-day price prediction |
| `GET` | `/api/forecast/lstm/<symbol>` | Get multi-day LSTM forecast |
| `GET` | `/api/performance/<symbol>` | Model leaderboard metrics |
| `GET` | `/api/feature_importance/<symbol>` | Feature importance (RF / XGBoost) |
| `GET` | `/api/sentiment/<symbol>` | Technical sentiment analysis |
| `GET` | `/api/stock/<symbol>/heatmap` | Correlation heatmap (base64 PNG) |
| `POST` | `/api/chatbot/message` | Send chatbot message |
| `GET` | `/report/download/<symbol>` | Download PDF analysis report |

---

## Security Notes

- Set a strong `SECRET_KEY` in production — the app emits a `UserWarning` if the default key is used.
- Debug mode (`FLASK_DEBUG`) must **not** be enabled in production as it exposes the Werkzeug interactive debugger.
- The `/login?next=` redirect parameter is validated to reject external URLs.
- Passwords are hashed using Werkzeug's `generate_password_hash` (PBKDF2-SHA256).

---

## License

This project is released for academic and educational purposes. See individual dataset licenses for data usage terms.
