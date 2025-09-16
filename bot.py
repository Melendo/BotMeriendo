import discord
from discord.ext import commands
import requests
from dotenv import load_dotenv
import os
from bs4 import BeautifulSoup
import yt_dlp as youtube_dl

# Cargar variables de entorno
load_dotenv()
TOKEN = os.getenv("TOKEN")
TRGGKEY = os.getenv("TRGGKEY")
print("Cargado token bot")

# Configuración del bot
descripcion = "Bot todopoderoso hijo de Melendo y hermano de Meriendo"
prefix = "!"
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
    print(f'We have logged in as {bot.user}')

@bot.event
async def on_member_join(member):
    await member.send(f'Bienvenido al server {member.name}, bonito nombre por cierto!')

@bot.event
async def on_member_remove(member):
    await bot.get_channel(762326170799702016).send(f'{member.name} se ha ido a mi mi mi zzz... zzz... zzz...')

# -------------------- COMANDOS BÁSICOS -------------------- #

@bot.command(name='ping', help='pong?', category='Basico')
async def pingpong(ctx):
    await ctx.send('pong')

@bot.command(name='hola', help='Saluda al usuario', category='Basico')
async def saludar(ctx):
    await ctx.send(f'Hola {ctx.author.mention}!')

# -------------------- GOOGLE SEARCH -------------------- #

@bot.command(name='buscar', help='Busca en google y devuelve el primer resultado', category='Utilidad')
async def buscar(ctx, *, query):
    url = f"https://www.google.com/search?q={query}"
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        first_result = soup.find('div', class_='tF2Cxc')
        if first_result:
            title = first_result.find('h3').text
            link = first_result.find('a')['href']
            await ctx.send(f"Título: {title}\nEnlace: {link}")
        else:
            await ctx.send("No se encontraron resultados.")
    else:
        await ctx.send("Error al realizar la búsqueda.")

# -------------------- ROCKET LEAGUE -------------------- #

@bot.command(name='rangoRL', help='Devuelve rango en 2s', category='Utilidad')
async def rangoRL(ctx, *, query):
    url = f"https://public-api.tracker.gg/v2/rocket-league/standard/profile/epic/{query}/sessions?"
    headers = {"TRN-Api-Key": TRGGKEY}
    response = requests.get(url, headers=headers)
    if response.status_code == 200: 
        datos = response.json()
        await ctx.send(f"El rango del jugador {query} es:\nEnlace del tracker: {url}")
    else:
        await ctx.send("Error al realizar la búsqueda.")

# -------------------- MÚSICA -------------------- #

ytdl_format_options = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True
}
ffmpeg_options = {'options': '-vn'}
ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

# Cola de reproducción por servidor
music_queues = {}

def play_next(ctx):
    guild_id = ctx.guild.id
    if music_queues[guild_id]:
        url, title = music_queues[guild_id].pop(0)
        source = discord.FFmpegOpusAudio(url, **ffmpeg_options)
        ctx.voice_client.play(
            source,
            after=lambda e: play_next(ctx)
        )
        coro = ctx.send(f"▶️ Reproduciendo: **{title}**")
        # necesitamos pasar de callback sync a async
        fut = discord.utils.run_coroutine_threadsafe(coro, ctx.bot.loop)
        try:
            fut.result()
        except:
            pass

@bot.command(name="join", help="El bot se une a tu canal de voz", category="Música")
async def join(ctx):
    if ctx.author.voice:
        channel = ctx.author.voice.channel
        await channel.connect()
    else:
        await ctx.send("¡Debes estar en un canal de voz!")

@bot.command(name="leave", help="El bot sale del canal de voz", category="Música")
async def leave(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        music_queues[ctx.guild.id] = []  # limpiar cola
    else:
        await ctx.send("No estoy en ningún canal de voz.")

@bot.command(name="play", help="Reproduce música de YouTube", category="Música")
async def play(ctx, *, url):
    if not ctx.voice_client:
        if ctx.author.voice:
            await ctx.author.voice.channel.connect()
        else:
            await ctx.send("Debes estar en un canal de voz o usar !join.")
            return

    async with ctx.typing():
        info = ytdl.extract_info(url, download=False)
        if "entries" in info:  # si fuese playlist
            info = info["entries"][0]

        audio_url = info['url']
        title = info['title']

        guild_id = ctx.guild.id
        if guild_id not in music_queues:
            music_queues[guild_id] = []

        if ctx.voice_client.is_playing() or ctx.voice_client.is_paused():
            music_queues[guild_id].append((audio_url, title))
            await ctx.send(f"➕ Añadido a la cola: **{title}**")
        else:
            source = await discord.FFmpegOpusAudio.from_probe(audio_url, **ffmpeg_options)
            ctx.voice_client.play(
                source,
                after=lambda e: play_next(ctx)
            )
            await ctx.send(f"▶️ Reproduciendo: **{title}**")

@bot.command(name="skip", help="Salta a la siguiente canción", category="Música")
async def skip(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send("⏭️ Canción saltada.")
    else:
        await ctx.send("No hay música sonando.")

@bot.command(name="stop", help="Detiene la música y limpia la cola", category="Música")
async def stop(ctx):
    if ctx.voice_client:
        ctx.voice_client.stop()
        music_queues[ctx.guild.id] = []
        await ctx.send("⏹️ Música detenida y cola vacía.")
    else:
        await ctx.send("No hay nada reproduciéndose.")

@bot.command(name="pause", help="Pausa la música", category="Música")
async def pause(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.pause()
        await ctx.send("⏸️ Música pausada.")
    else:
        await ctx.send("No hay música reproduciéndose.")

@bot.command(name="resume", help="Reanuda la música", category="Música")
async def resume(ctx):
    if ctx.voice_client and ctx.voice_client.is_paused():
        ctx.voice_client.resume()
        await ctx.send("▶️ Música reanudada.")
    else:
        await ctx.send("La música no está pausada.")

@bot.command(name="queue", help="Muestra la cola de reproducción", category="Música")
async def queue(ctx):
    guild_id = ctx.guild.id
    if guild_id in music_queues and music_queues[guild_id]:
        cola = "\n".join([f"{i+1}. {title}" for i, (_, title) in enumerate(music_queues[guild_id])])
        await ctx.send(f"📜 Cola de reproducción:\n{cola}")
    else:
        await ctx.send("La cola está vacía.")


# -------------------- EJECUCIÓN -------------------- #

bot.run(TOKEN)
