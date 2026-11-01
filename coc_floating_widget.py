import tkinter as tk
from PIL import Image, ImageTk
from pathlib import Path
from typing import Optional, Callable

ASSETS_DIR = Path(__file__).resolve().parent / "assets"
LOGO_PATH = ASSETS_DIR / "coc_logo.png"

class CoCFloatingWidget(tk.Toplevel):
    """
    Always-On-Top Draggable CoC Floating Shortcut Widget.
    Hovers comfortably over Clash of Clans and full-screen games,
    allowing instant 1-click start/stop and dashboard access.
    """
    def __init__(self, master, on_toggle_dashboard: Callable, on_toggle_run: Callable):
        super().__init__(master)
        self.on_toggle_dashboard = on_toggle_dashboard
        self.on_toggle_run = on_toggle_run

        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.configure(bg="#000001")
        self.wm_attributes("-transparentcolor", "#000001")

        self.width = 68
        self.height = 68
        
        # Position in top-right area by default
        screen_w = self.winfo_screenwidth()
        pos_x = screen_w - 90
        pos_y = 120
        self.geometry(f"{self.width}x{self.height}+{pos_x}+{pos_y}")

        self.canvas = tk.Canvas(self, width=self.width, height=self.height,
                                bg="#000001", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self._load_icon()

        # Drag & drop state
        self.drag_start_x = 0
        self.drag_start_y = 0
        self.has_dragged = False

        self.canvas.bind("<ButtonPress-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_motion)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)
        self.canvas.bind("<Button-3>", self._on_right_click)

        # Context menu
        self.menu = tk.Menu(self, tearoff=0, bg="#0f172a", fg="#fbbf24",
                            activebackground="#f59e0b", activeforeground="#000000",
                            font=("Segoe UI", 9))
        self.menu.add_command(label="📊 Open CoC Commander", command=self.on_toggle_dashboard)
        self.menu.add_command(label="▶️ Start Automation", command=lambda: self.on_toggle_run(True))
        self.menu.add_command(label="⏹️ Stop Automation", command=lambda: self.on_toggle_run(False))
        self.menu.add_separator()
        self.menu.add_command(label="❌ Exit", command=master.destroy)

        self.is_running_state = False
        self._enforce_topmost()

    def _load_icon(self):
        try:
            if LOGO_PATH.exists():
                img = Image.open(LOGO_PATH).resize((self.width, self.height), Image.Resampling.LANCZOS)
                self.icon_photo = ImageTk.PhotoImage(img)
                self.canvas.create_image(self.width//2, self.height//2, image=self.icon_photo)
            else:
                self.canvas.create_oval(4, 4, self.width-4, self.height-4, fill="#b45309", outline="#fbbf24", width=3)
                self.canvas.create_text(self.width//2, self.height//2, text="CoC", fill="#ffffff", font=("Segoe UI", 12, "bold"))
        except Exception:
            pass

    def _on_press(self, event):
        self.drag_start_x = event.x
        self.drag_start_y = event.y
        self.has_dragged = False

    def _on_motion(self, event):
        dx = event.x - self.drag_start_x
        dy = event.y - self.drag_start_y
        if abs(dx) > 3 or abs(dy) > 3:
            self.has_dragged = True
        new_x = self.winfo_x() + dx
        new_y = self.winfo_y() + dy
        self.geometry(f"+{new_x}+{new_y}")

    def _on_release(self, event):
        if not self.has_dragged:
            # Clicked! Toggle dashboard
            self.on_toggle_dashboard()

    def _on_right_click(self, event):
        self.menu.post(event.x_root, event.y_root)

    def set_running_visual(self, running: bool):
        self.is_running_state = running
        # Optional indicator or border
        pass

    def _enforce_topmost(self):
        try:
            self.attributes("-topmost", True)
            self.lift()
        except Exception:
            pass
        self.after(2000, self._enforce_topmost)
