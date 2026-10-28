import re

from discord import AppCommandOptionType

from test_smoke import BASE_COMMANDS


async def test_todos_tienen_version_barra(bot):
    slash = {c.name for c in bot.tree.get_commands()}
    assert BASE_COMMANDS <= slash


async def test_barra_cumple_limites_de_discord(bot):
    for cmd in bot.tree.get_commands():
        data = cmd.to_dict(bot.tree)  # falla si algo no es válido
        assert re.fullmatch(r"[a-z0-9_-]{1,32}", data["name"])
        assert 1 <= len(data["description"]) <= 100, data["name"]


async def test_parametros_barra(bot):
    tree = {c.name: c for c in bot.tree.get_commands()}
    play = tree["play"].parameters
    assert [p.name for p in play] == ["query"] and play[0].type == AppCommandOptionType.string
    remove = tree["remove"].parameters
    assert remove[0].type == AppCommandOptionType.integer


async def test_categorias_en_ayuda(bot, ctx):
    general = bot.get_cog("General")
    await general.help_custom.callback(general, ctx)
    embed = ctx.sent[-1]["embed"]
    campos = {f.name: f.value for f in embed.fields}
    assert set(campos) == {"**Música**", "**Basico**"}
    assert "play" in campos["**Música**"] and "ping" in campos["**Basico**"]


async def test_main_registra_sync():
    from src.main import bot as main_bot, sync_slash_commands
    assert main_bot.setup_hook is sync_slash_commands
