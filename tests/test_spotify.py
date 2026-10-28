import pytest
from aiohttp import web

from src.utils import spotify as sp
from src.utils.spotify import SpotifyClient, SpotifyError, busqueda_youtube, parse_spotify_url
from src.utils.state import music_queues, now_playing

PID = "37i9dQZF1DXcBWIGoYBM5M"  # 22 caracteres, como los ids reales
AID = "4aawyAB9vmqN3uQ7FjRGTy"
TID = "11dFghVXANMlKmJXsNCbNl"


# ---------- funciones puras ----------

@pytest.mark.parametrize("texto,esperado", [
    (f"https://open.spotify.com/playlist/{PID}?si=abc", ("playlist", PID)),
    (f"https://open.spotify.com/intl-es/album/{AID}", ("album", AID)),
    (f"spotify:track:{TID}", ("track", TID)),
    ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", None),
    ("rick astley", None),
])
def test_parse_spotify_url(texto, esperado):
    assert parse_spotify_url(texto) == esperado


def test_busqueda_youtube():
    c = {"type": "track", "name": "Bohemian Rhapsody", "artists": [{"name": "Queen"}]}
    assert busqueda_youtube(c) == ("ytsearch1:Queen - Bohemian Rhapsody audio", "Queen - Bohemian Rhapsody")
    dos = {"name": "X", "artists": [{"name": "A"}, {"name": "B"}]}
    assert busqueda_youtube(dos)[1] == "A, B - X"
    assert busqueda_youtube({"type": "episode", "name": "Podcast"}) is None
    assert busqueda_youtube({"type": "track", "name": None}) is None
    assert busqueda_youtube(None) is None


# ---------- cliente HTTP contra una API falsa en 127.0.0.1 ----------

def _cancion(i):
    return {"type": "track", "name": f"Song {i}", "artists": [{"name": "Band"}]}


@pytest.fixture
async def api_falsa(monkeypatch):
    estado = {"tokens": 0}

    async def token(request):
        estado["tokens"] += 1
        form = await request.post()
        if form.get("refresh_token") != "rt-bueno":
            return web.json_response({"error": "invalid_grant"}, status=400)
        return web.json_response({"access_token": "at", "expires_in": 3600})

    def auth_ok(request):
        return request.headers.get("Authorization") == "Bearer at"

    async def playlist(request):
        if request.match_info["id"] == "x" * 22:
            return web.json_response({"error": "not found"}, status=404)
        return web.json_response({"name": "Mi lista"})

    async def items(request):
        assert auth_ok(request)
        if request.match_info["id"] == "y" * 22:  # playlist ajena: sin items
            return web.json_response({"href": "..."})
        off, lim = int(request.query["offset"]), int(request.query["limit"])
        total = 120
        page = [{"item": _cancion(i)} for i in range(off, min(off + lim, total))]
        page.insert(0, {"item": None})  # canción local borrada
        nxt = "more" if off + lim < total else None
        return web.json_response({"items": page, "next": nxt})

    async def album(request):
        return web.json_response({"name": "Mi disco"})

    async def album_tracks(request):
        return web.json_response({"items": [_cancion(i) for i in range(3)], "next": None})

    async def track(request):
        return web.json_response(_cancion(7))

    app = web.Application()
    app.router.add_post("/api/token", token)
    app.router.add_get("/v1/playlists/{id}", playlist)
    app.router.add_get("/v1/playlists/{id}/items", items)
    app.router.add_get("/v1/albums/{id}", album)
    app.router.add_get("/v1/albums/{id}/tracks", album_tracks)
    app.router.add_get("/v1/tracks/{id}", track)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()
    port = site._server.sockets[0].getsockname()[1]
    monkeypatch.setattr(sp, "API", f"http://127.0.0.1:{port}/v1")
    monkeypatch.setattr(sp, "TOKEN_URL", f"http://127.0.0.1:{port}/api/token")
    yield estado
    await runner.cleanup()


def _cliente(rt="rt-bueno"):
    return SpotifyClient("id", "secret", rt)


