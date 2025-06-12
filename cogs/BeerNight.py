import discord        
from discord.ext import commands, tasks
import asyncio
import random
import datetime # Import datetime for time comparisons

class BeerNight(commands.Cog):
    __slots__ = ('bot', 'all_rules', 'active_rules', 'available_rules', 'reminder_task', 'end_timer_task', 'beer_night_start_time')
    def __init__(self, bot):
        self.bot = bot
        self.all_rules = [
            "Acabar top muertes = un trago",
            "Una triple = un trago",
            "Acabar top daños = bebes",
            "Si apelas de alguna manera a una etnia ajena para insultar a alguien del equipo = bebes",
            "Si te quejas de ir borracho = bebes",
            "Decir 'gg' o 'ez' = bebes",
            "Morir por caída = un trago extra",
            "Conseguir un 'ace' (Valorant) = el equipo contrario bebe",
            "Si te mata el mismo enemigo 3 veces seguidas = bebes 2 tragos",
            "Si un aliado te roba el 'kill' = el aliado bebe",
            "Ser el primero en morir = bebes",
            "Si un enemigo te hace 'emote' después de matarte = bebes",
            "Si pierdes una ronda importante = bebes",
            "Cada 1000 de daño = un trago",
            "Si fallas un ultimátum = bebes",
            "Conseguir un 'clutch' = el equipo contrario bebe"
        ]
        self.active_rules = []
        self.available_rules = []
        self.reminder_task = None
        self.end_timer_task = None
        self.beer_night_start_time = None

    async def _send_drink_reminder(self, ctx):
        while True:
            try:
                delay = random.uniform(0, 5)
                await asyncio.sleep(delay)
                await ctx.send("¡A BEBER! 🍻")
            except asyncio.CancelledError:
                break
            except Exception:
                break

    @commands.command(name="BeerNight")
    async def beer_night(self, ctx):
        if self.reminder_task and not self.reminder_task.done():
            await ctx.send("¡La Beer Night ya está en curso! Usa `ºendOfBeer` para terminarla o `ºmoreRules` para añadir otra regla.")
            return
        self.active_rules = []
        self.available_rules = list(self.all_rules)
        if not self.available_rules:
            await ctx.send("No hay reglas disponibles para iniciar la Beer Night.")
            return
        random_rule = self.available_rules.pop(random.randrange(len(self.available_rules)))
        self.active_rules.append(random_rule)
        await ctx.send(f"Empieza la noche del alcohol y el guarreo perras 🍻\n\n**Mandamientos divinos:**\n>>> {random_rule}")
        self.reminder_task = self.bot.loop.create_task(self._send_drink_reminder(ctx))
        self.beer_night_start_time = datetime.datetime.now()
        if self.end_timer_task:
            self.end_timer_task.cancel()
        self.end_timer_task = self.bot.loop.create_task(self._auto_end_beer_night(ctx.channel))

    async def _auto_end_beer_night(self, channel):
        time_to_wait = 7200
        if self.beer_night_start_time:
            elapsed_time = (datetime.datetime.now() - self.beer_night_start_time).total_seconds()
            time_to_wait = max(0, time_to_wait - elapsed_time)
        try:
            await asyncio.sleep(time_to_wait)
            if self.reminder_task:
                self.reminder_task.cancel()
                self.reminder_task = None
                self.active_rules = []
                self.available_rules = []
                await channel.send("El tiempo se ha acabado, ¡la Beer Night ha finalizado automáticamente! Que los efectos secundarios sean leves. 🤢")
                self.end_timer_task = None
        except asyncio.CancelledError:
            pass
        except Exception:
            pass

    @commands.command(name="endOfBeer")
    async def end_of_beer(self, ctx):
        if self.reminder_task:
            self.reminder_task.cancel()
            self.reminder_task = None
            self.active_rules = []
            self.available_rules = []
            await ctx.send("¡La Beer Night ha terminado! Que los efectos secundarios sean leves. 🤢")
            if self.end_timer_task:
                self.end_timer_task.cancel()
                self.end_timer_task = None
        else:
            await ctx.send("No hay ninguna Beer Night activa.")

    @commands.command(name="moreRules")
    async def more_rules(self, ctx):
        if not self.active_rules:
            await ctx.send("No hay una Beer Night activa para añadir más reglas. ¡Inicia una con `ºBeerNight`!")
            return
        if not self.available_rules:
            await ctx.send("¡No quedan normas por poner en esta sesión! ¡A cumplir las que ya hay! 😈")
            return
        new_rule = self.available_rules.pop(random.randrange(len(self.available_rules)))
        self.active_rules.append(new_rule)
        rules_text = "\n".join([f"- {rule}" for rule in self.active_rules])
        await ctx.send(f"¡Más reglas para la Beer Night! 🤯\n\n**Mandamientos Actuales:**\n>>> {rules_text}")

    def cog_unload(self):
        if self.reminder_task:
            self.reminder_task.cancel()
        if self.end_timer_task:
            self.end_timer_task.cancel()

async def setup(bot):
    await bot.add_cog(BeerNight(bot))