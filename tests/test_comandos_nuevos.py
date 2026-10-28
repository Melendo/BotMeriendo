import asyncio

from src.utils.state import loop_enabled, music_queues, now_playing

A = ("https://www.youtube.com/watch?v=aaaaaaaaaaa", "A")
B = ("https://www.youtube.com/watch?v=bbbbbbbbbbb", "B")
C = ("https://www.youtube.com/watch?v=ccccccccccc", "C")


async def _fin_de_cancion(music, ctx):
    """Simula que la canción acaba sola (lo que hace el callback after)."""
    ctx.voice_client.stop()
    await music.play_next_song(ctx)


async def test_nowplaying(music, ctx, fake_audio):
    await music.nowplaying.callback(music, ctx)
    assert ctx.sent == ["No suena nada ahora."]
    music_queues[ctx.guild.id] = [A, B]
    await music.play_next_song(ctx)
    ctx.sent.clear()
    await music.nowplaying.callback(music, ctx)
    embed = ctx.sent[0]["embed"]
    assert "A" in embed.description and "1 en la cola" in embed.footer.text


async def test_loop_repite_y_skip_avanza(music, ctx, fake_audio):
    music_queues[ctx.guild.id] = [A, B]
    await music.play_next_song(ctx)
    await music.loop.callback(music, ctx)
    assert ctx.guild.id in loop_enabled

    await _fin_de_cancion(music, ctx)                  # acaba sola: se repite A
    assert now_playing[ctx.guild.id] == A
    assert music_queues[ctx.guild.id] == [B]

    await music.skip.callback(music, ctx)              # skip: pasa a B aunque haya bucle
    await music.play_next_song(ctx)
    assert now_playing[ctx.guild.id] == B

    await music.loop.callback(music, ctx)
    assert ctx.guild.id not in loop_enabled


async def test_stop_quita_el_bucle(music, ctx, fake_audio):
    music_queues[ctx.guild.id] = [A]
    await music.play_next_song(ctx)
    await music.loop.callback(music, ctx)
    await music.stop.callback(music, ctx)
    assert ctx.guild.id not in loop_enabled
    assert ctx.guild.id not in now_playing


async def test_remove(music, ctx):
    music_queues[ctx.guild.id] = [A, B, C]
    await music.remove.callback(music, ctx, 2)
    assert music_queues[ctx.guild.id] == [A, C]
    assert ctx.sent[-1] == "🗑️ Quitada: **B**"
    await music.remove.callback(music, ctx, 9)
    assert "no válido" in ctx.sent[-1]
    assert music_queues[ctx.guild.id] == [A, C]


async def test_clear_no_para_la_actual(music, ctx, fake_audio):
    music_queues[ctx.guild.id] = [A, B, C]
    await music.play_next_song(ctx)
    await music.clear.callback(music, ctx)
    assert music_queues[ctx.guild.id] == []
    assert ctx.voice_client.is_playing()
    assert now_playing[ctx.guild.id] == A


async def test_shuffle(music, ctx, monkeypatch):
    import random
    music_queues[ctx.guild.id] = [A]
    await music.shuffle.callback(music, ctx)
    assert "al menos 2" in ctx.sent[-1]

    music_queues[ctx.guild.id] = [A, B, C]
    monkeypatch.setattr(random, "shuffle", lambda l: l.reverse())
    monkeypatch.setattr(music, "_start_prefetch", lambda gid: None)
    await music.shuffle.callback(music, ctx)
    assert music_queues[ctx.guild.id] == [C, B, A]


async def test_reset_al_desconectar(bot, ctx, fake_audio):
    from types import SimpleNamespace
    music = bot.get_cog("Music")
    events = bot.get_cog("Events")
    music_queues[ctx.guild.id] = [A, B]
    await music.play_next_song(ctx)
    loop_enabled.add(ctx.guild.id)

    events._reset_musica(SimpleNamespace(id=ctx.guild.id))
    await asyncio.sleep(0)
    assert music_queues[ctx.guild.id] == []
    assert ctx.guild.id not in now_playing and ctx.guild.id not in loop_enabled
    assert ctx.guild.id not in music._prefetch
