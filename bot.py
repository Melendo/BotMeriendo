import discord
from discord.ext import commands
import requests
from dotenv import load_dotenv
import os
from bs4 import BeautifulSoup

load_dotenv("/home/melendo/botMeriendo/.env")
TOKEN = os.getenv("TOKEN")
TRGGKEY = os.getenv("TRGGKEY")
print("Cargado token bot")

#Configuracion del cliente "bot"
descripcion = "Bot todopoderoso hijo de Melendo y hermano de Meriendo"
prefix = "!"
intents = discord.Intents.all()
intents.message_content = True
bot = commands.Bot(command_prefix=prefix, intents=intents, description = descripcion)

#<<<<<<<<<<<<<<<<<<<<<<<<<<EVENTOS>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

#Analizamos mensaje y se procesan los comandos
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    
    if message.author.bot:
        return

    await bot.process_commands(message)

#Mensaje login del bot por terminal
@bot.event
async def on_ready():
    print('We have logged in as {0}'.format(bot.user))

#Mensaje privado al unirse
@bot.event
async def on_member_join(member):
    await member.send(f'Bienvenido al server {member.name}, bonito nombre por cierto!')

#Mensaje en el server de quien se ha ido
@bot.event
async def on_member_remove(member):
    await bot.get_channel(762326170799702016).send(f'{member.name} se ha ido a mi mi mi zzz... zzz... zzz...')

#<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<COMANDOS>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    
#Comando ping
@bot.command(name='ping' , help='pong?', category='Basico')
async def pingpong(ctx):
    await ctx.send('pong')

#Comando de saludar al usuario
@bot.command(name='hola', help='Saluda al usuario', category='Basico')
async def saludar(ctx):
    await ctx.send(f'Hola {ctx.author.mention}!')

#Comando busqueda en google
@bot.command(name='buscar', help='Busca en google y te devuelve la primera búsqueda', category='Utilidad')
async def buscar(ctx, *, query):
    url = f"https://www.google.com/search?q={query}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.1 Safari/537.36"
    }

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        first_result = soup.find('div', class_='tF2Cxc')
        
        if first_result:
            title = first_result.find('h3').text
            link = first_result.find('a')['href']
            
            await ctx.send(f"Título del primer resultado: {title}\nEnlace del primer resultado: {link}")
        else:
            await ctx.send("No se encontraron resultados.")
    else:
        await ctx.send("Error al realizar la búsqueda.")

#Comando devuelve stats de Rocket League
@bot.command(name='rangoRL', help='introduciendo id epic devuelve el rango en 2s', category='Utilidad')

async def rangoRL(ctx, *, query):
    url = f"https://public-api.tracker.gg/v2/rocket-league/standard/profile/epic/{query}/sessions?"
    headers = {
        "TRN-Api-Key": TRGGKEY
    }

    response = requests.get(url, headers=headers)

    print(response.status_code)
    if response.status_code == 200: 
        datos = response.json()
        print(datos)
        await ctx.send(f"El rango del jugador {query} es : \nEnlace del tracker: {url}")
    else:
        await ctx.send("Error al realizar la búsqueda.")



bot.run(TOKEN)