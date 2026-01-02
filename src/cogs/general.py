
import discord
from discord.ext import commands
from src.config import PREFIX

class General(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='ping', help='pong?', category='Basico')
    async def pingpong(self, ctx):
        await ctx.send('pong')

    @commands.command(name='hola', help='Saluda al usuario', category='Basico')
    async def saludar(self, ctx):
        await ctx.send(f'Hola {ctx.author.mention}!')

    @commands.command(name="comandos", help="Muestra todos los comandos disponibles")
    async def help_custom(self, ctx):
        embed = discord.Embed(title="📋 Comandos del Bot", color=discord.Color.blue())
        
        categories = {}
        for command in self.bot.commands:
            category = getattr(command, 'category', 'Sin categoría')
            if category not in categories:
                categories[category] = []
            categories[category].append(f"`{PREFIX}{command.name}` - {command.help}")
        
        for category, cmds in categories.items():
            embed.add_field(name=f"**{category}**", value="\n".join(cmds), inline=False)
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(General(bot))
