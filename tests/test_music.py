from src.utils.state import music_queues


async def test_queue_larga_no_pasa_de_2000(music, ctx):
    music_queues[ctx.guild.id] = [(f"u{i}", "T" * 180) for i in range(30)]
    await music.queue.callback(music, ctx)
    assert len(ctx.sent) > 1
    assert all(len(m) <= 2000 for m in ctx.sent)


async def test_queue_vacia(music, ctx):
    await music.queue.callback(music, ctx)
    assert ctx.sent == ["La cola está vacía."]
