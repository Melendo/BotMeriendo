import asyncio
import os
from pathlib import Path

import yt_dlp


class YTDLService:
    """Servicio centralizado para obtener metadatos y descargar audio localmente."""

    def __init__(self, cookies_path: str = "cookies.txt", temp_dir: str = "/tmp/botmeriendo"):
        self.cookies_path = cookies_path
        self.temp_dir = Path(temp_dir)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.base_opts = {
            'format': 'bestaudio/best',
            'noplaylist': False,
            'quiet': True,
            'no_warnings': True,
            'ignoreerrors': True,
            'cookiefile': self.cookies_path,
            'extractor_args': {
                'youtube': {
                    'player_client': ['default', 'web', 'android']
                }
            },
            'source_address': '0.0.0.0',
            'nocheckcertificate': True,
            'socket_timeout': 15,
            'retries': 3,
        }

    def _build_download_opts(self, title: str | None = None, *, output_ext: str | None = None) -> dict:
        safe_title = (title or 'audio').replace('/', '_').replace('\\', '_')
        ext = output_ext or '%(ext)s'
        return {
            **self.base_opts,
            'outtmpl': str(self.temp_dir / f'{safe_title}-%(id)s.{ext}'),
            'quiet': True,
            'no_warnings': True,
            'noplaylist': True,
        }

    async def extract_info(self, query: str, *, download: bool = False):
        """Extrae información sin depender de un stream directo de GoogleVideo."""
        opts = self.base_opts.copy()
        opts['noplaylist'] = False
        opts['quiet'] = True
        opts['no_warnings'] = True
        opts['extract_flat'] = False
        return await asyncio.to_thread(yt_dlp.YoutubeDL(opts).extract_info, query, download=download)

    async def download_audio(self, video_url: str, title: str | None = None) -> str:
        """Descarga el audio a un archivo local y devuelve la ruta local segura."""
        safe_title = (title or 'audio').replace('/', '_').replace('\\', '_')
        opts = {
            **self.base_opts,
            'outtmpl': str(self.temp_dir / f'{safe_title}-%(title)s.%(ext)s'),
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

        with yt_dlp.YoutubeDL(opts) as ydl:
            info = await asyncio.to_thread(ydl.extract_info, video_url, download=True)
            video_id = info.get('id') if isinstance(info, dict) else None
            expected_name = safe_title if not video_id else f'{safe_title}-{video_id}'
            matches = list(self.temp_dir.glob(f'{expected_name}*.opus'))
            if matches:
                return str(matches[0])
            for candidate in self.temp_dir.glob(f'{safe_title}*.*'):
                if candidate.suffix.lower() in {'.opus', '.mp3', '.m4a', '.webm', '.ogg'}:
                    return str(candidate)
            raise FileNotFoundError(f'No se pudo localizar el archivo descargado para {title or video_url}')


music_service = YTDLService()
