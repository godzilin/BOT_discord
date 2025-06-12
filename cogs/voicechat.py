import discord
from discord.ext import commands
import asyncio
import json
import os
from functools import partial
import concurrent.futures
import yt_dlp
import re

QUEUE_DIR = 'u:/BOT_discord/json'
QUEUE_FILE = os.path.join(QUEUE_DIR, 'queue_data.json')
MAX_QUEUE_SIZE = 50

def is_url(text):
    url_pattern = re.compile(
        r'https?://'  # http:// or https://
        r'(?:(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+[A-Za-z]{2,6}|'  # domain
        r'localhost|'  # localhost
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$'
    )
    return bool(url_pattern.match(text))

YDL_OPTIONS = {
    'format': 'bestaudio/best',
    'quiet': True,
    'no_warnings': True,
    'default_search': 'ytsearch',
    'extract_flat': False,
    'age_limit': 0,
    'no_playlist': True,
    'socket_timeout': 30,
    'source_address': '0.0.0.0',
    'force-ipv4': True,
    'nocheckcertificate': True,
    'preferredcodec': 'mp3',
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }],
}

class VoiceChat(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.queue = []  # (url, ctx, title, duration)
        self.is_playing = False
        self._executor = None
        self._load_queue()

    @property
    def executor(self):
        if self._executor is None:
            self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=1, thread_name_prefix='yt_dlp')
        return self._executor

    def _save_queue(self):
        os.makedirs(QUEUE_DIR, exist_ok=True)
        data = {
            'queue': [(url, ctx.author.id if ctx else None, title, duration) 
                     for url, ctx, title, duration in self.queue],
        }
        try:
            with open(QUEUE_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f)
        except Exception:
            pass

    def _load_queue(self):
        if os.path.exists(QUEUE_FILE):
            try:
                with open(QUEUE_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.queue = [(url, None, title, duration) 
                            for url, _, title, duration in data.get('queue', [])]
            except Exception:
                self.queue = []
        else:
            self.queue = []

    def _update_queue_ctx(self, ctx):
        # Asignar el contexto real a los elementos de la cola que no lo tengan
        for i, (url, c) in enumerate(self.queue):
            if c is None:
                self.queue[i] = (url, ctx)

    async def _extract_info(self, url):
        try:
            loop = asyncio.get_event_loop()
            future = loop.run_in_executor(
                self.executor,
                lambda: yt_dlp.YoutubeDL(YDL_OPTIONS).extract_info(url, download=False)
            )
            info = await asyncio.wait_for(future, timeout=10.0)
            if info.get('age_limit', 0) > 0:
                raise Exception("❌ Este video tiene restricción de edad")
            return info
        except asyncio.TimeoutError:
            raise Exception("La extracción tardó demasiado tiempo")
        except Exception as e:
            error_msg = str(e)
            if "Sign in to confirm your age" in error_msg:
                raise Exception("❌ Este video tiene restricción de edad")
            raise Exception(f"Error al extraer información: {error_msg}")

    def cog_unload(self):
        """Cleanup cuando el cog es descargado"""
        if self._executor:
            self._executor.shutdown(wait=False)
        
    @commands.command(name='join', help='El bot se une a tu canal de voz actual.')
    async def join(self, ctx):
        if ctx.author.voice and ctx.author.voice.channel:
            channel = ctx.author.voice.channel
            await channel.connect()
            await ctx.send(f'🔊 Me he unido a {channel.mention}')
        else:
            await ctx.send('❌ Debes estar en un canal de voz para usar este comando.')

    @commands.command(name='kys', help='El bot sale del canal de voz.')
    async def kys(self, ctx):
        if ctx.voice_client:
            await ctx.voice_client.disconnect()
            await ctx.send('👋 Me he salido del canal de voz.')
        else:
            await ctx.send('❌ No estoy en ningún canal de voz.')
        self.queue.clear()
        self.is_playing = False
        self._save_queue()

    @commands.command(name='musica', help='Reproduce música. Puedes usar un enlace de YouTube o escribir el nombre de la canción.')
    async def musica(self, ctx, *, query: str):
        if not ctx.author.voice or not ctx.author.voice.channel:
            await ctx.send('❌ Debes estar en un canal de voz para usar este comando.')
            return

        if len(self.queue) >= MAX_QUEUE_SIZE:
            await ctx.send('❌ La cola está llena. Espera a que termine alguna canción.')
            return

        try:
            # Si no es URL, convertir a búsqueda de YouTube
            if not is_url(query):
                await ctx.send(f'🔍 Buscando: "{query}"...')
                search_url = f"ytsearch1:{query}"
            else:
                search_url = query

            try:
                info = await asyncio.wait_for(self._extract_info(search_url), timeout=15.0)
            except asyncio.TimeoutError:
                await ctx.send('❌ La búsqueda está tardando demasiado tiempo. Por favor, inténtalo de nuevo.')
                return
            except Exception as e:
                await ctx.send(f'❌ Error: {str(e)}')
                return

            # Si es resultado de búsqueda, tomar el primer resultado
            if 'entries' in info:
                if not info['entries']:
                    await ctx.send('❌ No se encontraron resultados.')
                    return
                info = info['entries'][0]

            # Procesar el video
            title = info.get('title', 'Desconocido')
            duration = info.get('duration', 0)
            webpage_url = info.get('webpage_url', info.get('url', search_url))

            # Formatear duración
            h = duration // 3600
            m = (duration % 3600) // 60
            s = duration % 60
            dur_str = f"{h:02}:{m:02}:{s:02}"

            # Conectar al canal de voz si es necesario
            try:
                if not ctx.voice_client:
                    await ctx.author.voice.channel.connect()
                elif ctx.voice_client.channel != ctx.author.voice.channel:
                    await ctx.voice_client.move_to(ctx.author.voice.channel)
            except Exception as e:
                await ctx.send('❌ Error al conectar al canal de voz. Inténtalo de nuevo.')
                return

            if not self.is_playing:
                await self._play_audio(ctx, webpage_url)
                await ctx.send(f'🎶 Reproduciendo [{title}]({webpage_url}) `{dur_str}`')
            else:
                self.queue.append((webpage_url, ctx, title, duration))
                self._save_queue()
                pos = len(self.queue)
                await ctx.send(f'⏳ Añadido a la cola [{title}]({webpage_url}) `{dur_str}` (Posición: {pos})')

        except Exception as e:
            await ctx.send(f'❌ Error inesperado: {str(e)}')

    async def _play_audio(self, ctx, url):
        try:
            info = await self._extract_info(url)
            # Usar el stream directo (opus/webm) si está disponible
            audio_url = info.get('url')
            play_title = info.get('title', 'Desconocido')
            video_url = info.get('webpage_url', url)
            duration = info.get('duration', 0)

            self.current_info = {
                'title': play_title,
                'duration': duration,
                'webpage_url': video_url,
                'start_time': asyncio.get_event_loop().time()
            }

            self.is_playing = True

            def after_playing(error=None):
                if error:
                    print(f"Error en la reproducción: {str(error)}")
                fut = asyncio.run_coroutine_threadsafe(self._handle_playback_end(ctx, error), ctx.bot.loop)
                try:
                    fut.result()
                except Exception as e:
                    print(f"Error en after_playing: {str(e)}")

            # Usar el stream directo (opus/webm) para máxima compatibilidad
            ffmpeg_options = {
                'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
                'options': '-vn'
            }
            audio_source = discord.PCMVolumeTransformer(
                discord.FFmpegPCMAudio(audio_url, **ffmpeg_options),
                volume=0.5
            )
            if ctx.voice_client:
                ctx.voice_client.play(audio_source, after=after_playing)
        except Exception as e:
            print(f"Error en _play_audio: {str(e)}")
            await ctx.send(f'❌ Error al reproducir el audio: {e}')
            self.is_playing = False
            await self._play_next(ctx)

    async def _handle_playback_end(self, ctx, error):
        if error:
            print(f"Error en reproducción: {str(error)}")
            self.is_playing = False
            await self._play_next(ctx)
            return
        
        self.is_playing = False
        await self._play_next(ctx)

    async def _play_next(self, ctx):
        if self.queue:
            next_url, next_ctx, _, _ = self.queue.pop(0)
            self._save_queue()
            await self._play_audio(next_ctx or ctx, next_url)
        else:
            self.is_playing = False
            self._save_queue()

    @commands.command(name='skip', help='Salta la canción actual y reproduce la siguiente de la cola.')
    async def skip(self, ctx):
        voice_client = ctx.voice_client
        if voice_client and voice_client.is_playing():
            voice_client.stop()
            await ctx.send('⏭️ Canción saltada.')
        else:
            await ctx.send('❌ No hay ninguna canción reproduciéndose.')

    @commands.command(name='resume', help='Reanuda la reproducción si está pausada.')
    async def resume(self, ctx):
        voice_client = ctx.voice_client
        if voice_client and voice_client.is_paused():
            voice_client.resume()
            await ctx.send('▶️ Reproducción reanudada.')
        else:
            await ctx.send('❌ No hay ninguna canción pausada.')

    @commands.command(name='cola', help='Muestra la cola de reproducción actual.')
    async def cola(self, ctx):
        if not self.queue and not self.is_playing:
            await ctx.send('📭 No hay ninguna canción en la cola.')
            return

        mensaje = ['```ml']
        mensaje.append('=== Cola de reproducción ===')

        # Mostrar canción actual
        if self.is_playing and hasattr(self, 'current_info'):
            title = self.current_info['title']
            duration = self.current_info['duration']
            h = duration // 3600
            m = (duration % 3600) // 60
            s = duration % 60
            dur_str = f"{h:02}:{m:02}:{s:02}"
            mensaje.append(f'\n"▶ Reproduciendo:"')
            mensaje.append(f'0. {title} [{dur_str}]')

        # Mostrar cola
        if self.queue:
            mensaje.append('\n"♪ En cola:"')
            for i, (_, _, title, duration) in enumerate(self.queue, 1):
                h = duration // 3600
                m = (duration % 3600) // 60
                s = duration % 60
                dur_str = f"{h:02}:{m:02}:{s:02}"
                mensaje.append(f'{i}. {title} [{dur_str}]')
                if i >= 10 and len(self.queue) > 10:
                    mensaje.append(f'\n... y {len(self.queue) - 10} canciones más ...')
                    break

        mensaje.append('```')

        # Añadir los links después del bloque de código
        links = []
        if self.is_playing and hasattr(self, 'current_info'):
            links.append(f'`0.` <{self.current_info["webpage_url"]}>')
        
        if self.queue:
            for i, (url, _, _, _) in enumerate(self.queue[:10], 1):
                links.append(f'`{i}.` <{url}>')

        # Enviar mensajes
        await ctx.send('\n'.join(mensaje))
        if links:
            await ctx.send('\n'.join(links))

async def setup(bot):
    await bot.add_cog(VoiceChat(bot))
