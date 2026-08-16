import asyncio
import os
from datetime import datetime, timedelta
from pathlib import Path

import yt_dlp


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

    def _build_download_opts(self, title: str | None = None, *, output_ext: str | None = None, strategy: dict | None = None) -> dict:
        safe_title = (title or 'audio').replace('/', '_').replace('\\', '_')
        ext = output_ext or '%(ext)s'
        opts = {
            **self.base_opts,
            **(strategy or {}),
            'outtmpl': str(self.temp_dir / f'{safe_title}-%(title)s.{ext}'),
            'quiet': True,
            'no_warnings': True,
            'noplaylist': True,
        }
        return opts

    def _find_downloaded_audio(self, title: str | None = None, video_id: str | None = None):
        safe_title = (title or 'audio').replace('/', '_').replace('\\', '_')
        expected_names = []
        if video_id:
            expected_names.append(f'{safe_title}-{video_id}')
        expected_names.append(safe_title)

        for name_prefix in expected_names:
            matches = sorted(self.temp_dir.glob(f'{name_prefix}*.opus')) + sorted(self.temp_dir.glob(f'{name_prefix}*.mp3')) + sorted(self.temp_dir.glob(f'{name_prefix}*.m4a')) + sorted(self.temp_dir.glob(f'{name_prefix}*.webm')) + sorted(self.temp_dir.glob(f'{name_prefix}*.ogg'))
            if matches:
                return str(matches[0])

        for candidate in sorted(self.temp_dir.iterdir()):
            if candidate.is_file() and candidate.suffix.lower() in {'.opus', '.mp3', '.m4a', '.webm', '.ogg'}:
                name_ok = title is None or candidate.name.startswith(safe_title)
                if name_ok:
                    return str(candidate)

        return None

    async def extract_info(self, query: str, *, download: bool = False):
        """Extrae información sin depender de un stream directo de GoogleVideo."""
        last_error = None
        for strategy in self._get_strategies():
            opts = {
                **self.base_opts,
                **strategy,
                'noplaylist': False,
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False,
            }
            try:
                return await asyncio.to_thread(yt_dlp.YoutubeDL(opts).extract_info, query, download=download)
            except Exception as exc:
                last_error = exc
        if last_error:
            raise last_error
        raise RuntimeError(f'No se pudo extraer información para: {query}')

    async def download_audio(self, video_url: str, title: str | None = None) -> str:
        """Descarga el audio a un archivo local y devuelve la ruta local segura."""
        last_error = None

        for strategy in self._get_strategies():
            opts = {
                **self.base_opts,
                **strategy,
                'outtmpl': str(self.temp_dir / f'{(title or "audio").replace("/", "_").replace("\\", "_")}-%(title)s.%(ext)s'),
                'noplaylist': True,
                'quiet': True,
                'no_warnings': True,
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'opus',
                    'preferredquality': '0',
                }],
                'format': 'bestaudio/best',
            }
            try:
                with yt_dlp.YoutubeDL(opts) as ydl:
                    info = await asyncio.to_thread(ydl.extract_info, video_url, download=True)
                video_id = info.get('id') if isinstance(info, dict) else None
                found = self._find_downloaded_audio(title=title, video_id=video_id)
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
