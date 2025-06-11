import discord
from discord.ext import commands
import traceback # Importamos traceback para mejor depuración de errores

# Cada cog debe ser una clase que herede de commands.Cog
class Basico(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        print("DEBUG: Cog Basico inicializado.") # Mensaje de depuración

    # Comando de ejemplo
    @commands.command(name='hola', help='Saluda al usuario.')
    async def hola(self, ctx):
        """Dice hola al usuario que lo invoca."""
        await ctx.send(f'¡Hola, {ctx.author.display_name}! YO SOY JOVAANII JOTAUVE LAGARTIJA IGUANA LAGARTO.')

    # Otro comando de ejemplo
    @commands.command(name='info', help='Muestra información básica del bot.')
    async def info(self, ctx):
        """Muestra la latencia del bot."""
        await ctx.send(f'Mi latencia es de {round(self.bot.latency * 1000)}ms.')


