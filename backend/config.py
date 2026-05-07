"""
Application configuration.
Loads environment variables and provides config constants.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# --- Database ---
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/enterprise.db")

# --- OpenAI ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# --- App ---
APP_TITLE = "Intelligent Enterprise Assistant"
APP_VERSION = "0.1.0"
DEBUG = os.getenv("DEBUG", "True").lower() == "true"
