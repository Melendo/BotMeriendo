
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

TOKEN = os.getenv("TOKEN")
TRGGKEY = os.getenv("TRGGKEY")

def validate_config():
    if not TOKEN:
        raise ValueError("TOKEN no encontrado en el archivo .env")

# Prefijo del bot
PREFIX = TRGGKEY if TRGGKEY else "!"
