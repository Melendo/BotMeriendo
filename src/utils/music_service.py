import asyncio
import os
import re
from datetime import datetime, timedelta
from pathlib import Path

import yt_dlp

AUDIO_EXTS = ('.opus', '.m4a', '.webm', '.mp3', '.ogg')
_YT_ID_RE = re.compile(r'(?:[?&]v=|youtu\.be/|/shorts/|/embed/)([\w-]{11})')


class YTDLService:
    """Servicio centralizado para obtener metadatos y descargar audio localmente."""

    def __init__(self, cookies_path: str = "cookies.txt", temp_dir: str = "/tmp/botmeriendo"):
        self.cookies_path = cookies_path
        self.temp_dir = Path(temp_dir)
        self.temp_dir.mkdir(parents=True, exist_ok=True)

        cookiefile = None
        if os.path.exists(self.cookies_path) and os.path.getsize(self.cookies_path) > 0:
            cookiefile = self.cookies_path

        self.base_opts = {
            'format': 'bestaudio/best',
            'noplaylist': False,
            'quiet': True,
            'no_warnings': True,
            'ignoreerrors': True,
            'source_address': '0.0.0.0',
            'nocheckcertificate': True,
            'socket_timeout': 15,
            'retries': 3,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36',
                'Referer': 'https://www.youtube.com/'
            },
        }
        if cookiefile:
            self.base_opts['cookiefile'] = cookiefile

    def _get_strategies(self):
        return [
            {
                'extractor_args': {
                    'youtube': {
                        'player_client': ['android']
                    }
                }
            },
            {
                'extractor_args': {
                    'youtube': {
                        'player_client': ['web', 'android', 'tv_embedded']
                    }
                }
            },
            {
                'extractor_args': {
                    'youtube': {
                        'player_client': ['default', 'web', 'android']
                    }
                }
            },
            {
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36',
                    'Referer': 'https://www.youtube.com/'
                }
            },
        ]

    def cleanup_old_files(self, max_age_hours: int = 24, max_files: int = 300) -> int:
        """Elimina archivos temporales viejos para evitar acumular música descargada."""
        now = datetime.now()
        cutoff = now - timedelta(hours=max_age_hours)
        deleted = 0

        candidates = sorted(self.temp_dir.iterdir(), key=lambda p: p.stat().st_mtime)
        for file_path in candidates:
            if file_path.is_file() and file_path.stat().st_mtime < cutoff.timestamp():
                try:
                    file_path.unlink()
                    deleted += 1
                except OSError:
                    continue

        if max_files > 0:
            files = sorted(self.temp_dir.iterdir(), key=lambda p: p.stat().st_mtime)
            while len(files) > max_files:
                oldest = files.pop(0)
                try:
                    oldest.unlink()
                    deleted += 1
                except OSError:
                    continue

        return deleted

    def _build_download_opts(self, title: str | None = None, *, strategy: dict | None = None) -> dict:
        # El archivo se llama por el id del vídeo: único y fácil de reencontrar (caché).
        opts = {
            **self.base_opts,
            **(strategy or {}),
            'outtmpl': str(self.temp_dir / '%(id)s.%(ext)s'),
            'quiet': True,
            'no_warnings': True,
            'noplaylist': True,
        }
        return opts

    @staticmethod
    def video_id(url: str | None) -> str | None:
        """Id de 11 caracteres de un enlace de YouTube, o None."""
        if not url:
            return None
        m = _YT_ID_RE.search(url)
        return m.group(1) if m else None

    def cached_path(self, url: str | None) -> str | None:
        """Ruta del audio ya descargado para ese enlace, si existe."""
        vid = self.video_id(url)
        if not vid:
            return None
        for ext in AUDIO_EXTS:
            p = self.temp_dir / f'{vid}{ext}'
            if p.is_file() and p.stat().st_size > 0:
                p.touch()  # recién usado: que la limpieza no lo borre
                return str(p)
        return None

    def _find_downloaded_audio(self, info) -> str | None:
        """Ruta final del audio según lo que devuelve yt-dlp."""
        if not isinstance(info, dict):
            return None
        for d in info.get('requested_downloads') or []:
            fp = d.get('filepath')
            if fp and os.path.isfile(fp):
                return fp
        vid = info.get('id')
        if vid:
            for ext in AUDIO_EXTS:
                p = self.temp_dir / f'{vid}{ext}'
                if p.is_file():
                    return str(p)
        return None

    async def extract_info(self, query: str, *, download: bool = False, flat: bool = True):
        """Extrae información sin depender de un stream directo de GoogleVideo.

        flat=True: en playlists y búsquedas solo pide url y título de cada vídeo
        (muy rápido). El audio se resuelve después, al reproducir.
        """
        last_error = None
        for strategy in self._get_strategies():
            opts = {
                **self.base_opts,
                **strategy,
                'noplaylist': False,
                'quiet': True,
                'no_warnings': True,
                'extract_flat': 'in_playlist' if flat else False,
            }
            try:
                info = await asyncio.to_thread(yt_dlp.YoutubeDL(opts).extract_info, query, download=download)
                if info:
                    return info
                # Con ignoreerrors yt-dlp devuelve None en vez de fallar: probar otra estrategia
            except Exception as exc:
                last_error = exc
        if last_error:
            raise last_error
        raise RuntimeError(f'No se pudo extraer información para: {query}')

    async def download_audio(self, video_url: str, title: str | None = None) -> str:
        """Descarga el audio a un archivo local y devuelve la ruta local segura."""
        cached = self.cached_path(video_url)
        if cached:
            return cached

        last_error = None

        for strategy in self._get_strategies():
            opts = {
                **self._build_download_opts(title, strategy=strategy),
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'opus',
                    'preferredquality': '0',
                }],
                'format': 'bestaudio/best',
                # Un solo vídeo: mejor que falle con el error real (p. ej. "Sign in
                # to confirm you're not a bot") que devolver None en silencio.
                'ignoreerrors': False,
            }
            try:
                with yt_dlp.YoutubeDL(opts) as ydl:
                    info = await asyncio.to_thread(ydl.extract_info, video_url, download=True)
                found = self._find_downloaded_audio(info)
                if found:
                    return found
            except Exception as exc:
                last_error = exc
                continue

        if last_error:
            raise last_error
        raise FileNotFoundError(f'No se pudo localizar el archivo descargado para {title or video_url}')

    def prune_cache_if_needed(self) -> None:
        """Limpia caché de música cada cierto número de descargas o al arrancar."""
        try:
            self.cleanup_old_files()
        except Exception:
            pass


music_service = YTDLService()