async def test_playlist_paginada_y_limite(api_falsa):
    c = _cliente()
    nombre, canciones = await c.canciones("playlist", PID, 31)
    assert nombre == "Mi lista"
    assert len(canciones) == 31
    assert canciones[0]["name"] == "Song 0"  # el None se ignora
    nombre, todas = await c.canciones("playlist", PID, 500)
    assert len(todas) == 120                   # 3 páginas de 50
    assert api_falsa["tokens"] == 1            # el token se reutiliza


async def test_album_y_cancion(api_falsa):
    c = _cliente()
    assert (await c.canciones("album", AID, 30))[0] == "Mi disco"
    assert len((await c.canciones("album", AID, 30))[1]) == 3
    nombre, canciones = await c.canciones("track", TID, 30)
    assert canciones[0]["name"] == "Song 7"


async def test_errores_claros(api_falsa):
    with pytest.raises(SpotifyError, match="Solo puedo leer"):
        await _cliente().canciones("playlist", "x" * 22, 30)    # 404
    with pytest.raises(SpotifyError, match="no deja ver"):
        await _cliente().canciones("playlist", "y" * 22, 30)    # ajena
    with pytest.raises(SpotifyError, match="iniciar sesión"):
        await _cliente("rt-malo").canciones("playlist", PID, 30)


async def test_sin_configurar():
    with pytest.raises(SpotifyError, match="no está configurado"):
        await SpotifyClient(None, None, None).canciones("playlist", PID, 30)


# ---------- integración con el cog de música ----------

async def test_play_spotify_encola_busquedas(music, ctx, monkeypatch):
    from src.cogs import music as mod

    async def fake_canciones(tipo, sid, limite):
        assert (tipo, sid) == ("playlist", PID)
        return "Mi lista", [_cancion(i) for i in range(min(40, limite))]

    async def no_play(*a, **k):
        pass

    monkeypatch.setattr(mod.spotify, "canciones", fake_canciones)
    monkeypatch.setattr(music, "play_next_song", no_play)
    await music.play.callback(music, ctx, query=f"https://open.spotify.com/playlist/{PID}")

    cola = music_queues[ctx.guild.id]
    assert len(cola) == mod.MAX_QUEUE_SIZE
    assert cola[0] == ("ytsearch1:Band - Song 0 audio", "Band - Song 0")
    assert any("Añadidas de Spotify" in m and "30 canciones" in m for m in ctx.sent)
    assert any("Cola llena" in m for m in ctx.sent)


async def test_play_spotify_error_se_muestra(music, ctx, monkeypatch):
    from src.cogs import music as mod

    async def falla(*a):
        raise SpotifyError("Spotify no está configurado en este bot.")

    monkeypatch.setattr(mod.spotify, "canciones", falla)
    await music.play.callback(music, ctx, query=f"spotify:album:{AID}")
    assert ctx.sent == ["❌ Spotify no está configurado en este bot."]
    assert music_queues[ctx.guild.id] == []


async def test_busqueda_se_resuelve_al_reproducir(music, ctx, monkeypatch, fake_audio):
    from src.cogs import music as mod
    real = "https://www.youtube.com/watch?v=fJ9rUzIMcZQ"

    async def fake_extract(query, **kw):
        assert query == "ytsearch1:Queen - Bohemian Rhapsody audio"
        return {"entries": [{"url": real, "title": "Queen – Bohemian Rhapsody (Official Video)"}]}

    monkeypatch.setattr(mod.music_service, "extract_info", fake_extract)
    music_queues[ctx.guild.id] = [("ytsearch1:Queen - Bohemian Rhapsody audio", "Queen - Bohemian Rhapsody")]
    await music.play_next_song(ctx)

    assert fake_audio == [real]                       # se baja el vídeo real
    assert now_playing[ctx.guild.id] == (real, "Queen - Bohemian Rhapsody")
    embed = ctx.channel.sent[0]["embed"]
    assert real in embed.description                  # el enlace del mensaje funciona
