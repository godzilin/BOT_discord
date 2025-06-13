import os
import json
from datetime import datetime, timedelta
import discord
from discord.ext import commands, tasks
import asyncio
from typing import Dict, Set, List, Tuple, Optional
from dataclasses import dataclass, field
from PIL import Image
import io
import aiohttp

@dataclass
class JugadorInfo:
    """Clase para almacenar información de un jugador"""
    display_name: str
    current_game: Optional[str]
    avatar_url: str

@dataclass
class GameState:
    """Estado completo de un juego con persistencia"""
    active_players: Set[int] = field(default_factory=set)
    start_time: Optional[datetime] = None
    notification_message: Optional[discord.Message] = None
    tracking_start: Optional[datetime] = None
    event_id: Optional[int] = None
    last_update: Optional[datetime] = None
    player_names: List[str] = field(default_factory=list)

class EventosJuegosOptimizado(commands.Cog):
    """Cog optimizado para eventos de juegos con persistencia completa"""

    def __init__(self, bot):
        self.bot = bot

        # Configuración principal
        self.roles_monitoreados = frozenset([631903790156480532, 777931594500407327])
        self.EVENTS_FILE = "json/events_data.json"
        self.NOTIFICATION_CHANNEL = 498474737563861004
        self.channel_id = 792184660091338784
        self.notification_channel_id = 498474737563861004
        self.robuso_id = 430508168385134622

        # Estado unificado y optimizado
        self.games_state: Dict[str, GameState] = {}
        self.eventos_activos: Set[str] = set()

        # Cache optimizado para reducir API calls
        self._member_cache = {}
        self._last_member_update = {}
        self._avatar_cache = {}

        # Control de timing optimizado
        self.last_check = discord.utils.utcnow()
        self.check_interval = 30  # Incrementado para menor consumo
        self.cache_duration = 180  # 3 minutos de cache

        # Cargar estado persistente
        self.load_persistent_state()

        # Iniciar task principal optimizado
        self.unified_game_monitor.start()

    def load_persistent_state(self):
        """Carga el estado persistente optimizado"""
        try:
            if os.path.exists(self.EVENTS_FILE):
                with open(self.EVENTS_FILE, 'r') as f:
                    data = json.load(f)

                # Reconstruir estados de juego desde datos persistentes
                for guild_id, guild_events in data.get("active_events", {}).items():
                    for game_name, event_data in guild_events.items():
                        state = GameState()
                        state.event_id = event_data.get("event_id")
                        state.start_time = datetime.fromisoformat(event_data["start_time"]) if event_data.get("start_time") else None
                        state.player_names = event_data.get("player_names", [])
                        state.last_update = datetime.fromisoformat(event_data.get("last_update", datetime.utcnow().isoformat()))

                        self.games_state[game_name] = state
                        self.eventos_activos.add(game_name)

            else:
                self.events_data = {"active_events": {}}
                self.save_persistent_state()

        except Exception as e:
            print(f"Error loading persistent state: {e}")
            self.events_data = {"active_events": {}}

    def save_persistent_state(self):
        """Guarda el estado de manera optimizada (solo cuando hay cambios)"""
        try:
            os.makedirs(os.path.dirname(self.EVENTS_FILE), exist_ok=True)

            # Construir datos para guardar desde el estado actual
            save_data = {"active_events": {}}

            for guild in self.bot.guilds:
                guild_id = str(guild.id)
                guild_data = {}

                for game_name, state in self.games_state.items():
                    if state.event_id and len(state.active_players) > 0:
                        guild_data[game_name] = {
                            "event_id": state.event_id,
                            "start_time": state.start_time.isoformat() if state.start_time else None,
                            "last_update": datetime.utcnow().isoformat(),
                            "player_names": state.player_names,
                            "channel_message": {
                                "message_id": state.notification_message.id if state.notification_message else None,
                                "timestamp": datetime.utcnow().isoformat()
                            }
                        }

                if guild_data:
                    save_data["active_events"][guild_id] = guild_data

            with open(self.EVENTS_FILE, 'w') as f:
                json.dump(save_data, f, indent=2)

        except Exception as e:
            print(f"Error saving persistent state: {e}")

    async def get_monitored_players_cached(self, guild) -> List[JugadorInfo]:
        """Versión con cache optimizada para reducir procesamiento"""
        current_time = discord.utils.utcnow()
        cache_key = guild.id

        # Verificar cache
        if (cache_key in self._member_cache and 
            cache_key in self._last_member_update and
            (current_time - self._last_member_update[cache_key]).total_seconds() < self.cache_duration):
            return self._member_cache[cache_key]

        # Actualizar cache
        jugadores = []
        jugadores_procesados = set()

        # Cache de roles para búsqueda optimizada
        roles_cache = {role.id: role for role in guild.roles if role.id in self.roles_monitoreados}

        for member in guild.members:
            if any(role.id in roles_cache for role in member.roles):
                if member.id in jugadores_procesados:
                    continue

                current_game = self._get_current_game(member)
                avatar_url = member.display_avatar.url if member.display_avatar else None

                jugador = JugadorInfo(member.display_name, current_game, avatar_url)
                jugadores.append(jugador)
                jugadores_procesados.add(member.id)

                if current_game:
                    self._update_game_state_optimized(member.id, current_game, member.display_name)

        # Actualizar cache
        self._member_cache[cache_key] = jugadores
        self._last_member_update[cache_key] = current_time

        return jugadores

    def _get_current_game(self, member) -> Optional[str]:
        """Versión optimizada para obtener juego actual"""
        try:
            for activity in member.activities:
                if (isinstance(activity, (discord.Game, discord.Activity)) and 
                    activity.type == discord.ActivityType.playing):
                    return activity.name
            return None
        except Exception:
            return None

    def _update_game_state_optimized(self, member_id: int, current_game: str, display_name: str):
        """Actualización optimizada del estado de juego"""
        # Crear estado si no existe
        if current_game not in self.games_state:
            self.games_state[current_game] = GameState()

        state = self.games_state[current_game]

        # Actualizar jugadores activos
        state.active_players.add(member_id)
        if display_name not in state.player_names:
            state.player_names.append(display_name)

        # Configurar tiempo de inicio si es elegible
        if not state.start_time and len(state.active_players) >= 2:
            state.start_time = discord.utils.utcnow()

        # Limpiar de otros juegos (optimizado)
        for game, other_state in list(self.games_state.items()):
            if game != current_game and member_id in other_state.active_players:
                other_state.active_players.discard(member_id)
                if display_name in other_state.player_names:
                    other_state.player_names.remove(display_name)

                # Limpiar estados vacíos
                if not other_state.active_players:
                    if game in self.eventos_activos:
                        self.eventos_activos.discard(game)
                    del self.games_state[game]

        state.last_update = discord.utils.utcnow()

    async def create_game_embed_optimized(self, guild, game_name, players, is_ended=False):
        """Embed optimizado con menos procesamiento"""
        embed = discord.Embed(
            title="🎮 Estado de Jugadores" if not is_ended else "🎮 Partida Finalizada",
            description="Listado de jugadores con roles monitoreados\n─────────────────",
            color=discord.Color.red() if is_ended else discord.Color.green(),
            timestamp=discord.utils.utcnow()
        )

        if is_ended:
            state = self.games_state.get(game_name)
            if state and state.start_time:
                duration = discord.utils.utcnow() - state.start_time
                hours = int(duration.total_seconds() // 3600)
                minutes = int((duration.total_seconds() % 3600) // 60)

                embed.add_field(
                    name=f"{game_name} (Finalizado)",
                    value=f"⏱️ Duración: {hours}h {minutes}m\n👥 Jugadores: {len(players)}",
                    inline=False
                )
        else:
            player_list = "\n".join(f"🎮 {player}" for player in players[:10])
            if len(players) > 10:
                player_list += f"\n*...y {len(players) - 10} más...*"

            embed.add_field(
                name=f"{game_name} ({len(players)})",
                value=player_list or "*Sin jugadores activos*",
                inline=False
            )

        return embed

    async def _download_avatar_cached(self, session: aiohttp.ClientSession, url: str) -> Optional[Image.Image]:
        """Descarga de avatar con cache optimizada"""
        if url in self._avatar_cache:
            return self._avatar_cache[url]

        try:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.read()
                    img = Image.open(io.BytesIO(data)).convert('RGBA').resize((128, 128))

                    # Cache limitado (máximo 20 avatares)
                    if len(self._avatar_cache) >= 20:
                        # Remover el más antiguo
                        self._avatar_cache.pop(next(iter(self._avatar_cache)))

                    self._avatar_cache[url] = img
                    return img
        except Exception:
            pass
        return None

    async def _create_combined_avatar_optimized(self, avatar_urls: List[str]) -> Optional[discord.File]:
        """Versión optimizada de avatares combinados"""
        if not avatar_urls:
            return None

        avatar_urls = avatar_urls[:4]

        async with aiohttp.ClientSession() as session:
            avatars = await asyncio.gather(
                *[self._download_avatar_cached(session, url) for url in avatar_urls],
                return_exceptions=True
            )

            valid_avatars = [av for av in avatars if isinstance(av, Image.Image)]
            if not valid_avatars:
                return None

            # Configuraciones optimizadas predefinidas
            configs = {
                1: ((128, 128), [(0, 0)]),
                2: ((256, 128), [(0, 0), (128, 0)]),
                3: ((256, 256), [(0, 0), (128, 0), (0, 128)]),
                4: ((256, 256), [(0, 0), (128, 0), (0, 128), (128, 128)])
            }

            size, positions = configs[len(valid_avatars)]
            combined = Image.new('RGBA', size, (0, 0, 0, 0))

            for img, pos in zip(valid_avatars, positions):
                combined.paste(img, pos, img)

            buffer = io.BytesIO()
            combined.save(buffer, 'PNG', optimize=True, quality=85)
            buffer.seek(0)

            return discord.File(buffer, 'combined_avatar.png')

    async def _create_and_activate_event_unified(self, guild, game_name: str, players: List[str]):
        """Creación de evento unificada y optimizada"""
        try:
            # Verificar si ya existe evento activo
            state = self.games_state.get(game_name)
            if state and state.event_id:
                try:
                    event = discord.utils.get(await guild.fetch_scheduled_events(), id=state.event_id)
                    if event and not event.ended:
                        return event
                except discord.NotFound:
                    pass

            current_time = discord.utils.utcnow()
            start_time = current_time + timedelta(minutes=5)
            end_time = current_time + timedelta(hours=2)

            event = await guild.create_scheduled_event(
                name=f"🎮 {game_name} Session",
                description=f"Join us for a {game_name} gaming session! Active players: {len(players)}",
                start_time=start_time,
                end_time=end_time,
                entity_type=discord.EntityType.external,
                privacy_level=discord.PrivacyLevel.guild_only,
                location=game_name
            )

            # Actualizar estado
            if not state:
                state = GameState()
                self.games_state[game_name] = state

            state.event_id = event.id
            state.start_time = current_time

            # Enviar notificación optimizada
            await self._send_optimized_notification(guild, game_name, players, event)

            await event.start()
            self.eventos_activos.add(game_name)

            # Guardar estado persistente
            self.save_persistent_state()

            return event

        except Exception as e:
            print(f"Error creating unified event: {e}")
            return None

    async def _send_optimized_notification(self, guild, game_name: str, players: List[str], event):
        """Notificación optimizada con menos recursos"""
        try:
            channel = self.bot.get_channel(self.NOTIFICATION_CHANNEL)
            if not channel:
                return

            # Verificar si Robuso necesita ping
            robuso = guild.get_member(self.robuso_id)
            voice_channel = guild.get_channel(self.channel_id)
            should_ping = (robuso and voice_channel and 
                          (not robuso.voice or robuso.voice.channel.id != self.channel_id))

            embed = await self.create_game_embed_optimized(guild, game_name, players)

            # Añadir información del evento
            embed.add_field(
                name="📅 Evento",
                value=f"[Ver evento]({event.url})" if hasattr(event, 'url') else "Evento creado",
                inline=True
            )

            content = f"<@{self.robuso_id}> ¡Únete a la partida de {game_name}!" if should_ping else None

            message = await channel.send(content=content, embed=embed)

            # Actualizar estado con mensaje
            state = self.games_state[game_name]
            state.notification_message = message

        except Exception as e:
            print(f"Error sending notification: {e}")

    async def end_event_unified(self, guild, game_name: str):
        """Finalización unificada y optimizada de eventos"""
        try:
            state = self.games_state.get(game_name)
            if not state:
                return

            # Finalizar evento de Discord
            if state.event_id:
                try:
                    events = await guild.fetch_scheduled_events()
                    event = discord.utils.get(events, id=state.event_id)
                    if event and not event.ended:
                        await event.edit(status=discord.EventStatus.ended)
                except Exception:
                    pass

            # Enviar notificación de finalización
            channel = self.bot.get_channel(self.NOTIFICATION_CHANNEL)
            if channel:
                embed = await self.create_game_embed_optimized(guild, game_name, state.player_names, is_ended=True)
                await channel.send(embed=embed)

            # Limpiar estado
            self.eventos_activos.discard(game_name)
            if game_name in self.games_state:
                del self.games_state[game_name]

            # Actualizar persistencia
            self.save_persistent_state()

        except Exception as e:
            print(f"Error ending unified event: {e}")

    @tasks.loop(seconds=30)  # Optimizado a 30 segundos
    async def unified_game_monitor(self):
        """Task principal optimizado que combina todas las funciones de monitoreo"""
        try:
            current_time = discord.utils.utcnow()

            # Control de frecuencia optimizado
            if (current_time - self.last_check).total_seconds() < self.check_interval:
                return

            self.last_check = current_time

            for guild in self.bot.guilds:
                try:
                    # Obtener jugadores con cache
                    jugadores = await self.get_monitored_players_cached(guild)

                    # Procesar estados de juego de manera optimizada
                    active_games = {}
                    for jugador in jugadores:
                        if jugador.current_game:
                            if jugador.current_game not in active_games:
                                active_games[jugador.current_game] = []
                            active_games[jugador.current_game].append(jugador.display_name)

                    # Procesar cada juego activo
                    for game_name, players in active_games.items():
                        if len(players) >= 2:  # Mínimo 2 jugadores
                            if game_name not in self.eventos_activos:
                                await self._create_and_activate_event_unified(guild, game_name, players)

                        # Actualizar estado del juego
                        if game_name in self.games_state:
                            state = self.games_state[game_name]
                            state.player_names = players
                            state.last_update = current_time

                    # Limpiar juegos inactivos (optimizado)
                    for game_name in list(self.games_state.keys()):
                        if game_name not in active_games:
                            state = self.games_state[game_name]

                            if not state.tracking_start:
                                state.tracking_start = current_time
                            elif (current_time - state.tracking_start).total_seconds() >= 900:  # 15 minutos
                                await self.end_event_unified(guild, game_name)
                        else:
                            # Reset tracking si vuelve a estar activo
                            state = self.games_state[game_name]
                            state.tracking_start = None

                    # Limpiar mensajes antiguos (cada hora)
                    if current_time.minute == 0:
                        await self._cleanup_old_data(guild, current_time)

                except Exception as e:
                    print(f"Error processing guild {guild.name}: {e}")
                    continue

        except Exception as e:
            print(f"Error in unified_game_monitor: {e}")

    async def _cleanup_old_data(self, guild, current_time):
        """Limpieza optimizada de datos antiguos"""
        try:
            # Limpiar cache de miembros cada hora
            if guild.id in self._member_cache:
                del self._member_cache[guild.id]
                del self._last_member_update[guild.id]

            # Limpiar cache de avatares (mantener solo los 10 más recientes)
            if len(self._avatar_cache) > 10:
                keys_to_remove = list(self._avatar_cache.keys())[:-10]
                for key in keys_to_remove:
                    del self._avatar_cache[key]

        except Exception as e:
            print(f"Error in cleanup: {e}")

    @commands.command(name="estado_juegos")
    async def check_current_games_optimized(self, ctx):
        """Comando optimizado para mostrar estado de jugadores"""
        try:
            jugadores = await self.get_monitored_players_cached(ctx.guild)

            # Procesamiento optimizado
            juegos = {}
            no_jugando = []

            for jugador in jugadores:
                if jugador.current_game:
                    if jugador.current_game not in juegos:
                        juegos[jugador.current_game] = []
                    juegos[jugador.current_game].append(jugador)
                else:
                    no_jugando.append(jugador.display_name)

            # Determinar color
            color = discord.Color.red()
            if juegos:
                max_players = max(len(players) for players in juegos.values())
                color = discord.Color.green() if max_players >= 2 else discord.Color.blue()

            # Crear embed principal
            embed_main = discord.Embed(
                title="🎮 Estado de Jugadores",
                description="Listado de jugadores con roles monitoreados\n─────────────────",
                color=color,
                timestamp=discord.utils.utcnow()
            )

            # Añadir juegos activos
            has_active_games = False
            combined_avatar = None

            for juego, jugadores_info in sorted(juegos.items(), key=lambda x: len(x[1]), reverse=True):
                players_names = [j.display_name for j in jugadores_info]
                titulo = f"{juego} ({len(players_names)})"

                if len(players_names) == 1:
                    titulo += " - ¡Falta 1 jugador! 🔥"

                value = "\n".join(f"🎮 {name}" for name in players_names[:10])
                if len(players_names) > 10:
                    value += f"\n*...y {len(players_names) - 10} más...*"

                embed_main.add_field(name=titulo, value=value, inline=False)
                has_active_games = True

                # Crear avatar combinado solo para el primer juego con más jugadores
                if not combined_avatar and len(jugadores_info) >= 2:
                    avatar_urls = [j.avatar_url for j in jugadores_info[:4] if j.avatar_url]
                    if avatar_urls:
                        combined_avatar = await self._create_combined_avatar_optimized(avatar_urls)

            if not has_active_games:
                embed_main.add_field(
                    name="Sin jugadores activos",
                    value="*No hay jugadores en partida actualmente*",
                    inline=False
                )

            # Enviar embed principal
            if combined_avatar:
                embed_main.set_image(url="attachment://combined_avatar.png")
                await ctx.send(file=combined_avatar, embed=embed_main)
            else:
                await ctx.send(embed=embed_main)

            # Embed secundario para jugadores inactivos
            if no_jugando:
                embed_inactive = discord.Embed(
                    title="😴 Jugadores Inactivos",
                    color=discord.Color.light_grey(),
                    timestamp=discord.utils.utcnow()
                )

                value = "\n".join(f"• {name}" for name in sorted(no_jugando))
                embed_inactive.add_field(
                    name=f"No jugando ({len(no_jugando)})",
                    value=value,
                    inline=False
                )
                await ctx.send(embed=embed_inactive)

        except Exception as e:
            await ctx.send("❌ Error al procesar el estado de jugadores")
            print(f"Error in check_current_games_optimized: {e}")

    @unified_game_monitor.before_loop
    async def before_unified_monitor(self):
        """Preparación antes del loop principal"""
        await self.bot.wait_until_ready()

        # Restaurar eventos activos desde persistencia
        try:
            for guild in self.bot.guilds:
                for game_name, state in self.games_state.items():
                    if state.event_id:
                        self.eventos_activos.add(game_name)
        except Exception as e:
            print(f"Error restoring active events: {e}")

    def cog_unload(self):
        """Limpieza optimizada al descargar"""
        try:
            self.unified_game_monitor.cancel()
            self.save_persistent_state()

            # Limpiar caches
            self._member_cache.clear()
            self._last_member_update.clear()
            self._avatar_cache.clear()

        except Exception as e:
            print(f"Error during cog unload: {e}")

async def setup(bot):
    await bot.add_cog(EventosJuegosOptimizado(bot))