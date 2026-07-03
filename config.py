import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    # Security
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-129847198274")
    
    # Database configuration
    # Can be easily switched to PostgreSQL by setting SQLALCHEMY_DATABASE_URI in .env
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL", 
        f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'stock_platform.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Custom File Uploads
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB limit
    
    # Models folder
    MODELS_FOLDER = os.path.join(BASE_DIR, 'models')
    
    # Dataset path
    DATASET_PATH = os.path.join(BASE_DIR, 'dataset', 'archive', 'Data')
    
    # Chatbot API Keys (Optional)
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
