# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Comandos `nowplaying` (`np`), `shuffle`, `loop`, `remove <n>` y `clear`.
- Todos los comandos funcionan también como comandos de barra (`/play`, ...).
- Descarga adelantada de la siguiente canción: sin silencio entre canciones.
- Caché de audio por id de vídeo (repetir una canción no la vuelve a bajar).
- Tests con pytest y job de tests en GitHub Actions; el deploy solo corre si pasan.
- Secreto opcional `YT_COOKIES` para crear `cookies.txt` en el deploy.

### Changed
- Playlists mucho más rápidas: solo se piden url y título (`extract_flat`).
- Se piden solo los intents necesarios en vez de `Intents.all()`.
- Versiones de dependencias fijadas (`yt-dlp` con mínimo, sin techo).
- `bot.log` rota a los 5 MB (máximo 4 archivos).
- La caché de audio se limpia cada hora, no solo al arrancar.
- `cookies.txt` pasa a `cookies.example.txt`; el real se ignora en git.

### Fixed
- El cog de música no cargaba en Python 3.11 (f-string con barra invertida).
- `docker stop` no cerraba el bot de forma limpia.
- El límite de 30 canciones no se aplicaba.
- `!queue` fallaba con colas largas (límite de 2000 caracteres de Discord).
- Si una descarga fallaba se podía reproducir otra canción con el mismo título.
- `!comandos` ponía todo en "Sin categoría".
- La auto-desconexión miraba el canal antiguo y contaba otros bots como personas.
- El botón de pausa podía quedar con el texto equivocado.

## [1.0.0] - 2026-06-28

### Added
- **Música y Reproducción (YouTube):**
  - Comando `!play` para reproducir música mediante términos de búsqueda en YouTube o enlaces directos (soporte para vídeos individuales y playlists de YouTube).
  - Optimización en el procesado de enlaces de YouTube mediante extracción rápida de metadatos (`extract_flat`) para acelerar la carga de playlists.
  - Resolución JIT (Just-In-Time) de streams de audio usando hilos (`asyncio.to_thread`) justo antes de reproducir, previniendo bloqueos del loop de eventos del bot.
  - Cola de reproducción por servidor (`!queue`) con un límite máximo de hasta 30 canciones simultáneas (`MAX_QUEUE_SIZE`).
  - Panel interactivo de reproducción (`MusicControls`) con botones interactivos de Discord UI para pausar/reanudar (`⏸️ Pausa` / `▶️ Reanudar`) y saltar canciones (`⏭️ Skip`).
  - Comandos dedicados de música: `!join` (unirse al canal de voz), `!leave` (desconectar del canal), `!stop` (detener reproducción y vaciar la cola), `!pause` (pausar), `!resume` (reanudar) y `!skip` (saltar canción).
- **Gestión de Eventos y Robustez:**
  - Auto-desconexión por inactividad: Desconexión automática del canal de voz si el bot se queda solo durante 1 minuto, limpiando la cola del servidor.
  - Limpieza de cola automática si el bot se desconecta o es desconectado del canal de voz por cualquier otra causa.
  - Mensaje de bienvenida personalizado por mensaje directo (DM) enviado automáticamente a nuevos miembros del servidor.
  - Manejo de excepciones centralizado (`on_command_error`) para errores comunes (comandos en cooldown, argumentos faltantes, etc.) proporcionando feedback en el chat.
- **Utilidades Generales:**
  - Comando de ayuda personalizado (`!comandos`) que muestra todos los comandos disponibles agrupados por categorías utilizando Embeds de Discord.
  - Comandos básicos de interacción: `!ping` (responde `pong`) y `!hola` (saludo que menciona al usuario).
- **Arquitectura, Infraestructura y DevOps:**
  - Estructuración modular basada en `Cogs` de `discord.py` (`general`, `music`, `events`).
  - Despliegue contenerizado con Docker y orquestación con Docker Compose con reinicio automático configurado (`unless-stopped`).
  - Configuración flexible y segura a través de variables de entorno mediante un archivo `.env` (`TOKEN`, `TRGGKEY`).
  - Sistema de registro (logging) persistente y limpio con rotación en el archivo `bot.log` y salida estándar filtrando logs innecesarios de `discord.py`.
  - Cierre y apagado ordenado de la aplicación manejando de forma limpia señales del sistema (`SIGTERM`, `SIGINT`).
