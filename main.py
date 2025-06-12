import sys
import discord
from discord.ext import commands
import os
import traceback
import nacl as PyNacl
from dotenv import load_dotenv
from keep_alive import keep_alive

keep_alive()  # Inicia el servidor web para mantener el bot activo

# Define los intents necesarios para tu bot
intents = discord.Intents.default()
intents.message_content = True 
intents.members = True
intents.presences = True  # Añade esta línea

# Crea una instancia del bot con un prefijo para los comandos
bot = commands.Bot(command_prefix='º', intents=intents)

# Evento que se dispara cuando el bot está listo y conectado
@bot.event
async def on_ready():
    print(f'¡Bot conectado como {bot.user}!')
    print('Cargando extensiones...')
    
    # Lista de cogs que intentaremos cargar al inicio
    cogs_to_load = ['cogs.basico', 'cogs.cumpleanos', 'cogs.flexionesdelguille', 'cogs.eventosjuegos', 'cogs.BeerNight', 'cogs.robusotrabaja','cogs.voicechat']

    for cog in cogs_to_load:
        try:
            await bot.load_extension(cog)
            print(f'Cog "{cog}" cargado correctamente.✅')
        except Exception as e:
            print(f'Error al cargar el cog "{cog}": {e} ❌')

@bot.command(name="reload")
@commands.is_owner()
async def reload_cog(ctx, extension: str):
    """
    Recarga un cog en caliente. Ejemplo: ºreload cogs.basico
    """
    try:
        await bot.reload_extension(extension)
        await ctx.send(f'✅ Cog `{extension}` recargado correctamente.')
        print(f'Cog "{extension}" recargado correctamente.')
    except Exception as e:
        await ctx.send(f'❌ Error al recargar `{extension}`: {e}')
        print(f'Error al recargar el cog "{extension}": {e}')


load_dotenv()  # Carga las variables de entorno desde el archivo .env
token = os.getenv("DISCORD_TOKEN")  # Asegúrate de que tienes un archivo .env con tu token

if token:
    bot.run(token)
else:
    print("Error: No se proporcionó un token de Discord.")
    print("Por favor, asegúrate de que la variable 'token' contenga tu token de bot.")

    # --- Manejador de errores para los comandos ---
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.NotOwner):
        await ctx.send("🚫 ¡Pringao de los cojones, este comando solo puede ser usado por el dueño del bot, leete un librito máquina! 🚫")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"⚠️ ¡Error! Te falta un argumento. Revisa el uso del comando. Ejemplo: `{ctx.prefix}{ctx.command.name} <argumento>`")
    # Puedes añadir más tipos de errores aquí si los necesitas
    else:
        # Para otros errores no manejados, imprimirlos para depurar
        print(f"Error inesperado en el comando '{ctx.command}': {error}")
        # await ctx.send(f"Ha ocurrido un error inesperado al ejecutar el comando: {error}") # Opcional: para que el bot responda con el error

# --- Fin de comandos para gestionar cogs ---




