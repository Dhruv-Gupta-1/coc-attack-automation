import tkinter as tk
from tkinter import simpledialog, messagebox
from PIL import Image, ImageTk, ImageGrab
from typing import Optional, Callable
from pathlib import Path

class ScreenIconSnipper:
    """
    Interactive Screen Icon Snapper.
    Freezes the screen with a transparent overlay and allows the user to
    draw a bounding box around any icon or button in Clash of Clans to save it
    into the Vision Detector library.
    """
    def __init__(self, on_snip_completed: Optional[Callable[[str, Image.Image], None]] = None):
        self.on_snip_completed = on_snip_completed
        self.root: Optional[tk.Toplevel] = None
        self.canvas: Optional[tk.Canvas] = None
        
        self.start_x = 0
        self.start_y = 0
        self.rect_id = None
        self.screenshot: Optional[Image.Image] = None
        self.photo: Optional[ImageTk.PhotoImage] = None

    def start_snip(self, parent_window: Optional[tk.Tk] = None):
        if parent_window:
            parent_window.withdraw()
            parent_window.update()

        # Capture current screen
        self.screenshot = ImageGrab.grab()
        w, h = self.screenshot.size

        # Create borderless fullscreen overlay
        top = tk.Toplevel(parent_window) if parent_window else tk.Tk()
        self.root = top
        top.attributes("-fullscreen", True)
        top.attributes("-topmost", True)
        top.config(cursor="cross")

        self.canvas = tk.Canvas(top, width=w, height=h, highlightthickness=0, bg="black")
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # Dimmed background to highlight selection
        dimmed = self.screenshot.point(lambda p: int(p * 0.6))
        self.photo = ImageTk.PhotoImage(dimmed)
        self.canvas.create_image(0, 0, image=self.photo, anchor="nw")

        # Instructions banner
        banner = self.canvas.create_rectangle(w//2 - 260, 20, w//2 + 260, 65, fill="#0f172a", outline="#f59e0b", width=2)
        self.canvas.create_text(w//2, 42, text="📸 Drag a box over any CoC Icon or Button | Press ESC to Cancel",
                                font=("Segoe UI", 11, "bold"), fill="#fbbf24")

        self.canvas.bind("<ButtonPress-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", lambda e: self._on_release(parent_window))
        top.bind("<Escape>", lambda e: self._cancel(parent_window))

    def _on_press(self, event):
        self.start_x = event.x
        self.start_y = event.y
        if self.rect_id:
            self.canvas.delete(self.rect_id)
        self.rect_id = self.canvas.create_rectangle(
            self.start_x, self.start_y, self.start_x, self.start_y,
            outline="#f59e0b", width=3, dash=(4, 4)
        )

    def _on_drag(self, event):
        cur_x, cur_y = event.x, event.y
        self.canvas.coords(self.rect_id, self.start_x, self.start_y, cur_x, cur_y)

    def _on_release(self, parent_window: Optional[tk.Tk]):
        coords = self.canvas.coords(self.rect_id) if self.rect_id else None
        if not coords:
            self._cancel(parent_window)
            return

        x1, y1, x2, y2 = coords
        bx1 = int(min(x1, x2))
        by1 = int(min(y1, y2))
        bx2 = int(max(x1, x2))
        by2 = int(max(y1, y2))

        width = bx2 - bx1
        height = by2 - by1

        self.root.destroy()
        if parent_window:
            parent_window.deiconify()
            parent_window.lift()

        if width < 12 or height < 12:
            return # Too small to be an icon

        crop = self.screenshot.crop((bx1, by1, bx2, by2))

        # Ask user for a label / name for this icon
        name = simpledialog.askstring("Save Icon Template", "Enter a name for this icon (e.g., 'dragon_icon', 'hero_king', 'upgrade_btn'):")
        if name and name.strip():
            if self.on_snip_completed:
                self.on_snip_completed(name.strip(), crop)

    def _cancel(self, parent_window: Optional[tk.Tk]):
        if self.root:
            self.root.destroy()
        if parent_window:
            parent_window.deiconify()
            parent_window.lift()
