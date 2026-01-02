
# 🤖 botMeriendo

Bot de música y utilidades para Discord, modularizado y listo para desplegar con Docker.

## 🚀 Instalación y Despliegue

### Requisitos Previos
- [Docker](https://docs.docker.com/get-docker/) y [Docker Compose](https://docs.docker.com/compose/install/) instalados.
- Un Token de Bot de Discord ([Conseguir aquí](https://discord.com/developers/applications)).
- (Opcional) Un entorno Python 3.11+ si vas a ejecutar localmente sin Docker.

### Configuración
1. Clona el repositorio:
   ```bash
   git clone <url-del-repo>
   cd botMeriendo
   ```

2. Crea el archivo de variables de entorno:
   ```bash
   cp .env.example .env
   ```

3. Edita el archivo `.env` y añade tu token:
   ```env
   TOKEN=tu_token_aqui_sin_comillas
   TRGGKEY=!
   ```

### 🐳 Ejecución con Docker (Recomendado)
Para iniciar el bot en segundo plano:
```bash
docker-compose up -d --build
```

Para ver los logs:
```bash
docker-compose logs -f
```

Para detener el bot:
```bash
docker-compose down
```

### 💻 Ejecución Local (Desarrollo)
1. Instala las dependencias de sistema (necesitas `ffmpeg`):
   - **Debian/Ubuntu**: `sudo apt install ffmpeg`
   - **Windows**: Descargar y añadir al PATH.

2. Crea un entorno virtual e instala dependencias:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Ejecuta el bot:
   ```bash
   python src/main.py
   ```

## 📂 Estructura del Proyecto
```
botMeriendo/
├── src/
│   ├── cogs/          # Módulos del bot
│   │   ├── events.py  # Manejo de eventos (join, errores, voz)
│   │   ├── general.py # Comandos básicos
│   │   └── music.py   # Lógica de música
│   ├── utils/         # Utilidades
│   │   ├── logger.py  # Configuración de logs
│   │   └── state.py   # Estado compartido (colas)
│   ├── config.py      # Configuración y validación
│   └── main.py        # Punto de entrada
├── Dockerfile         # Imagen de Docker
├── docker-compose.yml # Orquestación de contenedores
└── requirements.txt   # Dependencias Python
```

## ✨ Características
- **Música**: Reproducción desde YouTube (búsqueda y enlaces direcos), playlists, control de cola.
- **Auto-Desconexión**: El bot sale del canal de voz si se queda solo por 1 minuto.
- **Gestión de Errores**: Feedback visual en Discord cuando algo falla.
- **Logs**: Sistema de logging rotativo y limpio.
