import discord
from discord.ext import commands
import requests
from dotenv import load_dotenv
import os
from bs4 import BeautifulSoup
import yt_dlp as youtube_dl

# Cargar variables de entorno
load_dotenv("/home/melendo/botMeriendo/.env")
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
        audio_url = info['url']
        source = await discord.FFmpegOpusAudio.from_probe(audio_url, **ffmpeg_options)
        ctx.voice_client.stop()
        ctx.voice_client.play(source, after=lambda e: print(f"Error: {e}" if e else "Reproducción terminada"))

    await ctx.send(f"▶️ Reproduciendo: **{info['title']}**")

@bot.command(name="stop", help="Detiene la música", category="Música")
async def stop(ctx):
    if ctx.voice_client:
        ctx.voice_client.stop()
        await ctx.send("⏹️ Música detenida.")
    else:
        await ctx.send("No hay nada reproduciéndose.")

# -------------------- EJECUCIÓN -------------------- #

bot.run(TOKEN)
