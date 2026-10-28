import asyncio

from src.utils.music_service import YTDLService
from src.utils.state import music_queues

A = ("https://www.youtube.com/watch?v=aaaaaaaaaaa", "A")
B = ("https://www.youtube.com/watch?v=bbbbbbbbbbb", "B")


async def test_prefetch_baja_la_siguiente_una_vez(music, ctx, fake_audio):
    music_queues[ctx.guild.id] = [A, B]

    await music.play_next_song(ctx)          # suena A, empieza a bajar B
    assert ctx.voice_client.played == ["/fake/aaaaaaaaaaa.opus"]
    await asyncio.sleep(0.01)
    assert fake_audio == [A[0], B[0]]

    ctx.voice_client.stop()
    await music.play_next_song(ctx)          # suena B, sin volver a bajarla
    assert ctx.voice_client.played[-1] == "/fake/bbbbbbbbbbb.opus"
    assert fake_audio.count(B[0]) == 1


async def test_stop_cancela_prefetch(music, ctx, fake_audio):
    music_queues[ctx.guild.id] = [A, B]
    await music.play_next_song(ctx)
    assert ctx.guild.id in music._prefetch
    await music.stop.callback(music, ctx)
    assert ctx.guild.id not in music._prefetch
    assert music_queues[ctx.guild.id] == []


async def test_cola_vacia_avisa_en_el_canal(music, ctx, fake_audio):
    await music.play_next_song(ctx)
    assert ctx.channel.sent == ["La cola de reproducción ha terminado."]


def test_video_id():
    vid = YTDLService.video_id
    assert vid("https://www.youtube.com/watch?v=dQw4w9WgXcQ&list=x") == "dQw4w9WgXcQ"
    assert vid("https://youtu.be/dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert vid("https://www.youtube.com/shorts/dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert vid("https://example.com") is None


async def test_cache_evita_descargar_otra_vez(tmp_path, monkeypatch):
    svc = YTDLService(temp_dir=str(tmp_path))
    (tmp_path / "dQw4w9WgXcQ.opus").write_bytes(b"audio")

    def boom(*a, **k):
        raise AssertionError("no debería descargar")
    monkeypatch.setattr("src.utils.music_service.yt_dlp.YoutubeDL", boom)

    path = await svc.download_audio("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    assert path == str(tmp_path / "dQw4w9WgXcQ.opus")
