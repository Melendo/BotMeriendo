# BotMeriendo
Bot de música y utilidades para Discord, modularizado y listo para desplegar de forma sencilla con Docker. Permite la reproducción de música desde YouTube, control de colas y optimización de recursos mediante auto-desconexión.

# Descripción detallada
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
Para levantar la aplicación localmente en modo desarrollo:
```bash
python src/main.py
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

### Pruebas (Testing)
> [!NOTE]
> Este proyecto no cuenta actualmente con una suite de pruebas automatizadas. Para verificar su correcto funcionamiento, inicia el bot, invítalo a un servidor de Discord y prueba comandos interactivos como `!play` o `!help`.

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
│   │   └── state.py   # Estado compartido de colas y reproducción
│   ├── config.py      # Validación y carga de variables de entorno
│   └── main.py        # Punto de entrada y arranque de la aplicación
├── Dockerfile         # Receta de construcción de la imagen de Docker
├── docker-compose.yml # Orquestación del contenedor
└── requirements.txt   # Dependencias de Python
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
