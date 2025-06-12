import discord
from discord.ext import commands, tasks
from datetime import datetime, time
import json
import os

class FlexionesDelGuille(commands.Cog):
    __slots__ = ('bot', 'guille_id', 'channel_id', 'start_date', 'data_file', 'data')

    def __init__(self, bot):
        self.bot = bot
        self.guille_id = 335099198221320192
        self.channel_id = 498474737563861004
        self.start_date = datetime(2025, 6, 8)  # Día 1
        self.data_file = os.path.join('json', 'flexiones_data.json')
        self.load_data()
        self.recordatorio_diario.start()
        self.check_confirmacion.start()

    def load_data(self):
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r') as f:
                    self.data = json.load(f)
            except Exception:
                self.data = {'last_reminder': None}
        else:
            self.data = {'last_reminder': None}

    def save_data(self):
        try:
            os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
            with open(self.data_file, 'w') as f:
                json.dump(self.data, f)
        except Exception:
            pass

    async def send_flexiones_reminder(self):
        days_passed = (datetime.now() - self.start_date).days + 1
        flexiones = days_passed
        channel = self.bot.get_channel(self.channel_id)
        today = datetime.now().strftime('%Y-%m-%d')
        if channel:
            await channel.send(
                f"<@{self.guille_id}> ¡ES HORA DE TUS FLEXIONES DIARIAS! 💪\n"
                f"Hoy es el día {days_passed}, así que toca hacer {flexiones} flexiones 🏋️‍♂️\n"
                f"¡Cada día más fuerte! 💪💪\n"
                f"Cuando termines, usa el comando `ºconfirmar_flexiones` para confirmar que las has hecho."
            )
            self.data['last_reminder'] = today
            self.data['confirmed'] = False
            self.save_data()

    @tasks.loop(time=time(hour=16))  # Se ejecuta todos los días a las 16:00
    async def recordatorio_diario(self):
        await self.send_flexiones_reminder()

    @tasks.loop(time=time(hour=23, minute=59))  # Se ejecuta todos los días a las 23:59
    async def check_confirmacion(self):
        today = datetime.now().strftime('%Y-%m-%d')
        if self.data.get('last_reminder') == today and not self.data.get('confirmed', False):
            channel = self.bot.get_channel(self.channel_id)
            if channel:
                await channel.send(f"<@{self.guille_id}> ¡NO HAS CONFIRMADO TUS FLEXIONES DE HOY! 😡 ¡Hazlas o atente a las consecuencias!")
            # Intentar enviar DM
            user = self.bot.get_user(self.guille_id)
            if user:
                try:
                    await user.send(
                        "¿Te crees que puedes escaquearte de las flexiones? Última advertencia... 😈",
                        embed=discord.Embed().set_image(url="https://media.tenor.com/2g6lQkU4QJwAAAAC/spongebob-spunch-bop.gif")
                    )
                except Exception:
                    pass
        # Resetear confirmación para el día siguiente
        self.data['confirmed'] = False
        self.save_data()

    @recordatorio_diario.before_loop
    async def before_reminder(self):
        await self.bot.wait_until_ready()

    @check_confirmacion.before_loop
    async def before_check(self):
        await self.bot.wait_until_ready()

    @commands.command(name="confirmar_flexiones")
    async def confirmar_flexiones(self, ctx):
        if ctx.author.id != self.guille_id:
            await ctx.send("Este comando solo puede usarlo Guille para confirmar sus flexiones.")
            return
        today = datetime.now().strftime('%Y-%m-%d')
        if self.data.get('last_reminder') == today:
            if not self.data.get('confirmed', False):
                self.data['confirmed'] = True
                self.save_data()
                await ctx.send("¡Flexiones confirmadas! Buen trabajo 💪")
            else:
                await ctx.send("Ya has confirmado tus flexiones hoy.")
        else:
            await ctx.send("No hay flexiones pendientes para hoy.")

    @commands.command(name="test_flexiones")
    @commands.has_permissions(administrator=True)
    async def test_flexiones(self, ctx):
        await self.send_flexiones_reminder()
        await ctx.send("Recordatorio de prueba enviado.")

    def cog_unload(self):
        self.recordatorio_diario.cancel()
        self.check_confirmacion.cancel()

async def setup(bot):
    await bot.add_cog(FlexionesDelGuille(bot))