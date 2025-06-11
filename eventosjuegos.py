import discord
from discord.ext import commands, tasks
from datetime import datetime, timedelta
import asyncio
from typing import Dict, Set, Optional

class EventosJuegos(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.roles_monitoreados = frozenset([631903790156480532, 777931594500407327])  # Inmutable set
        self.jugadores_actuales: Dict[str, Set[int]] = {}
        self.eventos_activos: Set[str] = set()
        self.channel_id = 792184660091338784
        self.check_games.start()

    @commands.Cog.listener()
    async def on_presence_update(self, before, after):
        # Rápida comprobación inicial
        if not any(role.id in self.roles_monitoreados for role in after.roles):
            return

        # Optimización de la detección de juegos
        current_game = None
        for activity in after.activities:
            if (isinstance(activity, (discord.Game, discord.Activity)) and 
                activity.type == discord.ActivityType.playing):
                current_game = activity.name
                break

        if current_game:
            # Usar setdefault para reducir comprobaciones
            self.jugadores_actuales.setdefault(current_game, set()).add(after.id)
        
        # Limpiar juegos anteriores de manera eficiente
        for juego in list(self.jugadores_actuales):
            if juego != current_game:
                jugadores = self.jugadores_actuales[juego]
                jugadores.discard(after.id)
                if not jugadores:
                    del self.jugadores_actuales[juego]

    def get_next_15min_interval(self, current_time: datetime) -> datetime:
        minutes = current_time.minute
        next_15 = ((minutes // 15) + 1) * 15
        next_interval = current_time.replace(
            minute=0 if next_15 >= 60 else next_15,
            second=0, 
            microsecond=0
        )
        if next_15 >= 60:
            next_interval += timedelta(hours=1)
        return next_interval

    @tasks.loop(minutes=5)
    async def check_games(self):
        if not self.jugadores_actuales:
            return

        guild = self.bot.guilds[0]
        channel = guild.get_channel(self.channel_id)
        if not channel:
            return

        current_time = discord.utils.utcnow()
        start_time = self.get_next_15min_interval(current_time)
        end_time = start_time + timedelta(hours=2)

        for juego, jugadores in self.jugadores_actuales.items():
            if len(jugadores) >= 2 and juego not in self.eventos_activos:
                try:
                    await guild.create_scheduled_event(
                        name=f"¡Jugando {juego}!",
                        description="uníos perras",
                        start_time=start_time,
                        end_time=end_time,
                        entity_type=discord.EntityType.voice,
                        channel=channel,
                        privacy_level=discord.PrivacyLevel.guild_only
                    )
                    self.eventos_activos.add(juego)
                    
                    await asyncio.sleep(7200)
                    self.eventos_activos.discard(juego)
                except Exception as e:
                    print(f"Error en evento {juego}: {e}")

    @commands.command(name="estado_juegos")
    async def check_current_games(self, ctx):
        embed = discord.Embed(
            title="🎮 Estado de Juegos",
            color=discord.Color.green(),
            timestamp=datetime.utcnow()
        )

        # Optimización de la obtención de actividades
        current_activities = []
        for activity in ctx.author.activities:
            if hasattr(activity, 'name'):
                current_activities.append(activity.name)

        embed.add_field(
            name="🎯 Tu estado actual",
            value=f"Actividades: {', '.join(current_activities) if current_activities else 'Ninguna'}",
            inline=False
        )

        if not self.jugadores_actuales:
            embed.add_field(
                name="🎲 Juegos activos",
                value="No hay juegos siendo monitoreados actualmente.",
                inline=False
            )
        else:
            # Optimización de la obtención de nombres de usuarios
            for juego, jugadores in self.jugadores_actuales.items():
                nombres = []
                for uid in jugadores:
                    if user := self.bot.get_user(uid):
                        nombres.append(user.name)
                if nombres:
                    embed.add_field(
                        name=f"🎲 {juego}",
                        value=f"Jugadores: {', '.join(nombres)}",
                        inline=False
                    )

        await ctx.send(embed=embed)

    def cog_unload(self):
        self.check_games.cancel()

async def setup(bot):
    await bot.add_cog(EventosJuegos(bot))