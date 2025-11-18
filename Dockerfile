# Usamos Python 3.11 versión slim (ligera, ideal para Raspberry Pi)
FROM python:3.11-slim

# 1. Instalamos dependencias del SISTEMA OPERATIVO
# ffmpeg: Necesario para reproducir audio y descargar de YT
# libopus0: Codec de audio requerido por Discord
# gcc y python3-dev: A veces necesarios para compilar PyNaCl en arquitecturas ARM/Pi
RUN apt-get update && \
    apt-get install -y ffmpeg libopus0 gcc python3-dev && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# 2. Establecemos el directorio de trabajo dentro del contenedor
WORKDIR /app

# 3. Copiamos las dependencias e instalamos
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. Copiamos el código del bot
COPY bot.py .

# 5. Comando para ejecutar el bot
CMD ["python", "bot.py"]