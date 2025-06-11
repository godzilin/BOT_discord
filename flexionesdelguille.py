import discord
from discord.ext import commands, tasks
from datetime import datetime, time
import json
import os

class FlexionesDelGuille(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.guille_id = 335099198221320192
        self.channel_id = 498474737563861004
        self.start_date = datetime(2025, 6, 8)  # Día 1
        self.data_file = 'flexiones_data.json'
        self.load_data()
        self.recordatorio_diario.start()

    def load_data(self):
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r') as f:
                    self.data = json.load(f)
            else:
                self.data = {'last_reminder': None}
        except Exception as e:
            print(f"Error cargando datos: {e}")
            self.data = {'last_reminder': None}

    def save_data(self):
        try:
            with open(self.data_file, 'w') as f:
                json.dump(self.data, f)
        except Exception as e:
            print(f"Error guardando datos: {e}")

    async def send_flexiones_reminder(self):
        days_passed = (datetime.now() - self.start_date).days + 1
        flexiones = days_passed
        
        channel = self.bot.get_channel(self.channel_id)
        if channel:
            await channel.send(
                f"<@{self.guille_id}> ¡ES HORA DE TUS FLEXIONES DIARIAS! 💪\n"
                f"Hoy es el día {days_passed}, así que toca hacer {flexiones} flexiones 🏋️‍♂️\n"
                f"¡Cada día más fuerte! 💪💪"
            )
            self.data['last_reminder'] = datetime.now().strftime('%Y-%m-%d')
            self.save_data()

    @tasks.loop(time=time(hour=16))  # Se ejecuta todos los días a las 16:00
    async def recordatorio_diario(self):
        await self.send_flexiones_reminder()

    @recordatorio_diario.before_loop
    async def before_reminder(self):
        await self.bot.wait_until_ready()

    @commands.command(name="test_flexiones")
    @commands.has_permissions(administrator=True)
    async def test_flexiones(self, ctx):
        """Comando de prueba para forzar el recordatorio de flexiones"""
        await self.send_flexiones_reminder()
        await ctx.send("Recordatorio de prueba enviado.")

    def cog_unload(self):
        self.recordatorio_diario.cancel()

async def setup(bot):
    await bot.add_cog(FlexionesDelGuille(bot))