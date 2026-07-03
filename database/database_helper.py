from database import db
from database.models import User, PredictionHistory, ModelPerformance
from datetime import datetime

# --- User CRUD ---

def create_user(username, email, password):
    user = User(username=username, email=email)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return user

def get_user_by_id(user_id):
    return db.session.get(User, user_id)

def get_user_by_username(username):
    return User.query.filter_by(username=username).first()

def get_user_by_email(email):
    return User.query.filter_by(email=email).first()


# --- Predictions CRUD ---

def save_prediction(user_id, stock_symbol, model_name, prediction_date, predicted_price, confidence_score, actual_price=None):
    # Ensure prediction_date is a date object
    if isinstance(prediction_date, str):
        prediction_date = datetime.strptime(prediction_date, "%Y-%m-%d").date()
    elif isinstance(prediction_date, datetime):
        prediction_date = prediction_date.date()
        
    pred = PredictionHistory(
        user_id=user_id,
        stock_symbol=stock_symbol.upper(),
        model_name=model_name,
        prediction_date=prediction_date,
        predicted_price=predicted_price,
        actual_price=actual_price,
        confidence_score=confidence_score
    )
    db.session.add(pred)
    db.session.commit()
    return pred

def update_prediction_actual_price(prediction_id, actual_price):
    pred = db.session.get(PredictionHistory, prediction_id)
    if pred:
        pred.actual_price = actual_price
        db.session.commit()
    return pred

def get_user_predictions(user_id):
    return PredictionHistory.query.filter_by(user_id=user_id).order_by(PredictionHistory.prediction_date.desc()).all()


# --- Model Performance CRUD ---

def save_model_performance(stock_symbol, model_name, mae, rmse, r2, mape):
    # Check if a performance record already exists for this model & stock
    existing = ModelPerformance.query.filter_by(
        stock_symbol=stock_symbol.upper(),
        model_name=model_name
    ).first()
    
    if existing:
        existing.mae = mae
        existing.rmse = rmse
        existing.r2 = r2
        existing.mape = mape
        existing.trained_at = datetime.utcnow()
        perf = existing
    else:
        perf = ModelPerformance(
            stock_symbol=stock_symbol.upper(),
            model_name=model_name,
            mae=mae,
            rmse=rmse,
            r2=r2,
            mape=mape
        )
        db.session.add(perf)
        
    db.session.commit()
    return perf

def get_model_performance(stock_symbol, model_name):
    return ModelPerformance.query.filter_by(
        stock_symbol=stock_symbol.upper(),
        model_name=model_name
    ).first()

def get_all_model_performances(stock_symbol):
    return ModelPerformance.query.filter_by(stock_symbol=stock_symbol.upper()).order_by(ModelPerformance.r2.desc()).all()

# --- Chat Messages CRUD ---

def save_chat_message(user_id, sender, message):
    from database.models import ChatMessage
    msg = ChatMessage(user_id=user_id, sender=sender, message=message)
    db.session.add(msg)
    db.session.commit()
    return msg

def get_user_chat_history(user_id):
    from database.models import ChatMessage
    # Fetch last 50 messages, ordered oldest to newest
    return ChatMessage.query.filter_by(user_id=user_id).order_by(ChatMessage.created_at.asc()).limit(50).all()

def clear_user_chat_history(user_id):
    from database.models import ChatMessage
    ChatMessage.query.filter_by(user_id=user_id).delete()
    db.session.commit()
