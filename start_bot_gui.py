# start_bot_gui.py
import threading
import tkinter as tk
from tkinter import messagebox
import subprocess
import sys
import os
import psutil
import time
# Añadidos para system tray
import pystray
from PIL import Image, ImageDraw

class BotGUI:
    def __init__(self, master):
        self.master = master
        master.title("Discord Bot Controller")
        master.geometry("420x370")
        master.resizable(False, False)
        self.bot_process = None
        self.is_running = False
        self.bot_psutil = None
        # Solo modo oscuro
        self.bg_color = "#23272a"
        self.fg_color = "#f5f6fa"
        self.card_bg = "#2c2f33"
        self.accent = "#43b581"
        self.error = "#f04747"
        self.master.configure(bg=self.bg_color)

        # Header
        self.header = tk.Label(master, text="Discord Bot Controller", font=("Segoe UI", 15, "bold"), bg=self.bg_color, fg=self.fg_color)
        self.header.pack(pady=(10, 0))

        # Status Card
        self.status_frame = tk.Frame(master, bg=self.card_bg, bd=1, relief="solid")
        self.status_frame.pack(pady=10, padx=15, fill="x")
        self.status_label = tk.Label(self.status_frame, text="Estado: Bot detenido", fg=self.error, bg=self.card_bg, font=("Segoe UI", 12))
        self.status_label.pack(pady=5)

        # Resource Usage Card
        self.usage_frame = tk.Frame(master, bg=self.card_bg, bd=1, relief="solid")
        self.usage_frame.pack(pady=5, padx=15, fill="x")
        self.cpu_label = tk.Label(self.usage_frame, text="CPU: -", bg=self.card_bg, fg=self.fg_color, font=("Segoe UI", 10))
        self.cpu_label.pack(anchor="w", padx=10, pady=(5,0))
        self.mem_label = tk.Label(self.usage_frame, text="Memoria: -", bg=self.card_bg, fg=self.fg_color, font=("Segoe UI", 10))
        self.mem_label.pack(anchor="w", padx=10)
        self.uptime_label = tk.Label(self.usage_frame, text="Uptime: -", bg=self.card_bg, fg=self.fg_color, font=("Segoe UI", 10))
        self.uptime_label.pack(anchor="w", padx=10, pady=(0,5))

        # Gráfico de barras
        self.graph_frame = tk.Frame(master, bg=self.card_bg, bd=1, relief="solid")
        self.graph_frame.pack(pady=5, padx=15, fill="x")
        self.canvas = tk.Canvas(self.graph_frame, width=370, height=60, bg=self.card_bg, highlightthickness=0)
        self.canvas.pack(padx=10, pady=8)

        # Controls
        self.controls_frame = tk.Frame(master, bg=self.bg_color)
        self.controls_frame.pack(pady=5)
        self.toggle_btn = tk.Button(self.controls_frame, text="Iniciar Bot", command=self.toggle_bot, width=15, bg=self.accent, fg="white", font=("Segoe UI", 11, "bold"), relief="flat")
        self.toggle_btn.grid(row=0, column=0, padx=5)
        self.quit_btn = tk.Button(self.controls_frame, text="Salir", command=self.quit, width=10, bg=self.error, fg="white", font=("Segoe UI", 10), relief="flat")
        self.quit_btn.grid(row=0, column=1, padx=5)

        self.update_usage()

        self.tray_icon = None
        self.is_tray = False
        self.master.protocol("WM_DELETE_WINDOW", self.quit)
        self.master.bind('<Unmap>', self.on_minimize)

        # Iniciar el bot automáticamente al abrir la aplicación
        self.start_bot()

    def toggle_bot(self):
        if not self.is_running:
            self.start_bot()
        else:
            self.stop_bot()

    def start_bot(self):
        try:
            if getattr(sys, 'frozen', False):
                python_exe = sys.executable
                base_path = sys._MEIPASS if hasattr(sys, '_MEIPASS') else os.path.dirname(sys.executable)
            else:
                python_exe = sys.executable
                base_path = os.path.dirname(os.path.abspath(__file__))
            main_py = os.path.join(base_path, "main.py")
            creationflags = 0
            if os.name == 'nt':  # Solo en Windows
                creationflags = subprocess.CREATE_NO_WINDOW
            self.bot_process = subprocess.Popen([python_exe, main_py], cwd=base_path, creationflags=creationflags)
            self.is_running = True
            self.status_label.config(text="Estado: Bot en ejecución", fg=self.accent)
            self.toggle_btn.config(text="Detener Bot", bg=self.error)
            self.bot_psutil = psutil.Process(self.bot_process.pid)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo iniciar el bot: {e}")

    def stop_bot(self):
        if self.bot_process:
            self.bot_process.terminate()
            self.bot_process.wait()
            self.bot_process = None
            self.bot_psutil = None
        self.is_running = False
        self.status_label.config(text="Estado: Bot detenido", fg=self.error)
        self.toggle_btn.config(text="Iniciar Bot", bg=self.accent)
        self.cpu_label.config(text="CPU: -")
        self.mem_label.config(text="Memoria: -")
        self.uptime_label.config(text="Uptime: -")
        self.draw_graph(0, 0)

    def create_tray_icon(self):
        # Crear un icono simple
        image = Image.new('RGB', (64, 64), color=(67, 181, 129))
        d = ImageDraw.Draw(image)
        d.ellipse((16, 16, 48, 48), fill=(114, 137, 218))
        # Crear el menú solo con Restaurar y Salir
        def get_menu():
            return pystray.Menu(
                pystray.MenuItem("Restaurar", self.restore_window),
                pystray.MenuItem("Salir", self.quit_from_tray)
            )
        # Tooltip dinámico
        def update_tooltip():
            cpu = getattr(self, 'last_cpu', 0)
            mem = getattr(self, 'last_mem', 0)
            estado = "En ejecución" if self.is_running else "Detenido"
            icon.title = f"Bot: {estado}\nCPU: {cpu:.1f}%\nRAM: {mem:.1f} MB"
        # Crear el icono con on_click
        icon = pystray.Icon(
            "DiscordBot",
            image,
            "Discord Bot Controller",
            menu=get_menu(),
            on_click=self._on_tray_icon_click
        )
        icon.update_tooltip = update_tooltip
        return icon

    def _on_tray_icon_click(self, icon, item):
        # Restaurar solo si es click izquierdo
        import pystray._win32 as _win32
        if hasattr(_win32, 'WM_LBUTTONUP'):
            # Solo restaurar si es click izquierdo
            self.restore_window()
        else:
            # En otros sistemas, restaurar siempre
            self.restore_window()

    def on_minimize(self, event):
        if self.master.state() == 'iconic' and not self.is_tray:
            self.hide_to_tray()

    def hide_to_tray(self):
        self.is_tray = True
        self.master.withdraw()
        if not self.tray_icon:
            self.tray_icon = self.create_tray_icon()
            threading.Thread(target=self.tray_icon.run, daemon=True).start()
        # Actualizar tooltip periódicamente
        def tooltip_updater():
            while self.is_tray and self.tray_icon:
                if hasattr(self.tray_icon, 'update_tooltip'):
                    self.tray_icon.update_tooltip()
                time.sleep(1)
        threading.Thread(target=tooltip_updater, daemon=True).start()

    def restore_window(self, icon=None, item=None):
        self.is_tray = False
        self.master.after(0, self.master.deiconify)
        if self.tray_icon:
            self.tray_icon.stop()
            self.tray_icon = None

    def quit_from_tray(self, icon=None, item=None):
        self.master.after(0, self.quit)
        if self.tray_icon:
            self.tray_icon.stop()
            self.tray_icon = None

    def quit(self):
        if self.is_running:
            self.stop_bot()
        self.master.destroy()
        if self.tray_icon:
            self.tray_icon.stop()
            self.tray_icon = None

    def toggle_bot_from_tray(self, icon=None, item=None):
        self.master.after(0, self.toggle_bot)

    def update_usage(self):
        cpu = 0
        mem = 0
        uptime_str = "-"
        if self.is_running and self.bot_psutil:
            try:
                # Incluye el proceso principal y todos sus hijos
                procs = [self.bot_psutil] + self.bot_psutil.children(recursive=True)
                cpu = sum(p.cpu_percent(interval=0.1) for p in procs if p.is_running())
                mem = sum(p.memory_info().rss for p in procs if p.is_running()) / (1024*1024)
                uptime = time.time() - self.bot_psutil.create_time()
                mins, secs = divmod(int(uptime), 60)
                hours, mins = divmod(mins, 60)
                uptime_str = f"{hours}h {mins}m {secs}s"
                self.cpu_label.config(text=f"CPU: {cpu:.1f}%")
                self.mem_label.config(text=f"Memoria: {mem:.1f} MB")
                self.uptime_label.config(text=f"Uptime: {uptime_str}")
            except Exception:
                self.cpu_label.config(text="CPU: -")
                self.mem_label.config(text="Memoria: -")
                self.uptime_label.config(text="Uptime: -")
        else:
            self.cpu_label.config(text="CPU: -")
            self.mem_label.config(text="Memoria: -")
            self.uptime_label.config(text="Uptime: -")
        # Guardar para tooltip
        self.last_cpu = cpu
        self.last_mem = mem
        self.draw_graph(cpu, mem)
        self.master.after(1000, self.update_usage)

    def draw_graph(self, cpu, mem):
        self.canvas.delete("all")
        # CPU bar
        cpu_perc = min(max(cpu, 0), 100)
        cpu_bar_len = int(170 * cpu_perc / 100)
        self.canvas.create_rectangle(20, 10, 20+cpu_bar_len, 30, fill="#43b581", outline="")
        self.canvas.create_rectangle(20, 10, 190, 30, outline="#43b581", width=2)
        self.canvas.create_text(200, 20, text=f"CPU: {cpu_perc:.1f}%", fill=self.fg_color, font=("Segoe UI", 10, "bold"), anchor="w")
        # Mem bar (max 1024 MB visual)
        mem_bar_len = int(170 * min(mem, 1024) / 1024)
        self.canvas.create_rectangle(20, 40, 20+mem_bar_len, 60, fill="#7289da", outline="")
        self.canvas.create_rectangle(20, 40, 190, 60, outline="#7289da", width=2)
        self.canvas.create_text(200, 50, text=f"Mem: {mem:.1f} MB", fill=self.fg_color, font=("Segoe UI", 10, "bold"), anchor="w")

if __name__ == "__main__":
    root = tk.Tk()
    app = BotGUI(root)
    root.mainloop()
