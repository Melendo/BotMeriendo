import asyncio
import random
import time

import discord
from discord.ext import commands
from discord.ui import Button, View

from src.config import SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, SPOTIFY_REFRESH_TOKEN
from src.utils.logger import logger
from src.utils.music_service import music_service
from src.utils.queue_utils import pistas_de_info, trocear
from src.utils.spotify import SpotifyClient, SpotifyError, busqueda_youtube, es_spotify, parse_spotify_url
from src.utils.state import loop_enabled, music_queues, now_playing, reset_guild, skip_once

spotify = SpotifyClient(SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, SPOTIFY_REFRESH_TOKEN)

# Las opciones '-reconnect' solo son válidas para streams de red.
# Como aquí reproducimos archivos locales descargados, no deben usarse.
ffmpeg_options = {
    'options': '-vn'
}

MAX_QUEUE_SIZE = 30
CLEANUP_EVERY_SECS = 3600  # limpiar la caché de audio como mucho cada hora


def saltar(voice_client, guild_id):
    """Corta la canción actual; si hay bucle, esa vez no se repite."""
    skip_once.add(guild_id)
    voice_client.stop()


class MusicControls(View):
    def __init__(self, ctx):
        super().__init__(timeout=None)
        self.ctx = ctx

    @discord.ui.button(label="⏸️ Pausa", style=discord.ButtonStyle.blurple)
    async def pause_resume(self, interaction: discord.Interaction, button: Button):
        if not self.ctx.voice_client:
            await interaction.response.send_message("No estoy conectado.", ephemeral=True)
            return

        vc = self.ctx.voice_client
        if vc.is_playing():
            vc.pause()
            button.label = "▶️ Reanudar"
            button.style = discord.ButtonStyle.green
        elif vc.is_paused():
            vc.resume()
            button.label = "⏸️ Pausa"
            button.style = discord.ButtonStyle.blurple
        else:
            await interaction.response.send_message("No hay nada sonando.", ephemeral=True)
            return
        await interaction.response.edit_message(view=self)

    @discord.ui.button(label="⏭️ Skip", style=discord.ButtonStyle.red)
    async def skip(self, interaction: discord.Interaction, button: Button):
        if self.ctx.voice_client:
            saltar(self.ctx.voice_client, self.ctx.guild.id)
            await interaction.response.send_message("Saltando canción...", ephemeral=True)
        else:
            await interaction.response.send_message("No estoy conectado.", ephemeral=True)


