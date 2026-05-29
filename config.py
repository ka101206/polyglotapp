# config.py
import os

# --- API Settings ---
AI_MODEL = "qwen2.5" 
AI_API_URL = "http://host.docker.internal:11434/v1" 
API_KEY = "ollama" 

# --- Language Definitions ---
SUPPORTED_LANGUAGES = ["Japanese", "Spanish", "French", "Italian", "Chinese", "Korean"]
JAPANESE_MODES = ["なし", "ふりがな", "かなのみ"]

# --- Audio Settings ---
DEFAULT_SILENCE_TIMEOUT = 2.5  
DEFAULT_SENSITIVITY = 50.0
DEFAULT_TTS_SPEED = 1.2        

# --- UI Bounds ---
TIMEOUT_RANGE = (1.0, 10.0)
SPEED_RANGE = (1.0, 2.0)
SENSITIVITY_RANGE = (0.0, 100.0)

# --- Immersion Mode ---
IMMERSION_MODE = False