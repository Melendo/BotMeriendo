from src.utils.state import music_queues


async def test_queue_larga_no_pasa_de_2000(music, ctx):
    music_queues[ctx.guild.id] = [(f"u{i}", "T" * 180) for i in range(30)]
    await music.queue.callback(music, ctx)
    assert len(ctx.sent) > 1
    assert all(len(m) <= 2000 for m in ctx.sent)


async def test_queue_vacia(music, ctx):
    await music.queue.callback(music, ctx)
    assert ctx.sent == ["La cola está vacía."]


def _fake_extract(info):
    async def _f(query, **kw):
        _f.query = query
        return info
    return _f


async def _no_play(*a, **k):
    pass


async def test_play_playlist_respeta_limite(music, ctx, monkeypatch):
    from src.cogs import music as mod
    info = {"title": "Lista", "entries": [{"url": f"https://y/{i}", "title": f"t{i}"} for i in range(50)]}
    monkeypatch.setattr(mod.music_service, "extract_info", _fake_extract(info))
    monkeypatch.setattr(music, "play_next_song", _no_play)
    await music.play.callback(music, ctx, query="https://youtube.com/playlist?list=x")
    assert len(music_queues[ctx.guild.id]) == mod.MAX_QUEUE_SIZE
    assert any("Playlist añadida" in m and "30 canciones" in m for m in ctx.sent)
    assert any("Cola llena" in m for m in ctx.sent)


async def test_play_busqueda_coge_el_primero(music, ctx, monkeypatch):
    from src.cogs import music as mod
    info = {"entries": [{"url": "https://y/a", "title": "A"}, {"url": "https://y/b", "title": "B"}]}
    fake = _fake_extract(info)
    monkeypatch.setattr(mod.music_service, "extract_info", fake)
    monkeypatch.setattr(music, "play_next_song", _no_play)
    await music.play.callback(music, ctx, query="rick astley")
    assert fake.query == "ytsearch1:rick astley"
    assert music_queues[ctx.guild.id] == [("https://y/a", "A")]
    assert ctx.sent == ["➕ Añadido a la cola: **A**"]


async def test_play_sin_resultados(music, ctx, monkeypatch):
    from src.cogs import music as mod
    monkeypatch.setattr(mod.music_service, "extract_info", _fake_extract(None))
    monkeypatch.setattr(music, "play_next_song", _no_play)
    await music.play.callback(music, ctx, query="nada")
    assert ctx.sent == ["No se encontraron resultados."]
    assert music_queues[ctx.guild.id] == []