class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._last_cleanup = 0.0
        # guild_id -> (url, tarea que descarga esa canción por adelantado)
        self._prefetch: dict[int, tuple[str, asyncio.Task]] = {}

    async def _resolve_track(self, video_url: str, title: str | None = None) -> tuple[str, str]:
        """Entrada de la cola -> (enlace real del vídeo, archivo de audio local).

        Las canciones de Spotify entran en la cola como búsqueda ("ytsearch1:...")
        y se convierten aquí en un vídeo concreto, justo antes de bajarlo.
        """
        try:
            if video_url.startswith("ytsearch"):
                pistas = pistas_de_info(await music_service.extract_info(video_url))
                if not pistas:
                    raise LookupError(f"Sin resultados en YouTube para: {title}")
                video_url = pistas[0][0]
            return video_url, await music_service.download_audio(video_url, title=title)
        except Exception as exc:
            logger.warning(f"Fallo descargando {title or video_url}: {exc}")
            raise

    async def _get_track(self, guild_id: int, video_url: str, title: str | None) -> tuple[str, str]:
        """Usa la descarga adelantada si es esta canción; si no, descarga ahora."""
        pre = self._prefetch.pop(guild_id, None)
        if pre:
            url, task = pre
            if url == video_url:
                try:
                    return await task
                except Exception:
                    pass  # falló la previa: se reintenta abajo
            else:
                task.cancel()
        return await self._resolve_track(video_url, title)

    def _start_prefetch(self, guild_id: int):
        """Empieza a bajar la siguiente canción de la cola mientras suena la actual."""
        queue = music_queues.get(guild_id)
        if not queue:
            return
        url, title = queue[0]
        actual = self._prefetch.get(guild_id)
        if actual and actual[0] == url:
            return
        self.cancel_prefetch(guild_id)

        async def _bajar():
            return await self._resolve_track(url, title)

        task = asyncio.create_task(_bajar())
        # Evita el aviso "Task exception was never retrieved" si nadie la espera
        task.add_done_callback(lambda t: t.cancelled() or t.exception())
        self._prefetch[guild_id] = (url, task)

    def cancel_prefetch(self, guild_id: int):
        pre = self._prefetch.pop(guild_id, None)
        if pre:
            pre[1].cancel()

    def _reset(self, guild_id: int):
        self.cancel_prefetch(guild_id)
        reset_guild(guild_id)

    async def _schedule_cleanup(self):
        # Limpia la caché de música como mucho una vez por hora
        ahora = time.monotonic()
        if not self._last_cleanup or ahora - self._last_cleanup > CLEANUP_EVERY_SECS:
            self._last_cleanup = ahora
            await asyncio.to_thread(music_service.prune_cache_if_needed)

    async def play_next_song(self, ctx):
        guild_id = ctx.guild.id

        if not ctx.voice_client:
            return

        # Se escribe en el canal (no ctx.send): con comandos de barra la
        # interacción caduca a los 15 minutos y la cola puede durar más.
        canal = ctx.channel

        # Bucle: vuelve a poner la canción que acaba de sonar, salvo si se saltó
        saltada = guild_id in skip_once
        skip_once.discard(guild_id)
        actual = now_playing.get(guild_id)
        if actual and guild_id in loop_enabled and not saltada:
            music_queues.setdefault(guild_id, []).insert(0, actual)
        now_playing.pop(guild_id, None)

        while music_queues.get(guild_id):
            video_url, title = music_queues[guild_id].pop(0)

            try:
                video_url, local_audio_path = await self._get_track(guild_id, video_url, title)
                if not ctx.voice_client:
                    return  # se desconectó mientras descargaba
                source = discord.FFmpegOpusAudio(local_audio_path, **ffmpeg_options)

                def after_playing(error):
                    if error:
                        logger.error(f"Error en reproducción: {error}")
                    # No esperar aquí: este callback corre en el hilo de audio
                    asyncio.run_coroutine_threadsafe(self.play_next_song(ctx), self.bot.loop)

                now_playing[guild_id] = (video_url, title)
                ctx.voice_client.play(source, after=after_playing)
                embed = discord.Embed(title="Reproduciendo ahora", description=f"[{title}]({video_url})", color=0x00ff00)
                if guild_id in loop_enabled:
                    embed.set_footer(text="🔁 Bucle activado")
                view = MusicControls(ctx)
                await canal.send(embed=embed, view=view)
                if guild_id not in loop_enabled:
                    self._start_prefetch(guild_id)
                return

            except Exception as e:
                now_playing.pop(guild_id, None)
                logger.warning(f"Canción descartada por fallo de reproducción: {title} - {e}")
                continue

        await canal.send("La cola de reproducción ha terminado.")

    @commands.hybrid_command(name="join", help="El bot se une a tu canal de voz", extras={"category": "Música"})
    async def join(self, ctx):
        if not ctx.author.voice:
            await ctx.send("¡Debes estar en un canal de voz!")
            return

        channel = ctx.author.voice.channel
        if not channel.permissions_for(ctx.guild.me).connect:
            await ctx.send("No tengo permisos para conectarme a ese canal.")
            return

        if ctx.voice_client:
            await ctx.voice_client.move_to(channel)
        else:
            await channel.connect()
        await ctx.send(f"🔊 Conectado a **{channel.name}**.")

    @commands.hybrid_command(name="leave", help="El bot sale del canal de voz", extras={"category": "Música"})
    async def leave(self, ctx):
        if ctx.voice_client:
            self._reset(ctx.guild.id)
            await ctx.voice_client.disconnect()
            await ctx.send("👋 Desconectado.")
        else:
            await ctx.send("No estoy en ningún canal de voz.")

    async def _play_spotify(self, ctx, enlace: str):
        """Encola las canciones de un enlace de Spotify como búsquedas de YouTube."""
        guild_id = ctx.guild.id
        tipo, sid = parse_spotify_url(enlace)
        hueco = MAX_QUEUE_SIZE - len(music_queues[guild_id])
        try:
            # Se pide una de más para saber si la cola se queda corta
            nombre, canciones = await spotify.canciones(tipo, sid, hueco + 1)
        except SpotifyError as e:
            await ctx.send(f"❌ {e}")
            return

        pistas = [p for p in (busqueda_youtube(c) for c in canciones) if p]
        if not pistas:
            await ctx.send("No encontré canciones en ese enlace de Spotify.")
            return

        añadidas = pistas[:hueco]
        music_queues[guild_id].extend(añadidas)

        if tipo == "track":
            await ctx.send(f"➕ Añadido a la cola: **{añadidas[0][1]}** (de Spotify)")
        else:
            await ctx.send(f"✅ Añadidas de Spotify: **{nombre or 'Lista'}** ({len(añadidas)} canciones).")
        if len(pistas) > len(añadidas):
            await ctx.send(f"⚠️ Cola llena: solo caben {MAX_QUEUE_SIZE} canciones, el resto no se añadió.")

        if not ctx.voice_client.is_playing() and not ctx.voice_client.is_paused():
            await self.play_next_song(ctx)
        elif guild_id not in loop_enabled:
            self._start_prefetch(guild_id)

    @commands.hybrid_command(name="play", help="Reproduce de YouTube o Spotify (URL o búsqueda)", extras={"category": "Música"})
    async def play(self, ctx, *, query: str):
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

                if len(music_queues[guild_id]) >= MAX_QUEUE_SIZE:
                    await ctx.send(f"⚠️ La cola está llena (máximo {MAX_QUEUE_SIZE} canciones).")
                    return

                if es_spotify(query):
                    await self._play_spotify(ctx, query)
                    return

                es_url = query.startswith("http")
                info = await music_service.extract_info(query if es_url else f"ytsearch1:{query}")
                pistas = pistas_de_info(info)
                if not es_url:
                    pistas = pistas[:1]  # búsqueda: solo el primer resultado

                if not pistas:
                    await ctx.send("No se encontraron resultados.")
                    return

                hueco = MAX_QUEUE_SIZE - len(music_queues[guild_id])
                añadidas = pistas[:hueco]
                music_queues[guild_id].extend(añadidas)

                es_playlist = es_url and info.get("entries") is not None
                if es_playlist:
                    await ctx.send(f"✅ Playlist añadida: **{info.get('title', 'Lista')}** ({len(añadidas)} canciones).")
                else:
                    await ctx.send(f"➕ Añadido a la cola: **{añadidas[0][1]}**")
                if len(añadidas) < len(pistas):
                    await ctx.send(f"⚠️ Cola llena: solo caben {MAX_QUEUE_SIZE} canciones, el resto no se añadió.")

                if not ctx.voice_client.is_playing() and not ctx.voice_client.is_paused():
                    await self.play_next_song(ctx)
                elif guild_id not in loop_enabled:
                    self._start_prefetch(guild_id)

            except Exception as e:
                await ctx.send("Ocurrió un error al procesar la solicitud.")
                logger.error(f"Error al buscar música: {e}")

    @commands.hybrid_command(name="stop", help="Detiene la música y limpia la cola", extras={"category": "Música"})
    async def stop(self, ctx):
        if ctx.voice_client:
            self._reset(ctx.guild.id)
            ctx.voice_client.stop()
            await ctx.send("⏹️ Música detenida y cola vacía.")
        else:
            await ctx.send("No hay nada reproduciéndose.")

    @commands.hybrid_command(name="pause", help="Pausa la música", extras={"category": "Música"})
    async def pause(self, ctx):
        if ctx.voice_client and ctx.voice_client.is_playing():
            ctx.voice_client.pause()
            await ctx.send("⏸️ Música pausada.")
        else:
            await ctx.send("No hay música reproduciéndose.")

    @commands.hybrid_command(name="resume", help="Reanuda la música", extras={"category": "Música"})
    async def resume(self, ctx):
        if ctx.voice_client and ctx.voice_client.is_paused():
            ctx.voice_client.resume()
            await ctx.send("▶️ Música reanudada.")
        else:
            await ctx.send("La música no está pausada.")

    @commands.hybrid_command(name="skip", help="Salta la canción actual", extras={"category": "Música"})
    async def skip(self, ctx):
        if ctx.voice_client and (ctx.voice_client.is_playing() or ctx.voice_client.is_paused()):
            saltar(ctx.voice_client, ctx.guild.id)
            await ctx.send("⏭️ Canción saltada.")
        else:
            await ctx.send("No hay música reproduciéndose para saltar.")

    @commands.hybrid_command(name="queue", help="Muestra la cola de reproducción", extras={"category": "Música"})
    async def queue(self, ctx):
        guild_id = ctx.guild.id
        if guild_id in music_queues and music_queues[guild_id]:
            lineas = [f"{i+1}. {title}" for i, (_, title) in enumerate(music_queues[guild_id])]
            for mensaje in trocear(lineas, cabecera="📜 Cola de reproducción:"):
                await ctx.send(mensaje)
        else:
            await ctx.send("La cola está vacía.")

    @commands.hybrid_command(name="nowplaying", aliases=["np"], help="Muestra la canción que suena", extras={"category": "Música"})
    async def nowplaying(self, ctx):
        actual = now_playing.get(ctx.guild.id)
        if not actual:
            await ctx.send("No suena nada ahora.")
            return
        url, title = actual
        embed = discord.Embed(title="Sonando ahora", description=f"[{title}]({url})", color=0x00ff00)
        pendientes = len(music_queues.get(ctx.guild.id, []))
        bucle = "🔁 Bucle activado · " if ctx.guild.id in loop_enabled else ""
        embed.set_footer(text=f"{bucle}{pendientes} en la cola")
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="shuffle", help="Mezcla la cola", extras={"category": "Música"})
    async def shuffle(self, ctx):
        cola = music_queues.get(ctx.guild.id)
        if not cola or len(cola) < 2:
            await ctx.send("Hacen falta al menos 2 canciones en la cola.")
            return
        random.shuffle(cola)
        self._start_prefetch(ctx.guild.id)  # la siguiente ha cambiado
        await ctx.send(f"🔀 Cola mezclada ({len(cola)} canciones).")

    @commands.hybrid_command(name="loop", help="Repite la canción actual (activar/desactivar)", extras={"category": "Música"})
    async def loop(self, ctx):
        gid = ctx.guild.id
        if gid in loop_enabled:
            loop_enabled.discard(gid)
            self._start_prefetch(gid)
            await ctx.send("➡️ Bucle desactivado.")
        else:
            loop_enabled.add(gid)
            self.cancel_prefetch(gid)
            await ctx.send("🔁 Bucle activado: la canción actual se repetirá.")

    @commands.hybrid_command(name="remove", help="Quita una canción de la cola por su número", extras={"category": "Música"})
    async def remove(self, ctx, posicion: int):
        cola = music_queues.get(ctx.guild.id) or []
        if not 1 <= posicion <= len(cola):
            await ctx.send(f"Número no válido. La cola tiene {len(cola)} canciones.")
            return
        _, title = cola.pop(posicion - 1)
        if posicion == 1 and ctx.guild.id not in loop_enabled:
            self._start_prefetch(ctx.guild.id)  # la siguiente ha cambiado
        await ctx.send(f"🗑️ Quitada: **{title}**")

    @commands.hybrid_command(name="clear", help="Vacía la cola sin parar la canción actual", extras={"category": "Música"})
    async def clear(self, ctx):
        self.cancel_prefetch(ctx.guild.id)
        music_queues[ctx.guild.id] = []
        await ctx.send("🧹 Cola vaciada.")


async def setup(bot):
    await bot.add_cog(Music(bot))
