import discord
from discord.ext import commands, tasks
from datetime import datetime, time
import asyncio
import json
import os
from typing import Dict, Optional

class HorarioTrabajo(commands.Cog):
    __slots__ = ('bot', 'archivo_horarios', 'horarios', 'canal_default_name', 'dias_semana')
    
    DIAS_SEMANA = {
        0: 'lunes', 1: 'martes', 2: 'miercoles', 3: 'jueves', 
        4: 'viernes', 5: 'sabado', 6: 'domingo'
    }

    def __init__(self, bot):
        self.bot = bot
        self.archivo_horarios = os.path.join("json", "horarios.json")
        self.horarios: Dict = {}
        self.canal_default_name = "el-cónclave-de-los-racistas"
        self.dias_semana = self.DIAS_SEMANA
        self._ensure_json_dir()
        self.cargar_horarios()
        self.revisar_horarios.start()
    
    def _ensure_json_dir(self) -> None:
        """Asegura que existe el directorio json"""
        os.makedirs(os.path.dirname(self.archivo_horarios), exist_ok=True)
    
    def cog_unload(self):
        self.revisar_horarios.cancel()
        self.guardar_horarios()
    
    def cargar_horarios(self) -> None:
        if not os.path.exists(self.archivo_horarios):
            self.horarios = {}
            return
        
        try:
            with open(self.archivo_horarios, 'r', encoding='utf-8') as f:
                self.horarios = json.load(f)
        except Exception:
            self.horarios = {}
    
    def guardar_horarios(self) -> None:
        try:
            with open(self.archivo_horarios, 'w', encoding='utf-8') as f:
                json.dump(self.horarios, f, ensure_ascii=False)
        except Exception:
            pass
    
    @commands.command(name='horario', help='Establece tu horario de trabajo. Formato: ºhorario <día> HH:MM HH:MM #canal')
    async def establecer_horario(self, ctx, dia: str = None, entrada: str = None, salida: str = None, canal: discord.TextChannel = None):
        """
        Establece el horario de trabajo del usuario para un día específico.
        Formato: ºhorario lunes 09:00 17:30 #canal-trabajo
        Si no especificas canal, usará #el-cónclave-de-los-racistas por defecto.
        """
        # Verificar si se proporcionaron los argumentos necesarios
        if not dia or not entrada or not salida:
            embed = discord.Embed(
                title="❌ Argumentos Faltantes",
                description="Debes proporcionar el día, hora de entrada y salida.\n\n**Formato:** `ºhorario <día> HH:MM HH:MM #canal`\n**Ejemplo:** `ºhorario lunes 09:00 17:30 #trabajo`\n\n**Días válidos:** lunes, martes, miercoles, jueves, viernes, sabado, domingo\n\nSi no especificas canal, usaré **#el-cónclave-de-los-racistas** por defecto.",
                color=0xff0000
            )
            await ctx.send(embed=embed)
            return
        
        # Normalizar el día
        dia_normalizado = dia.lower().strip()
        dias_validos = ['lunes', 'martes', 'miercoles', 'jueves', 'viernes', 'sabado', 'domingo']
        
        if dia_normalizado not in dias_validos:
            embed = discord.Embed(
                title="❌ Día Inválido",
                description=f"**'{dia}'** no es un día válido.\n\n**Días válidos:** {', '.join(dias_validos)}",
                color=0xff0000
            )
            await ctx.send(embed=embed)
            return
        
        try:
            # Parsear las horas para validar el formato
            hora_entrada = datetime.strptime(entrada, '%H:%M').time()
            hora_salida = datetime.strptime(salida, '%H:%M').time()
            
            # Si no se especifica canal, usar #el-cónclave-de-los-racistas por defecto
            if canal:
                canal_notificaciones = canal
            else:
                # Buscar el canal por nombre
                canal_default = discord.utils.get(ctx.guild.channels, name="el-cónclave-de-los-racistas")
                canal_notificaciones = canal_default if canal_default else ctx.channel
            
            # Inicializar usuario si no existe
            user_id_str = str(ctx.author.id)
            if user_id_str not in self.horarios:
                self.horarios[user_id_str] = {}
            
            # Guardar el horario del usuario para el día específico
            self.horarios[user_id_str][dia_normalizado] = {
                'entrada': entrada,
                'salida': salida,
                'canal': canal_notificaciones.id,
                'nombre': ctx.author.display_name
            }
            
            # Guardar en archivo
            self.guardar_horarios()
            
            embed = discord.Embed(
                title="📅 Horario Establecido",
                description=f"**Día:** {dia_normalizado.capitalize()}\n**Entrada:** {entrada}\n**Salida:** {salida}\n**Canal de notificaciones:** {canal_notificaciones.mention}",
                color=0x00ff00
            )
            embed.set_footer(text=f"Usuario: {ctx.author.display_name}")
            
            await ctx.send(embed=embed)
            
        except ValueError:
            embed = discord.Embed(
                title="❌ Error de Formato",
                description="**Formato de hora incorrecto.**\n\nUsa el formato correcto: `ºhorario <día> HH:MM HH:MM #canal`\n**Ejemplo:** `ºhorario lunes 09:00 17:30 #trabajo`\n\n• Las horas deben estar en formato 24 horas\n• Usa dos dígitos para horas y minutos\n• Separa con dos puntos (:)",
                color=0xff0000
            )
            await ctx.send(embed=embed)
    
    @commands.command(name='ver_horario', help='Muestra tu horario semanal o el de otro usuario.')
    async def ver_horario(self, ctx, *, usuario: discord.Member = None):
        """Muestra el horario semanal del usuario especificado o del autor del comando."""
        target_user = usuario if usuario else ctx.author
        user_id_str = str(target_user.id)
        if user_id_str not in self.horarios or not self.horarios[user_id_str]:
            embed = discord.Embed(
                title="📅 Sin Horarios",
                description=f"{'No tienes' if target_user == ctx.author else f'{target_user.display_name} no tiene'} horarios establecidos.",
                color=0xffaa00
            )
            await ctx.send(embed=embed)
            return
        
        horarios_usuario = self.horarios[user_id_str]
        
        embed = discord.Embed(
            title=f"📅 Horario Semanal de {target_user.display_name}",
            color=0x0099ff
        )
        
        dias_ordenados = ['lunes', 'martes', 'miercoles', 'jueves', 'viernes', 'sabado', 'domingo']
        
        for dia in dias_ordenados:
            if dia in horarios_usuario:
                horario = horarios_usuario[dia]
                canal_notif = self.bot.get_channel(horario['canal'])
                canal_nombre = canal_notif.mention if canal_notif else "Canal no encontrado"
                
                embed.add_field(
                    name=f"📆 {dia.capitalize()}",
                    value=f"**Entrada:** {horario['entrada']}\n**Salida:** {horario['salida']}\n**Canal:** {canal_nombre}",
                    inline=True
                )
        
        if not embed.fields:
            embed.description = "No tienes horarios configurados para ningún día."
        
        embed.set_footer(text=f"Usuario: {ctx.author.display_name}")
        await ctx.send(embed=embed)
    
    @commands.command(name='borrar_horario', help='Borra tu horario de un día específico o toda la semana.')
    async def borrar_horario(self, ctx, dia: str = None):
        """Elimina el horario del usuario para un día específico o todos."""
        user_id_str = str(ctx.author.id)
        
        if user_id_str not in self.horarios:
            embed = discord.Embed(
                title="❌ Sin Horarios",
                description="No tienes horarios establecidos para eliminar.",
                color=0xff0000
            )
            await ctx.send(embed=embed)
            return
        
        if dia is None:
            # Borrar todos los horarios
            del self.horarios[user_id_str]
            self.guardar_horarios()
            embed = discord.Embed(
                title="🗑️ Todos los Horarios Eliminados",
                description="Todos tus horarios han sido eliminados correctamente.",
                color=0xff6600
            )
            await ctx.send(embed=embed)
        else:
            # Borrar horario específico
            dia_normalizado = dia.lower().strip()
            dias_validos = ['lunes', 'martes', 'miercoles', 'jueves', 'viernes', 'sabado', 'domingo']
            
            if dia_normalizado not in dias_validos:
                embed = discord.Embed(
                    title="❌ Día Inválido",
                    description=f"**'{dia}'** no es un día válido.\n\n**Días válidos:** {', '.join(dias_validos)}\n\nPara borrar todos los horarios usa: `ºborrar_horario`",
                    color=0xff0000
                )
                await ctx.send(embed=embed)
                return
            
            if dia_normalizado in self.horarios[user_id_str]:
                del self.horarios[user_id_str][dia_normalizado]
                # Si no quedan horarios, eliminar el usuario
                if not self.horarios[user_id_str]:
                    del self.horarios[user_id_str]
                self.guardar_horarios()
                embed = discord.Embed(
                    title="🗑️ Horario Eliminado",
                    description=f"Tu horario del **{dia_normalizado}** ha sido eliminado correctamente.",
                    color=0xff6600
                )
                await ctx.send(embed=embed)
            else:
                embed = discord.Embed(
                    title="❌ Sin Horario",
                    description=f"No tienes un horario establecido para el **{dia_normalizado}**.",
                    color=0xff0000
                )
                await ctx.send(embed=embed)
    
    @tasks.loop(minutes=1)  # Revisa cada minuto
    async def revisar_horarios(self):
        """Task que revisa los horarios y envía notificaciones."""
        ahora = datetime.now()
        hora_actual = ahora.time().replace(second=0, microsecond=0)  # Ignorar segundos y microsegundos
        dia_actual = self.dias_semana[ahora.weekday()]  # Obtener día actual
        
        for user_id_str, horarios_usuario in self.horarios.items():
            if dia_actual in horarios_usuario:
                horario = horarios_usuario[dia_actual]
                
                # Convertir strings a objetos time para comparar
                try:
                    hora_entrada = datetime.strptime(horario['entrada'], '%H:%M').time()
                    hora_salida = datetime.strptime(horario['salida'], '%H:%M').time()
                    
                    # Revisar entrada
                    if hora_entrada == hora_actual:
                        await self.enviar_notificacion_entrada(int(user_id_str), horario, dia_actual)
                    
                    # Revisar salida
                    elif hora_salida == hora_actual:
                        await self.enviar_notificacion_salida(int(user_id_str), horario, dia_actual)
                        
                except ValueError:
                    print(f"Error procesando horario para usuario {user_id_str}: formato de hora inválido")
    
    @revisar_horarios.before_loop
    async def antes_revisar_horarios(self):
        """Espera a que el bot esté listo antes de iniciar el task."""
        await self.bot.wait_until_ready()
    
    async def enviar_notificacion_entrada(self, user_id, horario, dia):
        """Envía notificación de entrada al trabajo."""
        try:
            canal = self.bot.get_channel(horario['canal'])
            if canal:
                embed = discord.Embed(
                    title="🏢 Inicio de Jornada",
                    description=f"robuso ha empezado su jornada laboral del **{dia}**",
                    color=0x00ff00,
                    timestamp=datetime.now()
                )
                embed.add_field(name="Día", value=dia.capitalize(), inline=True)
                embed.add_field(name="Hora de entrada", value=horario['entrada'], inline=True)
                embed.add_field(name="Hora de salida", value=horario['salida'], inline=True)
                embed.set_footer(text="¡Todos deseamos que te vaya genial y que los indios no toquen los huevos!")
                
                await canal.send(embed=embed)
        except Exception as e:
            print(f"Error enviando notificación de entrada: {e}")
    
    async def enviar_notificacion_salida(self, user_id, horario, dia):
        """Envía notificación de salida del trabajo."""
        try:
            canal = self.bot.get_channel(horario['canal'])
            if canal:
                embed = discord.Embed(
                    title="🏠 Fin de Jornada",
                    description=f"robuso ha terminado su jornada laboral del **{dia}**",
                    color=0xff6600,
                    timestamp=datetime.now()
                )
                embed.add_field(name="Día", value=dia.capitalize(), inline=True)
                embed.add_field(name="Hora de entrada", value=horario['entrada'], inline=True)
                embed.add_field(name="Hora de salida", value=horario['salida'], inline=True)
                embed.set_footer(text="¡Si no juega con vosotros es porque no os quiere!")
                
                await canal.send(embed=embed)
        except Exception as e:
            print(f"Error enviando notificación de salida: {e}")

# Función de setup para añadir el cog al bot
async def setup(bot):
    await bot.add_cog(HorarioTrabajo(bot))