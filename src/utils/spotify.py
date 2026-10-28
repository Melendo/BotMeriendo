"""Lee canciones de Spotify (playlist, álbum o canción) con la API oficial.

Spotify no deja reproducir su audio: solo se leen "artista - título" y cada
canción se busca luego en YouTube.

Desde febrero de 2026, una app en "Development Mode" solo puede leer el
contenido de playlists que el dueño de la app ha creado o en las que colabora.
Por eso se usa un refresh token de esa cuenta (ver scripts/spotify_token.py).
"""
import base64
import re
import time

import aiohttp

API = "https://api.spotify.com/v1"
TOKEN_URL = "https://accounts.spotify.com/api/token"
PAGE_SIZE = 50

_URL_RE = re.compile(
    r"(?:open\.spotify\.com/(?:intl-[a-z]{2}(?:-[a-z]{2})?/)?|spotify:)"
    r"(playlist|album|track)[/:]([A-Za-z0-9]{22})"
)


class SpotifyError(Exception):
    """Error con mensaje listo para mostrar en Discord."""


def parse_spotify_url(texto: str) -> tuple[str, str] | None:
    """('playlist' | 'album' | 'track', id) o None si no es de Spotify."""
    m = _URL_RE.search(texto or "")
    return (m.group(1), m.group(2)) if m else None


def es_spotify(texto: str) -> bool:
    return parse_spotify_url(texto) is not None


def busqueda_youtube(cancion: dict) -> tuple[str, str] | None:
    """Canción de Spotify -> (búsqueda de YouTube, título para mostrar)."""
    if not cancion or cancion.get("type", "track") != "track" or not cancion.get("name"):
        return None  # episodios de podcast, canciones locales sin datos...
    artistas = ", ".join(a["name"] for a in cancion.get("artists") or [] if a.get("name"))
    titulo = f"{artistas} - {cancion['name']}" if artistas else cancion["name"]
    return f"ytsearch1:{titulo} audio", titulo


class SpotifyClient:
    def __init__(self, client_id: str | None, client_secret: str | None, refresh_token: str | None):
        self.client_id = client_id
        self.client_secret = client_secret
        self.refresh_token = refresh_token
        self._token: str | None = None
        self._expira = 0.0

    @property
    def configurado(self) -> bool:
        return bool(self.client_id and self.client_secret and self.refresh_token)

    async def _access_token(self, session: aiohttp.ClientSession) -> str:
        if self._token and time.monotonic() < self._expira - 60:
            return self._token
        basic = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode()).decode()
        async with session.post(
            TOKEN_URL,
            data={"grant_type": "refresh_token", "refresh_token": self.refresh_token},
            headers={"Authorization": f"Basic {basic}"},
        ) as r:
            data = await r.json(content_type=None)
            if r.status != 200 or "access_token" not in data:
                raise SpotifyError("No pude iniciar sesión en Spotify. Revisa las claves SPOTIFY_* del .env.")
        self._token = data["access_token"]
        self._expira = time.monotonic() + data.get("expires_in", 3600)
        if data.get("refresh_token"):
            self.refresh_token = data["refresh_token"]  # Spotify a veces lo renueva
        return self._token

    async def _get(self, session: aiohttp.ClientSession, url: str, params=None) -> dict:
        token = await self._access_token(session)
        async with session.get(url, params=params, headers={"Authorization": f"Bearer {token}"}) as r:
            if r.status == 429:
                raise SpotifyError("Spotify pide esperar un poco (demasiadas peticiones). Prueba en un minuto.")
            if r.status in (403, 404):
                raise SpotifyError(
                    "No puedo leer eso de Spotify. Solo puedo leer playlists de la cuenta del bot "
                    "o colaborativas en las que esté, y tienen que existir."
                )
            if r.status != 200:
                raise SpotifyError(f"Spotify respondió con error {r.status}.")
            return await r.json(content_type=None)

    async def canciones(self, tipo: str, sid: str, limite: int) -> tuple[str, list[dict]]:
        """(nombre, canciones) de una playlist, álbum o canción. Como mucho `limite`."""
        if not self.configurado:
            raise SpotifyError("Spotify no está configurado en este bot (faltan claves SPOTIFY_* en el .env).")
        if limite <= 0:
            return "", []

        timeout = aiohttp.ClientTimeout(total=20)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            if tipo == "track":
                cancion = await self._get(session, f"{API}/tracks/{sid}")
                return cancion.get("name", ""), [cancion]

            if tipo == "album":
                info = await self._get(session, f"{API}/albums/{sid}")
                url = f"{API}/albums/{sid}/tracks"
                sacar = lambda e: e  # noqa: E731  (en álbumes cada elemento ya es la canción)
            else:
                info = await self._get(session, f"{API}/playlists/{sid}", {"fields": "name"})
                url = f"{API}/playlists/{sid}/items"
                # 2026: el campo pasó de "track" a "item"; se aceptan los dos
                sacar = lambda e: (e or {}).get("item") or (e or {}).get("track")  # noqa: E731

            nombre = info.get("name", "")
            resultado: list[dict] = []
            offset = 0
            while len(resultado) < limite:
                pagina = await self._get(session, url, {"limit": PAGE_SIZE, "offset": offset})
                elementos = pagina.get("items")
                if elementos is None:
                    raise SpotifyError(
                        "Spotify no deja ver las canciones de esa playlist. Solo puedo leer playlists "
                        "de la cuenta del bot o colaborativas en las que esté."
                    )
                resultado.extend(c for c in (sacar(e) for e in elementos) if c)
                if not pagina.get("next") or not elementos:
                    break
                offset += PAGE_SIZE
            return nombre, resultado[:limite]
