# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Ninguno (todos los desarrollos se encuentran liberados en la versión 1.0.0).

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
