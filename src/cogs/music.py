
import discord
from discord.ext import commands
from discord.ui import Button, View
import yt_dlp as youtube_dl
import asyncio
from src.utils.logger import logger
from src.utils.state import music_queues

# Configuración de youtube-dl y ffmpeg
ytdl_format_options = {
    'format': 'bestaudio/best',
    'noplaylist': False,
    'quiet': True,
    'no_warnings': True,
    'ignoreerrors': True,
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

MAX_QUEUE_SIZE = 30

class MusicControls(View):
    def __init__(self, ctx):
        super().__init__(timeout=None)
        self.ctx = ctx

    @discord.ui.button(label="⏸️ Pausa", style=discord.ButtonStyle.blurple)
    async def pause_resume(self, interaction: discord.Interaction, button: Button):
        if not self.ctx.voice_client:
            await interaction.response.send_message("No estoy conectado.", ephemeral=True)
            return

        if self.ctx.voice_client.is_playing():
            self.ctx.voice_client.pause()
            button.label = "▶️ Reanudar"
            button.style = discord.ButtonStyle.green
            await interaction.response.edit_message(view=self)
        else:
            self.ctx.voice_client.resume()
            button.label = "⏸️ Pausa"
            button.style = discord.ButtonStyle.blurple
            await interaction.response.edit_message(view=self)

    @discord.ui.button(label="⏭️ Skip", style=discord.ButtonStyle.red)
    async def skip(self, interaction: discord.Interaction, button: Button):
        if self.ctx.voice_client:
            self.ctx.voice_client.stop()
            await interaction.response.send_message("Saltando canción...", ephemeral=True)
        else:
            await interaction.response.send_message("No estoy conectado.", ephemeral=True)


class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def play_next_song(self, ctx):
        guild_id = ctx.guild.id

        if not ctx.voice_client:
            return

        if guild_id in music_queues and music_queues[guild_id]:
            # Ahora la cola contiene (video_url, title) pero el video_url aun no es el stream de audio
            video_url, title = music_queues[guild_id].pop(0)
            
            try:
                # RESOLUCION JIT: Extraemos el stream de audio aqui, justo antes de reproducir
                # Usamos asyncio.to_thread para no bloquear el loop mientras yt-dlp procesa
                info = await asyncio.to_thread(ytdl.extract_info, video_url, download=False)
                audio_source_url = info['url'] # Esta es la URL real del stream de audio

                source = await discord.FFmpegOpusAudio.from_probe(audio_source_url, **ffmpeg_options)
                
                def after_playing(error):
                    if error:
                        logger.error(f"Error en reproducción: {error}")
                    coro = self.play_next_song(ctx)
                    fut = asyncio.run_coroutine_threadsafe(coro, self.bot.loop)
                    try:
                        fut.result()
                    except:
                        pass

                ctx.voice_client.play(source, after=after_playing)
                embed = discord.Embed(title="Reproduciendo ahora", description=f"[{title}]({video_url})", color=0x00ff00)
                view = MusicControls(ctx)
                await ctx.send(embed=embed, view=view)
                
            except Exception as e:
                logger.error(f"Error al reproducir {title}: {e}")
                await ctx.send(f"Error al reproducir o procesar **{title}** ({e}), saltando a la siguiente...")
                await self.play_next_song(ctx)
        else:
            await ctx.send("La cola de reproducción ha terminado.")

    @commands.command(name="join", help="El bot se une a tu canal de voz", category="Música")
    async def join(self, ctx):
        if not ctx.author.voice:
            await ctx.send("¡Debes estar en un canal de voz!")
            return
        
        channel = ctx.author.voice.channel
        if not channel.permissions_for(ctx.guild.me).connect:
            await ctx.send("No tengo permisos para conectarme a ese canal.")
            return

        await channel.connect()

    @commands.command(name="leave", help="El bot sale del canal de voz", category="Música")
    async def leave(self, ctx):
        if ctx.voice_client:
            await ctx.voice_client.disconnect()
            if ctx.guild.id in music_queues:
                music_queues[ctx.guild.id] = []
        else:
            await ctx.send("No estoy en ningún canal de voz.")

    @commands.command(name="play", help="Reproduce música de YouTube (acepta URL o búsqueda)", category="Música")
    async def play(self, ctx, *, query):
        if not ctx.voice_client:
            if ctx.author.voice:
                await ctx.author.voice.channel.connect()
            else:
                await ctx.send("Debes estar en un canal de voz o usar !join.")
                return

        async with ctx.typing():
            try:
                guild_id = ctx.guild.id
                if guild_id not in music_queues:
                    music_queues[guild_id] = []

                if "spotify.com" in query:
                    await ctx.send("🔍 Analizando playlist de Spotify, esto puede tardar un poco...")
                    # Usamos yt-dlp para extraer solo los títulos de las canciones de la lista de Spotify
                    with youtube_dl.YoutubeDL({'extract_flat': True, 'quiet': True}) as ydl:
                        info = await asyncio.to_thread(ydl.extract_info, query, download=False)
                    
                    entries = list(info.get('entries', []))
                    added_count = 0
                    for entry in entries:
                        title = entry.get('title')
                        if title:
                            # Buscamos en YouTube el título de la canción de Spotify
                            search_result = await asyncio.to_thread(ytdl.extract_info, f"ytsearch:{title}", download=False)
                            tracks = search_result.get('entries', [])
                            if tracks:
                                track_info = tracks[0]
                                video_url = track_info.get('webpage_url')
                                video_title = track_info.get('title')
                                music_queues[guild_id].append((video_url, video_title))
                                added_count += 1
                    
                    await ctx.send(f"✅ Añadidas {added_count} canciones de Spotify a la cola.")
                    
                elif query.startswith("http"):
                    # OPTIMIZACION: Usamos extract_flat=True para obtener solo metadatos rapido
                    # 'extract_flat': 'in_playlist' asegura que si es playlist no descargue info de cada video, solo la lista
                    # Si es un video solo, igual extrae la info basica rapido.
                    opts = {'extract_flat': 'in_playlist'} 
                    # Hacemos una copia de las opciones globales y añadimos la especifica
                    temp_opts = ytdl_format_options.copy()
                    temp_opts.update(opts)
                    
                    with youtube_dl.YoutubeDL(temp_opts) as ydl_fast:
                         info = await asyncio.to_thread(ydl_fast.extract_info, query, download=False)
                    
                    if 'entries' in info:
                        entries = list(info['entries']) # Puede ser un generador
                        added_count = 0
                        
                        # Añadimos las URL a la cola. 
                        # Nota: En extract_flat, 'url' suele ser el ID o la URL completa dependiendo del extractor.
                        # Para youtube es usualmente el ID o URL relativa. Tratemos de asegurar URL completa si es YouTube.
                        
                        for entry in entries:
                            if entry:
                                # Construir URL completa si es necesario (para youtube)
                                video_url = entry.get('url')
                                video_title = entry.get('title', 'Video desconocido')
                                
                                # Si la URL es solo un ID (comun en extract_flat de youtube), construimos el link
                                if video_url and len(video_url) == 11 and ' ' not in video_url and '.' not in video_url:
                                     video_url = f"https://www.youtube.com/watch?v={video_url}"
                                
                                music_queues[guild_id].append((video_url, video_title))
                                added_count += 1

                        await ctx.send(f"✅ Playlist añadida: **{info.get('title', 'Lista')}** ({added_count} canciones).")
                        
                        # Iniciar reproduccion inmediatamente si no esta tocando
                        if not ctx.voice_client.is_playing() and not ctx.voice_client.is_paused():
                            await self.play_next_song(ctx)
                        return
                    else:
                        # Caso video unico (extract_flat podria devolverlo como info directa)
                        video_url = info.get('url') # web url
                        title = info.get('title')
                        # Mismo check de ID
                        if video_url and len(video_url) == 11 and ' ' not in video_url and '.' not in video_url:
                                     video_url = f"https://www.youtube.com/watch?v={video_url}"

                        music_queues[guild_id].append((video_url, title))
                        await ctx.send(f"➕ Añadido a la cola: **{title}**")
                else:
                    # Busqueda (ytsearch)
                    # Para busqueda no usaremos extract_flat pq queremos el primer resultado ya bien parseado
                    # O podemos usarlo pero es mas simple dejarlo como estaba para busquedas (suelen ser de 1)
                    result = await asyncio.to_thread(ytdl.extract_info, f"ytsearch:{query}", download=False)
                    if 'entries' in result and len(result['entries']) > 0:
                        info = result['entries'][0]
                        # Aqui info['url'] deberia ser la web url normalmente en ytsearch sin get_url=True?
                        # ytdl por defecto devuelve resolucion completa. 
                        # PERO para mantener consistencia con play_next_song que AHORA espera una web_url para hacer resolve...
                        # Necesitamos guardar la WEB URL (watch?v=...), NO la audio stream url.
                        # ytsearch devuelve la info completa, 'webpage_url' es lo que buscamos.
                        video_url = info.get('webpage_url')
                        title = info.get('title')
                        
                        music_queues[guild_id].append((video_url, title))
                        await ctx.send(f"➕ Añadido a la cola: **{title}**")
                    else:
                        await ctx.send("No se encontraron resultados.")
            
                if len(music_queues[guild_id]) >= MAX_QUEUE_SIZE:
                    await ctx.send(f"⚠️ La cola está llena, algunas canciones podrían no haberse añadido.")

                if not ctx.voice_client.is_playing() and not ctx.voice_client.is_paused():
                    await self.play_next_song(ctx)
            
            except Exception as e:
                await ctx.send("Ocurrió un error al procesar la solicitud.")
                logger.error(f"Error al buscar música: {e}")

    @commands.command(name="stop", help="Detiene la música y limpia la cola", category="Música")
    async def stop(self, ctx):
        if ctx.voice_client:
            ctx.voice_client.stop()
            if ctx.guild.id in music_queues:
                music_queues[ctx.guild.id] = []
            await ctx.send("⏹️ Música detenida y cola vacía.")
        else:
            await ctx.send("No hay nada reproduciéndose.")

    @commands.command(name="pause", help="Pausa la música", category="Música")
    async def pause(self, ctx):
        if ctx.voice_client and ctx.voice_client.is_playing():
            ctx.voice_client.pause()
            await ctx.send("⏸️ Música pausada.")
        else:
            await ctx.send("No hay música reproduciéndose.")

    @commands.command(name="resume", help="Reanuda la música", category="Música")
    async def resume(self, ctx):
        if ctx.voice_client and ctx.voice_client.is_paused():
            ctx.voice_client.resume()
            await ctx.send("▶️ Música reanudada.")
        else:
            await ctx.send("La música no está pausada.")

    @commands.command(name="skip", help="Salta la canción actual", category="Música")
    async def skip(self, ctx):
        if ctx.voice_client and (ctx.voice_client.is_playing() or ctx.voice_client.is_paused()):
            ctx.voice_client.stop() 
            await ctx.send("⏭️ Canción saltada.")
        else:
            await ctx.send("No hay música reproduciéndose para saltar.")

    @commands.command(name="queue", help="Muestra la cola de reproducción", category="Música")
    async def queue(self, ctx):
        guild_id = ctx.guild.id
        if guild_id in music_queues and music_queues[guild_id]:
            cola = "\n".join([f"{i+1}. {title}" for i, (_, title) in enumerate(music_queues[guild_id])])
            await ctx.send(f"📜 Cola de reproducción:\n{cola}")
        else:
            await ctx.send("La cola está vacía.")

async def setup(bot):
    await bot.add_cog(Music(bot))
