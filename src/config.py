
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

TOKEN = os.getenv("TOKEN")
TRGGKEY = os.getenv("TRGGKEY")

# Spotify (opcional): sin estas claves, los enlaces de Spotify no funcionan
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
SPOTIFY_REFRESH_TOKEN = os.getenv("SPOTIFY_REFRESH_TOKEN")

def validate_config():
    if not TOKEN:
        raise ValueError("TOKEN no encontrado en el archivo .env")

# Prefijo del bot
PREFIX = TRGGKEY if TRGGKEY else "!"
