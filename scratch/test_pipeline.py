import sys
import os

# Append project root directory to path to resolve imports correctly
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from database import db
from database.models import User, PredictionHistory, ModelPerformance
from services.data_service import get_stock_data, list_available_symbols
from services.ml_service import train_and_evaluate_models, load_ml_model_and_predict
from services.dl_service import train_lstm_model
from services.chatbot_service import get_chatbot_response
from services.report_service import generate_pdf_report

def run_tests():
    print("==================================================")
    print("   E2E INTEGRATION AND PIPELINE TEST SUITE")
    print("==================================================")
    
    # Enable test configurations
    app.config['TESTING'] = True
    
    with app.app_context():
        # --- TEST 1: Data Parsing & Indicators ---
        print("\n[TEST 1] Testing Data Services parsing and technical indicators...")
        try:
            symbols = list_available_symbols()
            print(f"-> Indexed {len(symbols)} symbols in local dataset directory.")
            if 'AAPL' not in symbols:
                print("-> FAIL: 'AAPL' not found in symbols. Make sure dataset folder is populated.")
                return
            
            df = get_stock_data('AAPL')
            print(f"-> Successfully loaded AAPL dataframe of shape {df.shape}.")
            required_cols = ['SMA_20', 'SMA_50', 'MACD', 'MACD_Signal', 'RSI', 'Volatility']
            for col in required_cols:
                assert col in df.columns, f"Missing indicator column: {col}"
            print("-> PASS: Data loaded and technical indicators successfully computed.")
        except Exception as e:
            print(f"-> FAIL: Data Service test failed: {str(e)}")
            return
            
        # --- TEST 2: Database Operations ---
        print("\n[TEST 2] Testing Database Models and ORM helpers...")
        try:
            # Create a mock user
            username = "tester_temp_user"
            email = "tester@example.com"
            password = "securepassword123"
            
            # Clean up existing tester if any
            existing_user = User.query.filter_by(username=username).first()
            if existing_user:
                db.session.delete(existing_user)
            existing_email = User.query.filter_by(email=email).first()
            if existing_email:
                db.session.delete(existing_email)
            db.session.commit()
                
            user = User(username=username, email=email)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            
            assert user.id is not None, "Failed to insert User row"
            assert user.check_password(password), "Password check assertion failed"
            
            print(f"-> Created test user '{user.username}' with ID {user.id}.")
            
            # Clean up test user
            db.session.delete(user)
            db.session.commit()
            print("-> PASS: User creation, password hashing, and DB commit work.")
        except Exception as e:
            print(f"-> FAIL: Database test failed: {str(e)}")
            return
            
        # --- TEST 3: Classical Machine Learning ---
        print("\n[TEST 3] Testing Classical ML Models training pipeline (Linear Regression, Random Forest, XGBoost)...")
        try:
            # We train on AAPL
            results = train_and_evaluate_models('AAPL')
            for model_name in ['Linear Regression', 'Random Forest', 'XGBoost']:
                assert model_name in results, f"Missing training output for model: {model_name}"
                print(f"   -> {model_name} metrics: MAE={results[model_name]['mae']:.4f}, R2={results[model_name]['r2']:.4f}")
            
            # Run prediction test
            pred_val, conf = load_ml_model_and_predict('AAPL', 'XGBoost')
            print(f"-> Next day prediction for AAPL with XGBoost: ${pred_val:.2f} (Confidence: {conf:.1f}%)")
            print("-> PASS: Classical ML training, metric evaluation, caching, and inference pass.")
        except Exception as e:
            print(f"-> FAIL: Classical ML pipeline failed: {str(e)}")
            return
            
        # --- TEST 4: LSTM Deep Learning ---
        print("\n[TEST 4] Testing Deep Learning LSTM pipeline (1 Epoch test)...")
        try:
            # Train for 1 epoch to verify model compiles, fits, and outputs metrics
            results = train_lstm_model('AAPL', lookback=60, epochs=1, batch_size=64)
            assert 'loss_history' in results, "Missing loss history in LSTM output"
            print(f"-> LSTM single epoch trained successfully. Test set R2={results['r2']:.4f}")
            print("-> PASS: Keras LSTM model initialized, fitted on sequences, and metrics outputted.")
        except Exception as e:
            print(f"-> FAIL: Deep Learning pipeline failed: {str(e)}")
            return
            
        # --- TEST 5: Chatbot Agent Fallback ---
        print("\n[TEST 5] Testing Intelligent Chatbot local responses...")
        try:
            concept_response = get_chatbot_response("Explain LSTM")
            assert "Long Short-Term Memory" in concept_response, "Failed to return conceptual answer"
            
            stock_response = get_chatbot_response("Analyze AAPL")
            assert "AAPL" in stock_response, "Failed to resolve active symbol context"
            
            dataset_response = get_chatbot_response("dataset info", active_symbol="AAPL")
            assert "Dataset Profile" in dataset_response, "Failed to return dataset information"
            assert "Total Records" in dataset_response
            assert "Start Date" in dataset_response
            
            model_response = get_chatbot_response("what model is selected?", active_symbol="AAPL", active_model="XGBoost")
            assert "Selected Model" in model_response or "XGBoost" in model_response, "Failed to resolve active model context"
            
            print("-> Chatbot Concept response length:", len(concept_response))
            print("-> Chatbot Stock response length:", len(stock_response))
            print("-> Chatbot Dataset response length:", len(dataset_response))
            print("-> Chatbot Model response length:", len(model_response))
            print("-> PASS: Chatbot handles analytical, conceptual, dataset, and active model requests successfully.")
        except Exception as e:
            print(f"-> FAIL: Chatbot Assistant failed: {str(e)}")
            return
            
        # --- TEST 6: Report Generation ---
        print("\n[TEST 6] Testing PDF Report generator compile stream...")
        try:
            pdf_buffer = generate_pdf_report('AAPL')
            pdf_data = pdf_buffer.getvalue()
            print(f"-> Generated ReportLab PDF binary size: {len(pdf_data)} bytes.")
            assert len(pdf_data) > 0, "PDF size is empty"
            print("-> PASS: PDF report layout compiled and generated as BytesIO binary stream.")
        except Exception as e:
            print(f"-> FAIL: PDF Report compilation failed: {str(e)}")
            return
            
        # --- TEST 7: Chat History Persistence ---
        print("\n[TEST 7] Testing Chat history persistence database operations...")
        try:
            from database.database_helper import save_chat_message, get_user_chat_history, clear_user_chat_history
            from database.models import ChatMessage
            
            # Use first user
            user = User.query.first()
            assert user is not None, "No users in DB for testing"
            
            # Clear existing chat history
            clear_user_chat_history(user.id)
            history = get_user_chat_history(user.id)
            assert len(history) == 0, "History was not cleared"
            
            # Save messages
            save_chat_message(user.id, 'user', "Hello AI!")
            save_chat_message(user.id, 'bot', "Hello Human!")
            
            history = get_user_chat_history(user.id)
            assert len(history) == 2, f"History should contain 2 messages, found {len(history)}"
            assert history[0].sender == 'user'
            assert history[1].sender == 'bot'
            print("-> Chat history messages successfully saved, sorted, and fetched.")
            
            # Clear again
            clear_user_chat_history(user.id)
            assert len(get_user_chat_history(user.id)) == 0
            print("-> PASS: Chat history CRUD helper operations fully functional.")
        except Exception as e:
            print(f"-> FAIL: Chat history persistence test failed: {str(e)}")
            return

        # --- TEST 8: Chatbot News & Sentiment integration ---
        print("\n[TEST 8] Testing Chatbot news and sentiment parsing local triggers...")
        try:
            # Query chatbot for news
            news_response = get_chatbot_response("Show AAPL news and sentiment")
            assert "News & Sentiment Report" in news_response, "Chatbot failed to trigger sentiment report"
            print("-> Chatbot triggered and formatted news sentiment output.")
            print("-> PASS: Chatbot news and sentiment local parser integration works.")
        except Exception as e:
            print(f"-> FAIL: Chatbot news integration test failed: {str(e)}")
            return
            
        # --- TEST 9: Advanced Chatbot features, Pivot Points, and Stop Words checks ---
        print("\n[TEST 9] Testing Advanced Chatbot conceptual Q&A, Pivot Points, and Symbol Stop Words...")
        try:
            # 1. Check conceptual explanation trigger
            overfit_res = get_chatbot_response("Explain overfitting and validation loss")
            assert "Overfitting & Loss Metrics" in overfit_res, "Failed to trigger overfitting Q&A explanation"
            
            # 2. Check Pivot Point calculation trigger
            quant_res = get_chatbot_response("Analyze AAPL indicators and summary")
            assert "Pivot Points & Trading Ranges" in quant_res, "Failed to calculate Pivot Points"
            assert "Resistance 1" in quant_res
            assert "Support 1" in quant_res
            
            # 3. Check Symbol tokenization stop word filter (ignores "IS", resolves AAPL)
            symbol_res = get_chatbot_response("What is the price of AAPL?")
            assert "Quantitative Report for **AAPL**" in symbol_res, f"Symbol resolved incorrectly: {symbol_res}"
            
            # 4. Check General Knowledge triggers
            gk_res = get_chatbot_response("what is the stock market?")
            assert "What is the Stock Market?" in gk_res, "Failed to trigger stock market explanation"
            hello_res = get_chatbot_response("Hello Assistant")
            assert "Hello there!" in hello_res, "Failed to trigger greeting"
            
            print("-> Successfully verified Pivot Points, ML Q&A, stop-words, and General Knowledge filters.")
            print("-> PASS: Advanced Chatbot features, token filters, and general knowledge work correctly.")
        except Exception as e:
            print(f"-> FAIL: Advanced Chatbot test failed: {str(e)}")
            return
            
        # --- TEST 10: Seaborn Correlation Heatmap ---
        print("\n[TEST 10] Testing Seaborn Correlation Heatmap Service...")
        try:
            from services.visualization_service import generate_correlation_heatmap
            df = get_stock_data('AAPL')
            for theme in ['dark', 'light', 'cyberpunk', 'forest']:
                img_data = generate_correlation_heatmap(df, theme=theme)
                assert len(img_data) > 100, f"Generated base64 string for theme '{theme}' is too short"
                assert isinstance(img_data, str), f"Generated heatmap for theme '{theme}' should be a string"
            print("-> Successfully verified Seaborn heatmap generation across all visual themes.")
            print("-> PASS: Heatmap base64 streams generated correctly.")
        except Exception as e:
            print(f"-> FAIL: Seaborn Heatmap test failed: {str(e)}")
            return
            
    print("\n==================================================")
    print("   ALL PIPELINE CHECKS PASSED SUCCESSFULLY!")
    print("==================================================")

if __name__ == '__main__':
    run_tests()
