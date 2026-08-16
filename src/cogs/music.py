
import asyncio
import os
import tempfile
from pathlib import Path

import discord
from discord.ext import commands
from discord.ui import Button, View

from src.utils.logger import logger
from src.utils.music_service import music_service
from src.utils.state import music_queues

# Las opciones '-reconnect' solo son válidas para streams de red.
# Como aquí reproducimos archivos locales descargados, no deben usarse.
ffmpeg_options = {
    'options': '-vn'
}

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
        self._cleanup_started = False

    async def _resolve_track(self, video_url: str, title: str | None = None):
        """Resuelve una entrada de cola a un archivo de audio local estable."""
        try:
            return await music_service.download_audio(video_url, title=title)
        except Exception as exc:
            logger.warning(f"Fallo descargando {title or video_url}: {exc}")
            raise

    async def _schedule_cleanup(self):
        if not self._cleanup_started:
            self._cleanup_started = True
            music_service.prune_cache_if_needed()

    async def play_next_song(self, ctx):
        guild_id = ctx.guild.id

        if not ctx.voice_client:
            return

        if guild_id in music_queues and music_queues[guild_id]:
            while music_queues[guild_id]:
                video_url, title = music_queues[guild_id].pop(0)

                try:
                    local_audio_path = await self._resolve_track(video_url, title)
                    source = discord.FFmpegOpusAudio(local_audio_path, **ffmpeg_options)

                    def after_playing(error):
                        if error:
                            logger.error(f"Error en reproducción: {error}")
                        coro = self.play_next_song(ctx)
                        fut = asyncio.run_coroutine_threadsafe(coro, self.bot.loop)
                        try:
                            fut.result()
                        except Exception:
                            pass

                    ctx.voice_client.play(source, after=after_playing)
                    embed = discord.Embed(title="Reproduciendo ahora", description=f"[{title}]({video_url})", color=0x00ff00)
                    view = MusicControls(ctx)
                    await ctx.send(embed=embed, view=view)
                    return

                except Exception as e:
                    logger.warning(f"Canción descartada por fallo de reproducción: {title} - {e}")
                    continue

            await ctx.send("La cola de reproducción ha terminado.")
            return

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
        await self._schedule_cleanup()

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

                if query.startswith("http"):
                    info = await music_service.extract_info(query, download=False)

                    if 'entries' in info and info.get('entries'):
                        entries = [entry for entry in info['entries'] if entry]
                        added_count = 0

                        for entry in entries:
                            video_url = entry.get('webpage_url') or entry.get('url')
                            video_title = entry.get('title', 'Video desconocido')

                            if video_url and len(video_url) == 11 and ' ' not in video_url and '.' not in video_url:
                                video_url = f"https://www.youtube.com/watch?v={video_url}"

                            if video_url:
                                music_queues[guild_id].append((video_url, video_title))
                                added_count += 1

                        await ctx.send(f"✅ Playlist añadida: **{info.get('title', 'Lista')}** ({added_count} canciones).")
                        if not ctx.voice_client.is_playing() and not ctx.voice_client.is_paused():
                            await self.play_next_song(ctx)
                        return

                    video_url = info.get('webpage_url') or info.get('url')
                    title = info.get('title')
                    if video_url and len(video_url) == 11 and ' ' not in video_url and '.' not in video_url:
                        video_url = f"https://www.youtube.com/watch?v={video_url}"

                    if video_url and title:
                        music_queues[guild_id].append((video_url, title))
                        await ctx.send(f"➕ Añadido a la cola: **{title}**")
                else:
                    result = await music_service.extract_info(f"ytsearch:{query}", download=False)
                    if result and 'entries' in result and result['entries'] and result['entries'][0]:
                        info = result['entries'][0]
                        video_url = info.get('webpage_url') or info.get('url')
                        title = info.get('title')

                        if video_url and title:
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
