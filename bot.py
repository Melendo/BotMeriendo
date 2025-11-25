import discord
from discord.ext import commands
from dotenv import load_dotenv
import os
import yt_dlp as youtube_dl
import asyncio
import logging
from discord.ui import Button, View

# Configurar logging al inicio del archivo
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)-8s %(name)s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)

logging.getLogger('discord').setLevel(logging.WARNING)
logging.getLogger('discord.http').setLevel(logging.WARNING)
logging.getLogger('discord.gateway').setLevel(logging.INFO)

logger = logging.getLogger('bot')

# Cargar variables de entorno
load_dotenv()
TOKEN = os.getenv("TOKEN")
TRGGKEY = os.getenv("TRGGKEY")

if not TOKEN: 
    raise ValueError("TOKEN no encontrado en el archivo .env")

logger.info("Cargado token bot")

# Configuración del bot
descripcion = "Bot todopoderoso del linaje Meriendo"
prefix = TRGGKEY if TRGGKEY else "!"
intents = discord.Intents.all()
intents.message_content = True
bot = commands.Bot(command_prefix=prefix, intents=intents, description=descripcion)

# -------------------- EVENTOS -------------------- #

@bot.event
async def on_message(message):
    if message.author == bot.user or message.author.bot:
        return
    await bot.process_commands(message)

@bot.event
async def on_ready():
    logger.info(f'We have logged in as {bot.user}')

@bot.event
async def on_member_join(member):
    await member.send(f'Bienvenido al server {member.name}, bonito nombre por cierto!')

@bot.event
async def on_voice_state_update(member, before, after):
    if member == bot.user and before.channel and not after.channel:
        # Bot desconectado, limpiar cola
        if before.channel.guild.id in music_queues:
            music_queues[before.channel.guild.id] = []

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return # Ignorar comandos inexistentes
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("Faltan argumentos para este comando.")
    elif isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"Espera un poco, comando en enfriamiento: {error.retry_after:.2f}s")
    else:
        logger.error(f"Error no controlado: {error}")
        await ctx.send("Ocurrió un error inesperado.")

@bot.event
async def on_voice_state_update(member, before, after):
    # ...existing code...
    
    # Lógica para desconexión automática si el bot se queda solo
    if before.channel is not None:
        voice_client = discord.utils.get(bot.voice_clients, guild=before.channel.guild)
        if voice_client and voice_client.channel == before.channel:
            if len(before.channel.members) == 1: # Solo queda el bot
                await asyncio.sleep(60) # Esperar 1 minuto
                if len(before.channel.members) == 1 and voice_client.is_connected():
                    await voice_client.disconnect()
                    # Limpiar cola
                    if before.channel.guild.id in music_queues:
                        music_queues[before.channel.guild.id] = []
                    logger.info(f"Desconectado de {before.channel.name} por inactividad.")

# -------------------- COMANDOS BÁSICOS -------------------- #

@bot.command(name='ping', help='pong?', category='Basico')
async def pingpong(ctx):
    await ctx.send('pong')

@bot.command(name='hola', help='Saluda al usuario', category='Basico')
async def saludar(ctx):
    await ctx.send(f'Hola {ctx.author.mention}!')

# Comando de ayuda personalizado
@bot.command(name="comandos", help="Muestra todos los comandos disponibles")
async def help_custom(ctx):
    embed = discord.Embed(title="📋 Comandos del Bot", color=discord.Color.blue())
    
    categories = {}
    for command in bot.commands:
        category = getattr(command, 'category', 'Sin categoría')
        if category not in categories:
            categories[category] = []
        categories[category].append(f"`{prefix}{command.name}` - {command.help}")
    
    for category, cmds in categories.items():
        embed.add_field(name=f"**{category}**", value="\n".join(cmds), inline=False)
    
    await ctx.send(embed=embed)


# -------------------- MÚSICA -------------------- #

# Configuración de youtube-dl y ffmpeg
ytdl_format_options = {
    'format': 'bestaudio/best',
    'noplaylist': False,
    'quiet': True,
    'no_warnings': True,
    'cookiefile': 'cookies.txt',
    'extractor_args': {
        'youtube': {
            'player_client': ['default']
        }
    }
}
ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}
ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

# Cola de reproducción por servidor (diccionario) y tam máximo
music_queues = {}
MAX_QUEUE_SIZE = 30

