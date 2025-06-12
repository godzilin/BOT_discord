import discord
from discord.ext import commands
import psutil
import time
import os

class Basico(commands.Cog):
    __slots__ = ('bot', 'start_time', 'last_command')
    def __init__(self, bot):
        self.bot = bot
        self.start_time = time.time()
        self.last_command = None

    @commands.Cog.listener()
    async def on_command(self, ctx):
        self.last_command = ctx.command.qualified_name

    @commands.command(name='hola', help='Saluda al usuario.')
    async def hola(self, ctx):
        await ctx.send(f'¡Hola, {ctx.author.display_name}! YO SOY JOVAANII JOTAUVE LAGARTIJA IGUANA LAGARTO.')

    def _get_status(self):
        return '🟢 Online'

    def _get_latency(self):
        return round(self.bot.latency * 1000)

    def _get_resources(self):
        proc = psutil.Process(os.getpid())
        cpu = proc.cpu_percent(interval=0.1)
        ram = proc.memory_info().rss / (1024*1024)  # MB
        return cpu, ram

    def _get_uptime(self):
        proc = psutil.Process(os.getpid())
        uptime_segundos = int(time.time() - proc.create_time())
        horas, resto = divmod(uptime_segundos, 3600)
        minutos, segundos = divmod(resto, 60)
        return f"{horas}h {minutos}m {segundos}s"

    def _get_last_command(self):
        return self.last_command if self.last_command else 'Ninguno'

    @commands.command(name='info', help='Muestra información básica del bot.')
    async def info(self, ctx):
        estado = '🟢 Online'
        latencia = self._get_latency()
        cpu, ram = self._get_resources()
        uptime = self._get_uptime()
        ultimo_cmd = self._get_last_command()

        embed = discord.Embed(title="🤖 Información del Bot", color=discord.Color.green())
        embed.add_field(name="Estado", value=estado, inline=False)
        embed.add_field(name="Latencia", value=f"🏓 {latencia} ms", inline=False)
        embed.add_field(name="CPU", value=f"🖥️ {cpu:.1f}%", inline=False)
        embed.add_field(name="RAM", value=f"💾 {ram:.1f} MB", inline=False)
        embed.add_field(name="Uptime", value=f"⏱️ {uptime}", inline=False)
        embed.add_field(name="Último comando", value=f"⌨️ {ultimo_cmd}", inline=False)
        embed.set_footer(text=f"Solicitado por {ctx.author.display_name}")
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Basico(bot))
