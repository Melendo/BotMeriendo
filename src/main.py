
import discord
from discord.ext import commands
import asyncio
import os
from src.config import TOKEN, PREFIX, validate_config
from src.utils.logger import logger

# Validar configuración antes de iniciar
validate_config()

# Configuración del bot
descripcion = "Bot todopoderoso del linaje Meriendo"
intents = discord.Intents.all()
intents.message_content = True

bot = commands.Bot(command_prefix=PREFIX, intents=intents, description=descripcion)

# Función para cargar extensiones
async def load_extensions():
    extensions = [
        "src.cogs.general",
        "src.cogs.music",
        "src.cogs.events"
    ]
    for ext in extensions:
        try:
            await bot.load_extension(ext)
            logger.info(f"Cargado extensión: {ext}")
        except Exception as e:
            logger.error(f"Error cargando extensión {ext}: {e}")

async def main():
    async with bot:
        await load_extensions()
        await bot.start(TOKEN)

if __name__ == "__main__":
    # Manejo limpio de cierre con señal de sistema
    import signal
    loop = asyncio.get_event_loop()
    
    def shutdown():
        tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        for task in tasks:
            task.cancel()
        logger.info("Cierre del bot iniciado...")

    loop.add_signal_handler(signal.SIGTERM, shutdown)
    loop.add_signal_handler(signal.SIGINT, shutdown)

    try:
        asyncio.run(main())
    except (asyncio.CancelledError, KeyboardInterrupt):
        logger.info("Bot detenido correctamente.")
    finally:
        logger.info("Limpieza finalizada.")
