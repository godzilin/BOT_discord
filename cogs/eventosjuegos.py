import discord
from discord.ext import commands, tasks
from datetime import datetime, timedelta
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
    avatar_url: str  # Añadimos el avatar

@dataclass
class GameState:
    """Estado de un juego"""
    active_players: Set[int] = field(default_factory=set)
    start_time: Optional[datetime] = None
    notification_message: Optional[discord.Message] = None
    tracking_start: Optional[datetime] = None

class EventosJuegos(commands.Cog):
    """Cog para manejar eventos de juegos y monitoreo de jugadores"""
    
    def __init__(self, bot):
        self.bot = bot
        self.roles_monitoreados = frozenset([631903790156480532, 777931594500407327])
        self.games_state: Dict[str, GameState] = {}  # Combina varios dictionaries en uno
        self.eventos_activos: Set[str] = set()
        self.last_check = discord.utils.utcnow()
        self.check_interval = 20
        
        # Configuración de canales
        self.channel_id = 792184660091338784
        self.notification_channel_id = 498474737563861004
        self.robuso_id = 430508168385134622
        
        # Iniciar tasks con intervalos optimizados
        self.check_games.change_interval(seconds=self.check_interval)
        self.check_scheduled_events.change_interval(minutes=1)
        self.check_games.start()
        self.check_scheduled_events.start()  # Iniciar la tarea de revisión de eventos

    async def get_monitored_players(self, guild) -> List[JugadorInfo]:
        """Obtiene lista de jugadores monitoreados con su información"""
        jugadores = []
        jugadores_procesados = set()
        
        # Crear cache de roles monitoreados para búsqueda más rápida
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
                    self._update_game_state(member.id, current_game)
                
        return jugadores

    def _get_current_game(self, member) -> Optional[str]:
        """Obtiene el juego actual de un miembro"""
        try:
            return next(
                (activity.name for activity in member.activities 
                 if isinstance(activity, (discord.Game, discord.Activity)) 
                 and activity.type == discord.ActivityType.playing),
                None
            )
        except Exception:
            return None

    def _update_game_state(self, member_id: int, current_game: str):
        """Actualiza el estado de un juego de manera eficiente"""
        # Obtener o crear estado del juego
        if current_game not in self.games_state:
            self.games_state[current_game] = GameState()
        
        game_state = self.games_state[current_game]
        game_state.active_players.add(member_id)
        
        # Actualizar tiempo de inicio si es necesario
        if not game_state.start_time and len(game_state.active_players) >= 2:
            game_state.start_time = discord.utils.utcnow()
        
        # Limpiar jugador de otros juegos
        for game, state in self.games_state.items():
            if game != current_game and member_id in state.active_players:
                state.active_players.discard(member_id)
                if not state.active_players:
                    del self.games_state[game]

    def _process_players_for_embed(self, jugadores: List[JugadorInfo]) -> Tuple[dict, List[str], discord.Color]:
        """Procesa jugadores para el embed y determina el color"""
        juegos = {}
        no_jugando = []
        
        for jugador in jugadores:
            if jugador.current_game:
                juegos.setdefault(jugador.current_game, []).append(jugador.display_name)
            else:
                no_jugando.append(jugador.display_name)

        # Determinar color basado en máximo de jugadores por juego
        color = discord.Color.red()
        if juegos:
            max_jugadores = max(len(players) for players in juegos.values())
            if max_jugadores >= 2:
                color = discord.Color.green()
            elif max_jugadores == 1:
                color = discord.Color.blue()

        return juegos, no_jugando, color

    async def _download_avatar(self, session: aiohttp.ClientSession, url: str) -> Optional[Image.Image]:
        """Descarga y prepara un avatar para combinar"""
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.read()
                    # Usar BytesIO para no escribir al disco
                    img = Image.open(io.BytesIO(data))
                    # Convertir a RGBA y resize para uniformidad
                    return img.convert('RGBA').resize((128, 128))
                return None
        except Exception:
            return None

    async def _create_combined_avatar(self, avatar_urls: List[str]) -> Optional[discord.File]:
        """Crea una imagen combinada de los avatares de manera eficiente"""
        if not avatar_urls:
            return None

        avatar_urls = avatar_urls[:4]  # Limitar a 4 avatares
        
        async with aiohttp.ClientSession() as session:
            # Usar gather para descargas paralelas
            avatars = await asyncio.gather(
                *[self._download_avatar(session, url) for url in avatar_urls],
                return_exceptions=True
            )
            
            # Filtrar errores y None
            avatars = [av for av in avatars if isinstance(av, Image.Image)]
            
            if not avatars:
                return None

            # Usar tamaños predefinidos para optimización
            SIZES = {
                1: ((128, 128), [(0, 0)]),
                2: ((256, 128), [(0, 0), (128, 0)]),
                3: ((256, 256), [(0, 0), (128, 0), (0, 128)]),
                4: ((256, 256), [(0, 0), (128, 0), (0, 128), (128, 128)])
            }
            
            size, positions = SIZES[len(avatars)]
            combined = Image.new('RGBA', size, (0, 0, 0, 0))
            
            # Combinar avatares
            for img, pos in zip(avatars, positions):
                combined.paste(img, pos, img)
            
            # Usar buffer optimizado
            buffer = io.BytesIO()
            combined.save(buffer, 'PNG', optimize=True)
            buffer.seek(0)
            
            return discord.File(buffer, 'combined_avatar.png')

    @commands.command(name="estado_juegos")
    async def check_current_games(self, ctx):
        """Muestra el estado actual de jugadores monitoreados"""
        try:
            jugadores = await self.get_monitored_players(ctx.guild)
            juegos, no_jugando, embed_color = self._process_players_for_embed(jugadores)
            jugadores_mostrados = set()  # Set para trackear jugadores ya mostrados

            # Primer embed para jugadores en juego
            embed_jugando = discord.Embed(
                title="🎮 Estado de Jugadores",
                description="Listado de jugadores con roles monitoreados\n─────────────────",
                color=embed_color,
                timestamp=datetime.utcnow()
            )

            # Añadir campos de juegos con avatares combinados
            hay_jugadores_activos = False
            for juego, jugadores_info in sorted(juegos.items(), key=lambda x: len(x[1]), reverse=True):
                titulo = f"{juego} ({len(jugadores_info)})"
                if len(jugadores_info) == 1:
                    titulo += " - ¡Falta 1 jugador para evento! 🔥"
                
                avatar_urls = []
                value = ""
                jugadores_en_juego = [j for j in jugadores if j.current_game == juego][:4]
                
                for jugador in jugadores_en_juego:
                    jugadores_mostrados.add(jugador.display_name)  # Añadir a mostrados
                    avatar_indicator = "🎮" if jugador.avatar_url else "•"
                    value += f"{avatar_indicator} {jugador.display_name}\n"
                    if jugador.avatar_url:
                        avatar_urls.append(jugador.avatar_url)
                
                if len(jugadores_info) > 4:
                    value += f"*...y {len(jugadores_info) - 4} más...*\n"

                embed_jugando.add_field(name=titulo, value=value, inline=False)
                hay_jugadores_activos = True

                if avatar_urls:
                    combined_avatar = await self._create_combined_avatar(avatar_urls)
                    if combined_avatar:
                        embed_jugando.set_image(url="attachment://combined_avatar.png")
                        await ctx.send(file=combined_avatar, embed=embed_jugando)
                        break  # Solo enviamos una vez el embed con jugadores activos

            # Si no hay jugadores activos, enviar el primer embed vacío
            if not hay_jugadores_activos:
                embed_jugando.add_field(
                    name="Sin jugadores activos",
                    value="*No hay jugadores en partida actualmente*",
                    inline=False
                )
                await ctx.send(embed=embed_jugando)

            # Segundo embed para jugadores no en juego
            no_jugando_filtrado = [nombre for nombre in no_jugando if nombre not in jugadores_mostrados]
            if no_jugando_filtrado:
                embed_no_jugando = discord.Embed(
                    title="😴 Jugadores Inactivos",
                    color=discord.Color.light_grey(),
                    timestamp=datetime.utcnow()
                )
                embed_no_jugando.add_field(
                    name=f"No jugando ({len(no_jugando_filtrado)})",
                    value="\n".join(f"• {nombre}" for nombre in sorted(no_jugando_filtrado)),
                    inline=False
                )
                await ctx.send(embed=embed_no_jugando)

        except Exception:
            await ctx.send("❌ Ocurrió un error al procesar el estado de jugadores")

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

    async def _notify_active_game(self, guild, juego: str, channel_id: int):
        """Notifica sobre un juego activo y pingea a Robuso si no está en el canal"""
        try:
            notification_channel = guild.get_channel(self.notification_channel_id)
            voice_channel = guild.get_channel(channel_id)
            if not notification_channel or not voice_channel:
                return

            # Comprobar si Robuso está en el canal de voz
            robuso = guild.get_member(self.robuso_id)
            should_ping = robuso and (
                not robuso.voice or 
                robuso.voice.channel.id != channel_id
            )

            # Guardar tiempo de inicio
            self.game_start_times[juego] = discord.utils.utcnow()

            # Crear embed de notificación
            embed = discord.Embed(
                title="🎮 ¡Partida en curso!",
                description=f"Hay una partida de **{juego}** en marcha\n─────────────────",
                color=discord.Color.green(),
                timestamp=self.game_start_times[juego]
            )
            embed.add_field(
                name="Estado",
                value="✅ Partida activa",
                inline=False
            )
            embed.add_field(
                name="Inicio",
                value=f"<t:{int(self.game_start_times[juego].timestamp())}:R>",
                inline=True
            )

            # Añadir mención si es necesario
            content = f"<@{self.robuso_id}> ¡Únete a la partida!" if should_ping else None

            # Enviar o actualizar mensaje
            if juego in self.notification_messages:
                try:
                    await self.notification_messages[juego].edit(content=content, embed=embed)
                except discord.NotFound:
                    # Si el mensaje fue borrado, crear uno nuevo
                    self.notification_messages[juego] = await notification_channel.send(content=content, embed=embed)
            else:
                self.notification_messages[juego] = await notification_channel.send(content=content, embed=embed)
            
        except Exception:
            pass

    async def _update_game_ended(self, guild, juego: str):
        """Actualiza el mensaje de notificación cuando termina la partida"""
        try:
            if juego in self.notification_messages:
                end_time = discord.utils.utcnow()
                start_time = self.game_start_times.get(juego, end_time)
                duration = end_time - start_time

                embed = discord.Embed(
                    title="🎮 Partida finalizada",
                    description=f"La partida de **{juego}** ha terminado\n─────────────────",
                    color=discord.Color.red(),
                    timestamp=end_time
                )
                embed.add_field(
                    name="Estado",
                    value="❌ Partida terminada",
                    inline=False
                )
                embed.add_field(
                    name="Inicio",
                    value=f"<t:{int(start_time.timestamp())}:F>",
                    inline=True
                )
                embed.add_field(
                    name="Fin",
                    value=f"<t:{int(end_time.timestamp())}:F>",
                    inline=True
                )
                embed.add_field(
                    name="Duración",
                    value=f"{int(duration.total_seconds() / 60)} minutos",
                    inline=True
                )

                try:
                    await self.notification_messages[juego].edit(content=None, embed=embed)
                except discord.NotFound:
                    pass  # Ignorar si el mensaje fue borrado
                
                # Limpiar tracking
                del self.notification_messages[juego]
                del self.game_start_times[juego]
                
        except Exception:
            pass

    async def end_game_event(self, guild, game_name: str):
        """Helper function para terminar eventos"""
        try:
            for event in guild.scheduled_events:
                if (event.name == f"¡Jugando {game_name}!" and 
                    event.status != discord.EventStatus.ended):
                    await event.edit(
                        status=discord.EventStatus.ended,
                        end_time=discord.utils.utcnow()
                    )
                    self.eventos_activos.discard(game_name)
                    self.notified_events.discard(game_name)
                    if game_name in self.eventos_tracking:
                        del self.eventos_tracking[game_name]
                    
                    # Actualizar mensaje de notificación
                    await self._update_game_ended(guild, game_name)
                    
        except Exception:
            pass

    @tasks.loop(seconds=20)  # Cambiado de minutes=1 a seconds=20
    async def check_games(self):
        current_time = discord.utils.utcnow()
        
        if (current_time - self.last_check).total_seconds() < self.check_interval:
            return
            
        self.last_check = current_time
        guild = self.bot.guilds[0]
        
        # Procesar todos los estados de juego de una vez
        for game_name, state in list(self.games_state.items()):
            # Verificar condiciones de juego activo
            is_active = len(state.active_players) >= 2
            
            if not is_active:
                if not state.tracking_start:
                    state.tracking_start = current_time
                elif (current_time - state.tracking_start).total_seconds() >= 900:
                    await self.end_game_event(guild, game_name)
            else:
                state.tracking_start = None
                if game_name not in self.eventos_activos:
                    await self._create_and_activate_event(guild, game_name)

    @tasks.loop(minutes=1)
    async def check_scheduled_events(self):
        """Revisa y activa los eventos programados cuando sea su hora"""
        try:
            current_time = discord.utils.utcnow()
            
            for guild in self.bot.guilds:
                try:
                    scheduled_events = guild.scheduled_events
                    
                    for event in scheduled_events:
                        if (event.status == discord.EventStatus.scheduled and 
                            event.start_time <= current_time):
                            try:
                                await event.edit(status=discord.EventStatus.active)
                            except (discord.Forbidden, discord.HTTPException):
                                pass
            
                except (discord.Forbidden, Exception):
                    pass
                
        except Exception:
            pass

    @check_scheduled_events.before_loop
    async def before_check_scheduled_events(self):
        """Espera a que el bot esté listo antes de iniciar la tarea"""
        await self.bot.wait_until_ready()

    def cog_unload(self):
        """Limpieza al descargar el cog"""
        self.check_games.cancel()
        self.check_scheduled_events.cancel()

async def setup(bot):
    await bot.add_cog(EventosJuegos(bot))