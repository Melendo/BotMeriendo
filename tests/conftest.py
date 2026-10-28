import os
import sys
from pathlib import Path

import pytest

# Token falso: los tests nunca se conectan a Discord.
os.environ.setdefault("TOKEN", "dummy-token")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import discord
from discord.ext import commands

EXTENSIONS = ["src.cogs.general", "src.cogs.music", "src.cogs.events"]


@pytest.fixture
async def bot():
    b = commands.Bot(command_prefix="!", intents=discord.Intents.default())
    for ext in EXTENSIONS:
        await b.load_extension(ext)
    yield b
    await b.close()


class FakeVoice:
    """Cliente de voz falso: guarda el estado como uno real."""

    def __init__(self):
        self.playing = False
        self.paused = False
        self.played = []

    def is_playing(self):
        return self.playing

    def is_paused(self):
        return self.paused

    def is_connected(self):
        return True

    def play(self, source, after=None):
        self.played.append(source)
        self.playing = True
        self.after = after

    def stop(self):
        self.playing = False
        self.paused = False

    def pause(self):
        self.playing, self.paused = False, True

    def resume(self):
        self.playing, self.paused = True, False


class FakeChannel:
    def __init__(self):
        self.sent = []

    async def send(self, content=None, **kwargs):
        self.sent.append(content if content is not None else kwargs)


class FakeCtx:
    """Contexto falso: lo que mandan ctx.send y ctx.channel.send queda en .sent."""

    def __init__(self, guild_id=1):
        from types import SimpleNamespace
        self.guild = SimpleNamespace(id=guild_id, name="test")
        self.voice_client = FakeVoice()
        self.channel = FakeChannel()
        self.sent = self.channel.sent
        self.author = SimpleNamespace(voice=None, mention="@yo")

    async def send(self, content=None, **kwargs):
        self.sent.append(content if content is not None else kwargs)

    def typing(self):
        import contextlib

        @contextlib.asynccontextmanager
        async def _t():
            yield
        return _t()


@pytest.fixture
def ctx():
    from src.utils.state import music_queues
    music_queues.clear()
    return FakeCtx()


@pytest.fixture
def music(bot):
    return bot.get_cog("Music")
