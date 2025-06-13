import discord
from discord.ext import commands
import cv2
import numpy as np
import os
import io
from PIL import Image

class Magik(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def magik(self, ctx):
        if not ctx.message.attachments:
            await ctx.send("❌ Debes adjuntar una imagen para aplicar el efecto mágico.")
            return

        attachment = ctx.message.attachments[0]
        if not any(attachment.filename.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg']):
            await ctx.send("❌ El archivo debe ser una imagen (PNG, JPG o JPEG).")
            return

        # Descargar la imagen
        image_bytes = await attachment.read()
        image = Image.open(io.BytesIO(image_bytes))
        
        # Convertir la imagen a formato que OpenCV pueda manejar
        image_np = np.array(image)
        if image_np.shape[2] == 4:  # Si tiene canal alpha (RGBA)
            image_np = cv2.cvtColor(image_np, cv2.COLOR_RGBA2BGR)
        else:
            image_np = cv2.cvtColor(image_np, cv2.COLOR_RGB2BGR)

        # Aplicar el efecto magik
        height, width = image_np.shape[:2]
        map_x = np.zeros((height, width), dtype=np.float32)
        map_y = np.zeros((height, width), dtype=np.float32)

        center_x, center_y = width // 2, height // 2
        for y in range(height):
            for x in range(width):
                dx = x - center_x
                dy = y - center_y
                radius = np.sqrt(dx**2 + dy**2)
                
                if radius < min(width, height) / 3:
                    map_x[y, x] = center_x + dx * 1.2
                    map_y[y, x] = center_y + dy * 0.8
                else:
                    map_x[y, x] = x
                    map_y[y, x] = y

        distorted_img = cv2.remap(image_np, map_x, map_y, cv2.INTER_LINEAR)

        # Convertir la imagen distorsionada de vuelta a formato PIL
        distorted_img = cv2.cvtColor(distorted_img, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(distorted_img)

        # Guardar la imagen en un buffer
        with io.BytesIO() as image_binary:
            pil_image.save(image_binary, 'PNG')
            image_binary.seek(0)
            await ctx.send("✨ ¡Imagen magificada! ✨", file=discord.File(fp=image_binary, filename='magik.png'))

async def setup(bot):
    await bot.add_cog(Magik(bot))