
import discord
from discord.ext import commands
import asyncio
from src.utils.logger import logger
from src.cogs.music import music_queues  # Importamos para limpiar colas

class Events(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        logger.info(f'We have logged in as {self.bot.user}')

    @commands.Cog.listener()
    async def on_member_join(self, member):
        await member.send(f'Bienvenido al server {member.name}, bonito nombre por cierto!')

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandNotFound):
            return 
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("Faltan argumentos para este comando.")
        elif isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"Espera un poco, comando en enfriamiento: {error.retry_after:.2f}s")
        else:
            logger.error(f"Error no controlado: {error}")
            await ctx.send("Ocurrió un error inesperado.")

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        # Lógica combinada para desconexión y limpieza
        
        # Caso 1: El bot se desconecta o le desconectan
        if member == self.bot.user and before.channel and not after.channel:
            if before.channel.guild.id in music_queues:
                music_queues[before.channel.guild.id] = []
                logger.info(f"Cola limpiada para {before.channel.guild.name} tras desconexión del bot.")

        # Caso 2: Desconexión automática si se queda solo
        if before.channel is not None:
             # Verificar si el bot está conectado en ese guild
            voice_client = discord.utils.get(self.bot.voice_clients, guild=before.channel.guild)
            
            # Si el bot está en el canal del que alguien salió
            if voice_client and voice_client.channel == before.channel:
                 # Si solo queda 1 miembro (el bot)
                if len(before.channel.members) == 1:
                    logger.info(f"Bot solo en {before.channel.name}, iniciando timer de desconexión.")
                    await asyncio.sleep(60)
                    
                    # Verificar de nuevo tras el tiempo
                    if len(before.channel.members) == 1 and voice_client.is_connected():
                        await voice_client.disconnect()
                        if before.channel.guild.id in music_queues:
                            music_queues[before.channel.guild.id] = []
                        logger.info(f"Desconectado de {before.channel.name} por inactividad.")

async def setup(bot):
    await bot.add_cog(Events(bot))
