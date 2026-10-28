# BotMeriendo
Bot de música y utilidades para Discord, modularizado y listo para desplegar de forma sencilla con Docker. Permite la reproducción de música desde YouTube, control de colas y optimización de recursos mediante auto-desconexión.

## Descripción detallada
BotMeriendo nace como una solución personalizada y ligera para reproducir música y ofrecer herramientas de utilidad en servidores de Discord. A diferencia de los bots públicos comerciales, que suelen imponer limitaciones de uso, suscripciones o anuncios de audio, este bot ofrece control total al administrador del servidor. 

Está diseñado principalmente para grupos de amigos, comunidades pequeñas y desarrolladores que desean alojar su propio bot musical en un servidor local, VPS o Raspberry Pi. Además de reproducir pistas de audio individuales y listas de reproducción de YouTube, incorpora una característica clave de eficiencia energética y consumo de ancho de banda: se desconecta automáticamente de los canales de voz cuando detecta inactividad (si se queda solo durante 1 minuto).

## Índice
- [Requisitos Previos](#requisitos-previos)
- [Instalación](#instalación)
- [Configuración](#configuración)
- [Ejecución y Uso](#ejecución-y-uso)
- [Arquitectura y Stack Tecnológico](#arquitectura-y-stack-tecnológico)
- [Contribuciones](#contribuciones)
- [Licencia y Créditos](#licencia-y-créditos)

## Requisitos Previos
Antes de comenzar con la instalación, asegúrate de cumplir con los siguientes requisitos de entorno y software:
- **Sistema Operativo recomendado:** Linux (ej. Debian/Ubuntu para servidores y Raspberry Pi), macOS o Windows.
- **Runtime o Lenguaje:** Python 3.11+.
- **Gestor de paquetes:** `pip` (incluido por defecto con Python).
- **Dependencias del sistema:**
  - **FFmpeg** (obligatorio para la reproducción de audio si se ejecuta localmente).
  - **Docker** y **Docker Compose** (opcional, recomendado para producción y despliegue rápido).
- **Discord Developer Portal:** Un token de bot de Discord activo y con los privilegios e intents de voz habilitados.

## Instalación
Sigue estos pasos para clonar el repositorio e instalar las dependencias:

### Opción 1: Ejecución Local (Desarrollo)
1. **Clonar el repositorio:**
   ```bash
   git clone https://github.com/Melendo/botMeriendo.git
   cd botMeriendo
   ```

2. **Instalar FFmpeg en el sistema:**
   - En **Ubuntu/Debian**:
     ```bash
     sudo apt update && sudo apt install ffmpeg -y
     ```
   - En **macOS** (usando Homebrew):
     ```bash
     brew install ffmpeg
     ```
   - En **Windows**: Descarga el binario de la página oficial de FFmpeg y añádelo al PATH de tu sistema.

3. **Crear e iniciar el entorno virtual de Python:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # En Windows usa: venv\Scripts\activate
   ```

4. **Instalar las dependencias de Python:**
   ```bash
   pip install -r requirements.txt
   ```

### Opción 2: Despliegue con Docker (Recomendado)
Si prefieres desplegar mediante contenedores, no necesitas instalar Python ni FFmpeg localmente. Solo clona el repositorio y asegúrate de tener Docker instalado:
```bash
git clone https://github.com/Melendo/botMeriendo.git
cd botMeriendo
```

## Configuración
El proyecto utiliza un archivo de configuración `.env` para gestionar las credenciales y el prefijo de comandos. Duplica el archivo de ejemplo y edita los valores necesarios:
```bash
cp .env.example .env
```

### Variables de Entorno
| Variable | Descripción | Valor por Defecto | Requerido |
| :--- | :--- | :--- | :---: |
| `TOKEN` | Token de autenticación de tu bot obtenido en Discord Developer Portal | `TokedeDc` | Sí |
| `TRGGKEY` | Símbolo o prefijo para activar los comandos del bot (ej. `!`, `?`, `-`) | `SimboloParaComandos` | Sí |

## Ejecución y Uso

### Entorno de Desarrollo
Para levantar la aplicación localmente en modo desarrollo (desde la raíz del repo):
```bash
python -m src.main
```

### Ejecución con Docker
Si prefieres ejecutar el bot de forma aislada y en segundo plano mediante contenedores:

- **Iniciar el contenedor:**
  ```bash
  docker-compose up -d --build
  ```
- **Ver los logs en tiempo real:**
  ```bash
  docker-compose logs -f
  ```
- **Detener el bot:**
  ```bash
  docker-compose down
  ```

### Comandos
Todos funcionan con el prefijo (`!play`) y como comando de barra (`/play`). `!comandos` los lista.

| Comando | Qué hace |
| :--- | :--- |
| `play <url o búsqueda>` | Añade una canción o una playlist de YouTube (máx. 30 en cola) |
| `pause` / `resume` / `skip` / `stop` | Controlan la reproducción |
| `queue` | Muestra la cola |
| `nowplaying` (`np`) | Muestra la canción que suena |
| `shuffle` | Mezcla la cola |
| `loop` | Repite la canción actual (activar/desactivar) |
| `remove <número>` | Quita una canción de la cola |
| `clear` | Vacía la cola sin parar la canción actual |
| `join` / `leave` | Entra o sale del canal de voz |
| `ping` / `hola` / `comandos` | Utilidades |

Los comandos de barra se registran al arrancar. La primera vez Discord puede tardar un rato en mostrarlos.

### Cookies de YouTube
Si YouTube responde *"Sign in to confirm you're not a bot"*, el bot necesita cookies:
- **Local:** exporta tus cookies a `cookies.txt` en la raíz (ver `cookies.example.txt`). Está en `.gitignore`: no se sube.
- **Deploy con GitHub Actions:** crea el secreto `YT_COOKIES` con el contenido de ese archivo. El workflow escribe `cookies.txt` antes de construir la imagen.

### Pruebas (Testing)
```bash
pip install -r requirements-dev.txt
pytest -q
```
Los tests no se conectan a Discord ni a YouTube. GitHub Actions los ejecuta en cada push y Pull Request; el deploy solo corre si pasan.

## Arquitectura y Stack Tecnológico
El bot está estructurado modularmente utilizando la extensión de "Cogs" de `discord.py` para separar los comandos y el ciclo de vida del bot de manera limpia y escalable.

- **Backend / Core:** Python 3.11+, [discord.py](https://github.com/Rapptz/discord.py) (v2.x con soporte de voz), [yt-dlp](https://github.com/yt-dlp/yt-dlp) (para la descarga y streaming dinámico de audio), [PyNaCl](https://github.com/pyca/pynacl) (para cifrado de audio de Discord).
- **Base de Datos / Almacenamiento:** No requiere base de datos persistente. Utiliza memoria RAM (`src/utils/state.py`) para gestionar la cola de reproducción en vivo por servidor.
- **Infraestructura / DevOps:** Docker (imagen base `python:3.11-slim` con instalación interna de `ffmpeg`), Docker Compose para arranque con reinicio automático (`unless-stopped`).

### Estructura de Directorios
```text
botMeriendo/
├── src/
│   ├── cogs/          # Módulos del bot
│   │   ├── events.py  # Manejo de eventos (salidas, desconexiones, errores)
│   │   ├── general.py # Comandos de texto básicos y utilidades
│   │   └── music.py   # Lógica y comandos de reproducción musical
│   ├── utils/         # Clases y funciones auxiliares
│   │   ├── logger.py  # Configuración rotativa y formateada de logs
│   │   ├── music_service.py # Descarga y caché de audio con yt-dlp
│   │   ├── queue_utils.py   # Funciones puras de la cola (fáciles de probar)
│   │   └── state.py   # Estado compartido de colas y reproducción
│   ├── config.py      # Validación y carga de variables de entorno
│   └── main.py        # Punto de entrada y arranque de la aplicación
├── tests/             # Tests con pytest
├── Dockerfile         # Receta de construcción de la imagen de Docker
├── docker-compose.yml # Orquestación del contenedor
├── requirements.txt   # Dependencias de Python
└── requirements-dev.txt # Dependencias para tests
```

## Contribuciones
Si deseas contribuir al desarrollo de este proyecto, por favor sigue estos pasos:
1. Haz un Fork del repositorio.
2. Crea una nueva rama para tu funcionalidad:
   ```bash
   git checkout -b feature/nueva-funcionalidad
   ```
3. Realiza tus cambios y haz un commit claro siguiendo convenciones:
   ```bash
   git commit -m 'Añade nueva funcionalidad'
   ```
4. Sube los cambios a tu rama:
   ```bash
   git push origin feature/nueva-funcionalidad
   ```
5. Abre una Pull Request explicando detalladamente los cambios realizados.

## Licencia y Créditos

### Licencia
Este proyecto está bajo la Licencia [Apache 2.0](https://www.apache.org/licenses/LICENSE-2.0).

### Créditos y Agradecimientos
- Desarrollado por [Melendo](https://github.com/Melendo).
