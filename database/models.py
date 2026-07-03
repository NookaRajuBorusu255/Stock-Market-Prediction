from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from database import db

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(128), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    predictions = db.relationship('PredictionHistory', backref='user', lazy='dynamic')
    chat_messages = db.relationship('ChatMessage', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
        
    def __repr__(self):
        return f'<User {self.username}>'


class PredictionHistory(db.Model):
    __tablename__ = 'prediction_history'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    stock_symbol = db.Column(db.String(16), nullable=False, index=True)
    model_name = db.Column(db.String(32), nullable=False)
    prediction_date = db.Column(db.Date, nullable=False)
    predicted_price = db.Column(db.Float, nullable=False)
    actual_price = db.Column(db.Float, nullable=True)  # Updated once real price is available
    confidence_score = db.Column(db.Float, nullable=False)  # 0.0 to 100.0
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Prediction {self.stock_symbol} by User {self.user_id}>'


class ModelPerformance(db.Model):
    __tablename__ = 'model_performance'
    
    id = db.Column(db.Integer, primary_key=True)
    stock_symbol = db.Column(db.String(16), nullable=False, index=True)
    model_name = db.Column(db.String(32), nullable=False)
    mae = db.Column(db.Float, nullable=False)
    rmse = db.Column(db.Float, nullable=False)
    r2 = db.Column(db.Float, nullable=False)
    mape = db.Column(db.Float, nullable=False)
    trained_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<ModelPerformance {self.model_name} for {self.stock_symbol}>'

class ChatMessage(db.Model):
    __tablename__ = 'chat_messages'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    sender = db.Column(db.String(10), nullable=False)  # 'user' or 'bot'
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<ChatMessage {self.id} by User {self.user_id}>'
