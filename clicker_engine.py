import time
import math
import random
import win32gui
import win32con
import pygetwindow as gw
import pyautogui
from typing import Optional, Tuple, List, Callable

# Safety settings
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.05

class ClickerEngine:
    """
    ScreenWriter Screen Clicker & Input Actuator.
    Executes smooth humanized clicks, troop deployment, zooms, and window management
    strictly targeting dynamically detected icons on screen.
    """
    def __init__(self, on_log: Optional[Callable[[str], None]] = None):
        self.on_log = on_log or print
        self.is_running = False
        self.should_stop = False

    def log(self, msg: str):
        if self.on_log:
            self.on_log(f"[{time.strftime('%H:%M:%S')}] {msg}")

    def find_game_window(self, titles: Optional[List[str]] = None) -> Optional[gw.Win32Window]:
        """Finds active Clash of Clans or emulator window by partial title, strictly excluding web browsers and developer tools."""
        EXCLUDE_WORDS = ["brave", "chrome", "edge", "firefox", "visual studio", "code", "antigravity", "chat", "whatsapp", "terminal"]
        
        all_wins = gw.getAllWindows()
        
        # 1. First priority: Window whose title starts with 'Clash of Clans'
        for w in all_wins:
            if not w.title:
                continue
            t_low = w.title.lower().strip()
            if any(ex in t_low for ex in EXCLUDE_WORDS):
                continue
            if t_low.startswith("clash of clans"):
                return w

        # 2. Second priority: Explicit titles provided or emulator names
        if not titles:
            titles = ["clash of clans", "google play games", "bluestacks", "nox", "ldplayer", "mumu"]
        else:
            titles = [t.lower() for t in titles]

        for w in all_wins:
            if not w.title:
                continue
            t_low = w.title.lower().strip()
            if any(ex in t_low for ex in EXCLUDE_WORDS):
                continue
            for target in titles:
                if target in t_low:
                    return w
                    
        return None

    def bring_game_to_front(self, titles: Optional[List[str]] = None) -> Optional[Tuple[int, int, int, int]]:
        """
        Activates the game window, restores it if minimized, and brings it to the foreground.
        Uses Alt-key bypass to overcome Windows SetForegroundWindow restrictions.
        Returns (left, top, width, height) or None.
        """
        import ctypes
        user32 = ctypes.windll.user32
        
        win = self.find_game_window(titles)
        if not win:
            return None

        hwnd = win._hWnd
        try:
            # Unlock foreground window permissions using ALT key trick
            user32.keybd_event(0x12, 0, 0, 0) # Alt down
            if win32gui.IsIconic(hwnd):
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            else:
                win32gui.ShowWindow(hwnd, win32con.SW_SHOW)

            win32gui.BringWindowToTop(hwnd)
            win32gui.SetForegroundWindow(hwnd)
            user32.SwitchToThisWindow(hwnd, True)
            user32.keybd_event(0x12, 0, 2, 0) # Alt up
            time.sleep(0.35)
        except Exception as e:
            try:
                win.activate()
                time.sleep(0.3)
            except Exception:
                pass

        rect = win32gui.GetWindowRect(hwnd)
        l, t, r, b = rect
        w, h = r - l, b - t

        # Verify window is not minimized at negative coordinates
        if l < -5000 or w < 200 or h < 200:
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            time.sleep(0.5)
            rect = win32gui.GetWindowRect(hwnd)
            l, t, r, b = rect
            w, h = r - l, b - t

        return l, t, w, h

    def click_at(self, x: int, y: int, label: str = "", duration: float = 0.15, click_type: str = "single"):
        """
        Moves mouse and sends low-level Win32 hardware mouse events with hold delay,
        ensuring input registers in DirectX games and Google Play Games PC.
        """
        if self.should_stop:
            return

        import ctypes
        user32 = ctypes.windll.user32

        jitter_x = int(x + random.randint(-2, 2))
        jitter_y = int(y + random.randint(-2, 2))

        self.log(f"🖱️ Clicking {'[' + label + '] ' if label else ''}at ({jitter_x}, {jitter_y})")
        
        # Position cursor
        user32.SetCursorPos(jitter_x, jitter_y)
        time.sleep(0.04)

        if click_type == "double":
            user32.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            time.sleep(0.06)
            user32.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
            time.sleep(0.08)
            user32.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            time.sleep(0.06)
            user32.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
        else:
            # STRICT SINGLE CLICK: Press Down, hold 70-90ms for touch registration, Release Up
            user32.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            time.sleep(random.uniform(0.07, 0.09)) # Genuine hardware touch hold duration
            user32.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
            time.sleep(0.05)

    def zoom_out(self, center_x: int, center_y: int, ticks: int = 18):
        """Moves to center and scrolls down to zoom out to max view."""
        self.log(f"🔍 Zooming out max view at center ({center_x}, {center_y})...")
        import ctypes
        user32 = ctypes.windll.user32
        user32.SetCursorPos(int(center_x), int(center_y))
        time.sleep(0.1)

        for _ in range(abs(ticks)):
            if self.should_stop:
                break
            # Native Win32 mouse wheel event: WHEEL_DELTA is 120, negative is down
            user32.mouse_event(win32con.MOUSEEVENTF_WHEEL, 0, 0, -120, 0)
            pyautogui.scroll(-3)
            time.sleep(0.06)

    def deploy_troops_16_times(self, win_rect: Tuple[int, int, int, int], troop_name: str = "Troop", count: int = 16):
        """
        Clicks outside the red line repeatedly 16 times to deploy troops cleanly.
        Spreads clicks across 16 perimeter spots situated on the outer grass boundary outside the red line.
        """
        l, t, w, h = win_rect
        self.log(f"🐉 Deploying {count}x [{troop_name}] outside red line perimeter...")

        # 16 distinct perimeter coordinates situated on the outer grass boundary outside the red line
        outer_16_spots = [
            (0.18, 0.30),
            (0.24, 0.24),
            (0.32, 0.18),
            (0.42, 0.15),
            (0.52, 0.15),
            (0.62, 0.18),
            (0.72, 0.22),
            (0.80, 0.28),
            (0.84, 0.38),
            (0.84, 0.50),
            (0.82, 0.62),
            (0.74, 0.72),
            (0.62, 0.78),
            (0.50, 0.80),
            (0.36, 0.76),
            (0.24, 0.68)
        ]

        import ctypes
        user32 = ctypes.windll.user32

        for i in range(count):
            if self.should_stop:
                self.log(f"Deployment of [{troop_name}] stopped by user.")
                break
            rx, ry = outer_16_spots[i % len(outer_16_spots)]
            jx = int(l + rx * w) + random.randint(-4, 4)
            jy = int(t + ry * h) + random.randint(-4, 4)

            user32.SetCursorPos(jx, jy)
            time.sleep(0.02)
            user32.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            time.sleep(0.05)
            user32.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
            self.log(f"💥 [{troop_name}] {i+1}/{count} deployed outside red line at ({jx}, {jy})")
            time.sleep(0.10)

        self.log(f"✅ All {count} [{troop_name}] successfully deployed outside red line!")

    def deploy_dragons_16_times(self, win_rect: Tuple[int, int, int, int], count: int = 16):
        """Compatibility alias for deploy_troops_16_times."""
        self.deploy_troops_16_times(win_rect, troop_name="Dragon", count=count)

    def deploy_type_1_outside_red_line(self, win_rect: Tuple[int, int, int, int], duration_sec: float = 3.0):
        """
        Selects Troop Type 1 (slot 1) and clicks continuously outside
        the red line deployment perimeter for 3 seconds.
        """
        l, t, w, h = win_rect

        # 1. Click on Troop Type 1 (first slot in bottom battle dock)
        type_1_x = int(l + 0.08 * w)
        type_1_y = int(t + 0.925 * h)
        self.log(f"🗡️ Selecting Troop Type 1 at ({type_1_x}, {type_1_y})...")
        pyautogui.moveTo(type_1_x, type_1_y, duration=0.18)
        pyautogui.click()
        time.sleep(0.2)

        # 2. Continuous clicking outside red line perimeter for duration_sec (3.0s)
        self.log(f"💥 Deploying troops outside red line continuously for {duration_sec:.1f} seconds...")
        
        # Outer deployable grass tiles outside the red boundary
        outer_spots = [
            (0.16, 0.32),
            (0.26, 0.22),
            (0.42, 0.16),
            (0.58, 0.16),
            (0.74, 0.22),
            (0.84, 0.34),
            (0.84, 0.58),
            (0.74, 0.72),
            (0.52, 0.80),
            (0.28, 0.72),
            (0.16, 0.58),
            (0.14, 0.44)
        ]

        start_time = time.time()
        spot_idx = 0
        click_count = 0

        while (time.time() - start_time) < duration_sec:
            if self.should_stop:
                self.log("Deployment stopped by user.")
                break

            rx, ry = outer_spots[spot_idx % len(outer_spots)]
            jx = int(l + rx * w) + random.randint(-6, 6)
            jy = int(t + ry * h) + random.randint(-6, 6)

            pyautogui.moveTo(jx, jy, duration=0.04)
            pyautogui.click()
            click_count += 1
            spot_idx += 1
            time.sleep(0.06)

        self.log(f"✅ Troop deployment complete! Dispatched {click_count} clicks outside red line.")

    def deploy_troops_scatter(self, win_rect: Tuple[int, int, int, int], troop_count: int = 12):
        """
        Deploys troops around the village perimeter calculated dynamically
        from the game window bounds.
        """
        l, t, w, h = win_rect
        self.log(f"⚔️ Deploying {troop_count} troops around base perimeter...")

        # 12 deployment perimeter positions relative to current game window
        perimeter_ratios = [
            (0.18, 0.30),
            (0.30, 0.20),
            (0.50, 0.18),
            (0.70, 0.22),
            (0.82, 0.35),
            (0.84, 0.55),
            (0.72, 0.70),
            (0.50, 0.80),
            (0.30, 0.72),
            (0.16, 0.55),
            (0.12, 0.42),
            (0.22, 0.25)
        ]

        for i in range(min(troop_count, len(perimeter_ratios))):
            if self.should_stop:
                self.log("Deployment stopped by user.")
                break
            rx, ry = perimeter_ratios[i]
            dx = int(l + rx * w)
            dy = int(t + ry * h)
            
            pyautogui.moveTo(dx, dy, duration=0.15)
            pyautogui.click()
            time.sleep(random.uniform(0.15, 0.25))

    def wait_delay(self, seconds: float, reason: str = ""):
        """Waits while periodically checking for user stop signal."""
        if reason:
            self.log(f"⏳ Waiting {seconds:.1f}s — {reason}")
        
        step = 0.2
        elapsed = 0.0
        while elapsed < seconds:
            if self.should_stop:
                break
            time.sleep(step)
            elapsed += step