class MusicControls(View):
    def __init__(self, ctx):
        super().__init__(timeout=None)
        self.ctx = ctx

    @discord.ui.button(label="⏸️ Pausa", style=discord.ButtonStyle.blurple)
    async def pause_resume(self, interaction: discord.Interaction, button: Button):
        # Verificación de seguridad
        if not self.ctx.voice_client:
            await interaction.response.send_message("No estoy conectado.", ephemeral=True)
            return

        if self.ctx.voice_client.is_playing():
            self.ctx.voice_client.pause()
            # Cambiamos el aspecto del botón
            button.label = "▶️ Reanudar"
            button.style = discord.ButtonStyle.green
            # Actualizamos el mensaje con la nueva vista
            await interaction.response.edit_message(view=self)
        else:
            self.ctx.voice_client.resume()
            # Restauramos el aspecto original
            button.label = "⏸️ Pausa"
            button.style = discord.ButtonStyle.blurple
            # Actualizamos el mensaje
            await interaction.response.edit_message(view=self)

    @discord.ui.button(label="⏭️ Skip", style=discord.ButtonStyle.red)
    async def skip(self, interaction: discord.Interaction, button: Button):
        self.ctx.voice_client.stop()
        await interaction.response.send_message("Saltando canción...", ephemeral=True)


# Función para reproducir la siguiente canción en la cola
async def play_next_song(ctx):
    guild_id = ctx.guild.id

    # Verificar conexión
    if not ctx.voice_client:
        return

    # Si hay canciones en la cola
    if guild_id in music_queues and music_queues[guild_id]:
        # Extraer la siguiente canción
        url, title = music_queues[guild_id].pop(0)
        
        try:
            # Usamos from_probe (asíncrono) que es más robusto
            source = await discord.FFmpegOpusAudio.from_probe(url, **ffmpeg_options)
            
            # Definimos el callback que se ejecutará al terminar la canción
            def after_playing(error):
                if error:
                    logger.error(f"Error en reproducción: {error}")
                # Programar la siguiente canción en el bucle de eventos principal
                coro = play_next_song(ctx)
                fut = asyncio.run_coroutine_threadsafe(coro, bot.loop)
                try:
                    fut.result()
                except:
                    pass

            ctx.voice_client.play(source, after=after_playing)
            embed = discord.Embed(title="Reproduciendo ahora", description=f"[{title}]({url})", color=0x00ff00)
            view = MusicControls(ctx)
            await ctx.send(embed=embed, view=view)
            
        except Exception as e:
            logger.error(f"Error al reproducir {title}: {e}")
            await ctx.send(f"Error al reproducir **{title}**, saltando...")
            # Intentar con la siguiente si falla
            await play_next_song(ctx)
    else:
        # La cola está vacía
        await ctx.send("La cola de reproducción ha terminado.")


# Comando para que el bot se una al canal de voz del usuario
@bot.command(name="join", help="El bot se une a tu canal de voz", category="Música")
async def join(ctx):

    # Verificar si el usuario está en un canal de voz
    if not ctx.author.voice:
        await ctx.send("¡Debes estar en un canal de voz!")
        return
    
    channel = ctx.author.voice.channel
    
    # Verificar permisos
    if not channel.permissions_for(ctx.guild.me).connect:
        await ctx.send("No tengo permisos para conectarme a ese canal.")
        return

    await channel.connect()

# Comando para que el bot salga del canal de voz
@bot.command(name="leave", help="El bot sale del canal de voz", category="Música")
async def leave(ctx):

    # Salir del canal de voz si está conectado
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        if ctx.guild.id in music_queues:
            music_queues[ctx.guild.id] = []
    else:
        await ctx.send("No estoy en ningún canal de voz.")

