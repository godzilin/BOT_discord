import discord
from discord.ext import commands, tasks
import json
import os
from datetime import datetime

class Cumpleanos(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Cambia la ruta para guardar los cumpleaños en la carpeta json
        self.birthdays_file = os.path.join("json", "birthdays.json")
        self.birthdays = self.cargar_cumpleanos()
        self.check_birthdays.start()

    def cargar_cumpleanos(self):
        """Carga los cumpleaños desde el archivo JSON en la carpeta json."""
        try:
            if os.path.exists(self.birthdays_file):
                with open(self.birthdays_file, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error cargando cumpleaños: {e}")
        return {}

    def guardar_cumpleanos(self):
        """Guarda los cumpleaños en el archivo JSON en la carpeta json."""
        try:
            with open(self.birthdays_file, "w", encoding="utf-8") as f:
                json.dump(self.birthdays, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Error guardando cumpleaños: {e}")

    @commands.command(name="cumple", help="Registra tu cumpleaños. Ejemplo: ºcumple 10 5 2002")
    async def registrar_cumple(self, ctx, dia: int, mes: int, anio: int):
        """Permite a un usuario registrar su cumpleaños."""
        user_id = str(ctx.author.id)
        self.birthdays[user_id] = {
            "day": dia,
            "month": mes,
            "year": anio,
            "name": ctx.author.display_name
        }
        self.guardar_cumpleanos()
        await ctx.send(f"🎉 Cumpleaños registrado para {ctx.author.display_name}: {dia}/{mes}/{anio}")

    @commands.command(name="vercumple", help="Muestra tu cumpleaños registrado.")
    async def ver_cumple(self, ctx):
        user_id = str(ctx.author.id)
        if user_id in self.birthdays:
            b = self.birthdays[user_id]
            await ctx.send(f"🎂 Tu cumpleaños registrado es: {b['day']}/{b['month']}/{b['year']}")
        else:
            await ctx.send("No tienes cumpleaños registrado. Usa `ºcumple <día> <mes> <año>` para registrarlo.")

    @tasks.loop(hours=24)
    async def check_birthdays(self):
        """Comprueba si hoy es el cumpleaños de alguien y felicita."""
        today = datetime.now()
        for user_id, b in self.birthdays.items():
            if b["day"] == today.day and b["month"] == today.month:
                user = self.bot.get_user(int(user_id))
                if user:
                    try:
                        await user.send(f"🎉 ¡Feliz cumpleaños, {b['name']}! 🎉")
                    except Exception as e:
                        print(f"No se pudo enviar mensaje de cumpleaños a {b['name']}: {e}")

    @check_birthdays.before_loop
    async def before_check_birthdays(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(Cumpleanos(bot))