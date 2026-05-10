"""
Application configuration.
Loads environment variables and provides config constants.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# --- Database ---
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/enterprise.db")

# --- NVIDIA NIM ---
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY", "")
NVIDIA_MODEL = os.getenv("NVIDIA_MODEL", "meta/llama-3.1-70b-instruct")

# --- App ---
APP_TITLE = "Intelligent Enterprise Assistant"
APP_VERSION = "0.1.0"
DEBUG = os.getenv("DEBUG", "True").lower() == "true"