# Comando para reproducir música desde YouTube
# ...existing code...
@bot.command(name="play", help="Reproduce música de YouTube (acepta URL o búsqueda)", category="Música")
async def play(ctx, *, query):

    # Unirse al canal de voz si el bot no esta conectado y el usuario si
    if not ctx.voice_client:
        if ctx.author.voice:
            await ctx.author.voice.channel.connect()
        else:
            await ctx.send("Debes estar en un canal de voz o usar !join.")
            return

    # Mientras se procesa la solicitud el bot muestra el estado de "escribiendo..."
    async with ctx.typing():
        try:
            guild_id = ctx.guild.id
            if guild_id not in music_queues:
                music_queues[guild_id] = []

            # Si el usuario proporciona el enlace directo
            if query.startswith("http"):
                # extract_flat=False descarga la info completa de cada video (puede tardar en playlists largas)
                info = await asyncio.to_thread(ytdl.extract_info, query, download=False)
                
                # Detectar si es una playlist
                if 'entries' in info:
                    # Es una playlist
                    entries = info['entries']
                    added_count = 0
                    
                    for entry in entries:
                        # A veces hay entradas vacías en playlists (videos borrados)
                        if entry:
                            music_queues[guild_id].append((entry['url'], entry['title']))
                            added_count += 1
                            
                    await ctx.send(f"✅ Playlist añadida: **{info.get('title', 'Lista')}** ({added_count} canciones).")
                    
                    # Si no está sonando nada, iniciar la primera de la lista
                    if not ctx.voice_client.is_playing() and not ctx.voice_client.is_paused():
                        await play_next_song(ctx)
                    return # Salimos aquí porque ya manejamos la respuesta

                else:
                    # Es un video único por URL
                    audio_url = info['url']
                    title = info['title']
                    music_queues[guild_id].append((audio_url, title))
                    await ctx.send(f"➕ Añadido a la cola: **{title}**")

            # Si no es URL, buscar en YouTube (Mantenemos lógica de búsqueda simple)
            else:
                result = await asyncio.to_thread(ytdl.extract_info, f"ytsearch:{query}", download=False)
                info = result['entries'][0]
                audio_url = info['url']
                title = info['title']
                music_queues[guild_id].append((audio_url, title))
                await ctx.send(f"➕ Añadido a la cola: **{title}**")
        
            # Verificar límite de cola (Opcional: mover esto antes de añadir si quieres ser estricto)
            if len(music_queues[guild_id]) >= MAX_QUEUE_SIZE:
                await ctx.send(f"⚠️ La cola está llena, algunas canciones podrían no haberse añadido.")

            # Si NO está reproduciendo nada, iniciar la cadena (para video único o búsqueda)
            if not ctx.voice_client.is_playing() and not ctx.voice_client.is_paused():
                await play_next_song(ctx)
        
        except Exception as e:
            await ctx.send("Ocurrió un error al procesar la solicitud.")
            logger.error(f"Error al buscar música: {e}")
            return
        
# Comando para detener la música y limpiar la cola
@bot.command(name="stop", help="Detiene la música y limpia la cola", category="Música")
async def stop(ctx):
    
    # Si hay música reproduciéndose o en cola, la detiene y limpia la cola
    if ctx.voice_client:
        ctx.voice_client.stop()
        if ctx.guild.id in music_queues:
            music_queues[ctx.guild.id] = []
        await ctx.send("⏹️ Música detenida y cola vacía.")
    else:
        await ctx.send("No hay nada reproduciéndose.")

# Comando para pausar la música
@bot.command(name="pause", help="Pausa la música", category="Música")
async def pause(ctx):
    
    # Si hay música reproduciéndose, la pausa
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.pause()
        await ctx.send("⏸️ Música pausada.")
    else:
        await ctx.send("No hay música reproduciéndose.")

# Comando para reanudar la música
@bot.command(name="resume", help="Reanuda la música", category="Música")
async def resume(ctx):
    
    # Si la música está pausada, la reanuda
    if ctx.voice_client and ctx.voice_client.is_paused():
        ctx.voice_client.resume()
        await ctx.send("▶️ Música reanudada.")
    else:
        await ctx.send("La música no está pausada.")

# Comando para saltar la canción actual
@bot.command(name="skip", help="Salta la canción actual", category="Música")
async def skip(ctx):
    # Verificar si hay algo reproduciéndose o pausado
    if ctx.voice_client and (ctx.voice_client.is_playing() or ctx.voice_client.is_paused()):
        ctx.voice_client.stop() 
        await ctx.send("⏭️ Canción saltada.")
    else:
        await ctx.send("No hay música reproduciéndose para saltar.")

# Comando para mostrar la cola de reproducción
@bot.command(name="queue", help="Muestra la cola de reproducción", category="Música")
async def queue(ctx):

    # Obitener la cola del servidor
    guild_id = ctx.guild.id

    # Si la cola existe y tiene canciones, las muestra
    if guild_id in music_queues and music_queues[guild_id]:
        cola = "\n".join([f"{i+1}. {title}" for i, (_, title) in enumerate(music_queues[guild_id])])
        await ctx.send(f"📜 Cola de reproducción:\n{cola}")
    else:
        await ctx.send("La cola está vacía.")


# -------------------- EJECUCIÓN -------------------- #

bot.run(TOKEN)
