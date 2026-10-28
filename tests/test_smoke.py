from types import SimpleNamespace

from src.cogs.events import _solo_bots
from src.utils.music_service import music_service

BASE_COMMANDS = {
    "comandos", "hola", "join", "leave", "pause", "ping",
    "play", "queue", "resume", "skip", "stop",
    "nowplaying", "shuffle", "loop", "remove", "clear",
}


async def test_cogs_cargan(bot):
    assert {"General", "Music", "Events"} <= set(bot.cogs)


async def test_comandos_registrados(bot):
    names = {c.name for c in bot.commands}
    assert BASE_COMMANDS <= names


def test_main_importa():
    import src.main  # noqa: F401


def test_opts_descarga_por_id():
    opts = music_service._build_download_opts("a/b\\c", strategy={"x": 1})
    assert opts["outtmpl"].endswith("%(id)s.%(ext)s")
    assert opts["noplaylist"] is True
    assert opts["x"] == 1


def _canal(*bots):
    return SimpleNamespace(members=[SimpleNamespace(bot=b) for b in bots])


def test_solo_bots():
    assert _solo_bots(_canal(True))
    assert _solo_bots(_canal(True, True))
    assert not _solo_bots(_canal(True, False))


def test_intents_minimos():
    from src.main import bot as main_bot
    it = main_bot.intents
    assert it.message_content and it.members and it.voice_states and it.guilds
    assert not it.presences  # no lo usa: no se pide
