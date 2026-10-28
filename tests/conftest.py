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
