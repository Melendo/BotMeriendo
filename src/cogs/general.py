import discord
from discord.ext import commands
from src.config import PREFIX

CATEGORY_ORDER = ["Música", "Basico"]


class General(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name='ping', help='pong?', extras={"category": "Basico"})
    async def pingpong(self, ctx):
        await ctx.send('pong')

    @commands.hybrid_command(name='hola', help='Saluda al usuario', extras={"category": "Basico"})
    async def saludar(self, ctx):
        await ctx.send(f'Hola {ctx.author.mention}!')

    @commands.hybrid_command(name="comandos", help="Muestra todos los comandos disponibles", extras={"category": "Basico"})
    async def help_custom(self, ctx):
        embed = discord.Embed(
            title="📋 Comandos del Bot",
            description=f"Usa `{PREFIX}comando` o `/comando`.",
            color=discord.Color.blue(),
        )

        categories = {}
        for command in sorted(self.bot.commands, key=lambda c: c.name):
            # "help" es el de serie de discord.py; "comandos" ya hace ese papel
            if command.hidden or command.name == "help":
                continue
            category = command.extras.get('category', 'Otros')
            categories.setdefault(category, []).append(f"`{PREFIX}{command.name}` - {command.help}")

        orden = CATEGORY_ORDER + sorted(c for c in categories if c not in CATEGORY_ORDER)
        for category in orden:
            if category in categories:
                embed.add_field(name=f"**{category}**", value="\n".join(categories[category]), inline=False)

        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(General(bot))
