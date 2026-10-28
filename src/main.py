
import discord
from discord.ext import commands
import asyncio
import signal
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
    # Manejo limpio de cierre con señal de sistema.
    # Se registra en el loop que de verdad corre (el de asyncio.run).
    loop = asyncio.get_running_loop()

    def shutdown():
        logger.info("Cierre del bot iniciado...")
        loop.create_task(bot.close())

    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, shutdown)

    async with bot:
        await load_extensions()
        await bot.start(TOKEN)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (asyncio.CancelledError, KeyboardInterrupt):
        logger.info("Bot detenido correctamente.")
    finally:
        logger.info("Limpieza finalizada.")
