import discord
from discord.ext import commands

# Clase de vista para los botones de prueba
class MyView(discord.ui.View):
    def __init__(self):
        # Asegúrate de que el timeout es None si quieres que los botones persistan indefinidamente
        # o un número de segundos si quieres que expiren.
        super().__init__(timeout=None) 
        print("DEBUG: MyView inicializada.") # Mensaje de depuración

    # Botón de prueba
    @discord.ui.button(label="Test", style=discord.ButtonStyle.green, custom_id="my_custom_button")
    async def testbutton(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Siempre haz un defer de la respuesta para evitar "Interacción Fallida"
        # antes de hacer operaciones que puedan tardar más de 3 segundos.
        await interaction.response.defer(ephemeral=False) # ephemeral=False para que la edición sea visible para todos
        print(f"DEBUG: Botón 'Test' pulsado por {interaction.user.name} ({interaction.user.id}).") # Mensaje de depuración
        try:
            # Edita el mensaje original para mostrar la respuesta
            await interaction.followup.edit_message(
                message_id=interaction.message.id,
                content=f"¡Testing completado por {interaction.user.display_name}! Los botones funcionan.",
                view=None # Deshabilita la vista (los botones) después de la interacción
            )
            print("DEBUG: Mensaje de test editado con éxito.") # Mensaje de depuración
        except Exception as e:
            print(f"ERROR: Fallo al editar el mensaje en el botón de test: {e}")
            import traceback
            traceback.print_exc()
            await interaction.followup.send("¡Ups! Hubo un error al procesar tu clic. Intenta de nuevo.", ephemeral=True)


# Clase del Cog de prueba
class Test(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        print("DEBUG: Cog Test inicializado.") # Mensaje de depuración

    # Comando de barra (slash command) para enviar la vista de botones
    # Los comandos de barra necesitan ser sincronizados.
    @discord.app_commands.command(name='testbotones', description='Envía un mensaje con botones de prueba.')
    async def testbotones(self, interaction: discord.Interaction):
        print(f"DEBUG: Comando /testbotones invocado por {interaction.user.name} ({interaction.user.id}).") # Mensaje de depuración
        # Enviar el mensaje con la vista de botones
        await interaction.response.send_message("¡Aquí está tu mensaje de prueba con botones!", view=MyView())
        print("DEBUG: Mensaje con botones enviado.") # Mensaje de depuración

# Función de setup para añadir el cog al bot
async def setup(bot):
    # Asegúrate de importar discord.app_commands si estás usando comandos de barra
    # No es necesario importarlo aquí si ya lo haces globalmente en main.py o si el comando está en commands.Cog
    await bot.add_cog(Test(bot))
    print("DEBUG: Cog Test añadido al bot.") # Mensaje de depuración

    # ¡IMPORTANTE! Sincronizar comandos de barra.
    # Esto SÓLO debe hacerse una vez cuando los comandos estén definidos y listos.
    # En un bot de producción, lo harías al inicio y solo cuando actualices comandos.
    # No lo hagas en cada 'setup' de un cog si el bot recarga cogs con frecuencia,
    # ya que puede causar ratelimits o retrasos.
    # Una buena práctica es tener un comando de "sincronizar" en tu cog principal (main.py)
    # que solo el dueño pueda usar, o hacerlo una vez manualmente al inicio del bot.
    # Por ahora, para pruebas, lo pondremos aquí:
    try:
        await bot.tree.sync()
        print("DEBUG: Comandos de barra sincronizados con éxito.")
    except Exception as e:
        print(f"ERROR: Fallo al sincronizar comandos de barra: {e}")
        import traceback
        traceback.print_exc()

