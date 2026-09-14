import os
import warnings
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

_secret_key = os.getenv("SECRET_KEY")
if not _secret_key:
    warnings.warn(
        "SECRET_KEY is not set in environment variables. "
        "Using an insecure default key — DO NOT use this in production. "
        "Set SECRET_KEY in your .env file.",
        stacklevel=1,
    )
    _secret_key = "dev-secret-key-129847198274"

class Config:
    # Security
    SECRET_KEY = _secret_key
    
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
