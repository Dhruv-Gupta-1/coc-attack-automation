import os
import cv2
import numpy as np
from pathlib import Path
from typing import Optional, Tuple, List, Dict, Any
from PIL import Image, ImageGrab
import mss

ASSETS_DIR = Path(__file__).resolve().parent / "assets"
TEMPLATES_DIR = ASSETS_DIR / "templates"
TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)

class VisualTarget:
    def __init__(self, name: str, center_x: int, center_y: int, box: Tuple[int, int, int, int], confidence: float, source: str = "template"):
        self.name = name
        self.center_x = center_x
        self.center_y = center_y
        self.box = box # (x, y, w, h)
        self.confidence = confidence
        self.source = source

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "center": (self.center_x, self.center_y),
            "box": self.box,
            "confidence": round(self.confidence, 3),
            "source": self.source
        }

class VisionDetector:
    """
    ScreenScope Visual Detection Engine for Clash of Clans & Desktop Games.
    Dynamically locates target buttons, icons, and UI elements on screen
    WITHOUT hardcoded coordinates.
    """
    def __init__(self, templates_dir: Optional[Path] = None):
        self.templates_dir = templates_dir or TEMPLATES_DIR
        self.sct = mss.mss()
        self._cached_templates: Dict[str, np.ndarray] = {}
        self._attach_desktop()
        self.load_all_templates()

    def _attach_desktop(self):
        """Attaches the interactive desktop to current thread for reliable GDI screen grabs."""
        try:
            import ctypes
            user32 = ctypes.windll.user32
            hdesk = user32.OpenInputDesktop(0, False, 0x01FF)
            if hdesk:
                user32.SetThreadDesktop(hdesk)
        except Exception:
            pass

    def load_all_templates(self):
        """Preloads all PNG/JPG icon templates from disk."""
        self._cached_templates.clear()
        if not self.templates_dir.exists():
            return
        for file in self.templates_dir.glob("*.*"):
            if file.suffix.lower() in [".png", ".jpg", ".jpeg", ".bmp"]:
                name = file.stem.lower()
                img = cv2.imread(str(file), cv2.IMREAD_UNCHANGED)
                if img is not None:
                    self._cached_templates[name] = img

    def get_template_names(self) -> List[str]:
        return sorted(list(self._cached_templates.keys()))

    def capture_screen_bgr(self, region: Optional[Tuple[int, int, int, int]] = None) -> Tuple[np.ndarray, int, int]:
        """
        Captures screen as a BGR numpy array using mss with seamless fallback to PIL ImageGrab.
        Returns (bgr_img, offset_x, offset_y).
        """
        self._attach_desktop()
        
        if region:
            rx, ry, rw, rh = region
            rx, ry, rw, rh = int(rx), int(ry), int(rw), int(rh)
            monitor = {"left": rx, "top": ry, "width": rw, "height": rh}
            offset_x, offset_y = rx, ry
        else:
            try:
                mon = self.sct.monitors[1] if len(self.sct.monitors) > 1 else self.sct.monitors[0]
                monitor = mon
                offset_x, offset_y = mon["left"], mon["top"]
            except Exception:
                monitor = None
                offset_x, offset_y = 0, 0

        # Attempt 1: Fast mss grab
        if monitor:
            try:
                sct_img = self.sct.grab(monitor)
                bgr = np.array(sct_img, dtype=np.uint8)
                if bgr.shape[2] == 4:
                    bgr = cv2.cvtColor(bgr, cv2.COLOR_BGRA2BGR)
                return bgr, offset_x, offset_y
            except Exception:
                pass

        # Attempt 2: Bulletproof PIL ImageGrab fallback
        try:
            if region:
                bbox = (rx, ry, rx + rw, ry + rh)
                img = ImageGrab.grab(bbox=bbox, all_screens=True)
            else:
                img = ImageGrab.grab(all_screens=True)
            arr = np.array(img, dtype=np.uint8)
            bgr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
            return bgr, offset_x, offset_y
        except Exception as e:
            # Emergency blank canvas fallback if screen locked
            return np.zeros((600, 800, 3), dtype=np.uint8), offset_x, offset_y

    def find_icon(self, icon_name: str, region: Optional[Tuple[int, int, int, int]] = None,
                  threshold: float = 0.72, multi_scale: bool = True) -> Optional[VisualTarget]:
        """
        Finds a specific named icon on screen using multi-scale OpenCV template matching.
        Returns exact center point and bounding box on the desktop coordinate plane.
        """
        icon_name = icon_name.lower().strip()
        template = self._cached_templates.get(icon_name)
        if template is None:
            # Try reloading in case user added a new icon
            self.load_all_templates()
            template = self._cached_templates.get(icon_name)
            if template is None:
                return None

        screen_bgr, off_x, off_y = self.capture_screen_bgr(region)
        screen_gray = cv2.cvtColor(screen_bgr, cv2.COLOR_BGR2GRAY)

        # Handle template transparency (alpha mask)
        mask = None
        if len(template.shape) > 2 and template.shape[2] == 4:
            alpha = template[:, :, 3]
            mask = np.where(alpha > 128, 255, 0).astype(np.uint8)
            tpl_bgr = template[:, :, :3]
        else:
            tpl_bgr = template

        tpl_gray = cv2.cvtColor(tpl_bgr, cv2.COLOR_BGR2GRAY)
        th, tw = tpl_gray.shape[:2]

        scales = [1.0, 0.95, 1.05, 0.90, 1.10, 0.85, 1.15, 0.80, 1.20, 0.75, 1.25, 0.70, 0.65, 0.60, 0.55, 0.50] if multi_scale else [1.0]
        best_val = -1.0
        best_loc = None
        best_size = (tw, th)

        for s in scales:
            sw = int(tw * s)
            sh = int(th * s)
            if sw > screen_gray.shape[1] or sh > screen_gray.shape[0] or sw < 10 or sh < 10:
                continue

            scaled_tpl = cv2.resize(tpl_gray, (sw, sh), interpolation=cv2.INTER_AREA if s < 1.0 else cv2.INTER_LINEAR)
            
            if mask is not None:
                scaled_mask = cv2.resize(mask, (sw, sh), interpolation=cv2.INTER_NEAREST)
                res = cv2.matchTemplate(screen_gray, scaled_tpl, cv2.TM_CCORR_NORMED, mask=scaled_mask)
            else:
                res = cv2.matchTemplate(screen_gray, scaled_tpl, cv2.TM_CCOEFF_NORMED)

            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
            if max_val > best_val:
                best_val = max_val
                best_loc = max_loc
                best_size = (sw, sh)

        if best_val >= threshold and best_loc is not None:
            bx = off_x + best_loc[0]
            by = off_y + best_loc[1]
            bw, bh = best_size
            cx = bx + bw // 2
            cy = by + bh // 2
            return VisualTarget(icon_name, cx, cy, (bx, by, bw, bh), best_val, source="template")

        return None

    def find_any_icon(self, icon_names: List[str], region: Optional[Tuple[int, int, int, int]] = None,
                      threshold: float = 0.72) -> Optional[VisualTarget]:
        """Tries multiple candidate icon names and returns the highest confidence match."""
        best_target = None
        for name in icon_names:
            target = self.find_icon(name, region=region, threshold=threshold)
            if target:
                if best_target is None or target.confidence > best_target.confidence:
                    best_target = target
        return best_target

    def find_all_matching_icons(self, icon_name: str, region: Optional[Tuple[int, int, int, int]] = None,
                                threshold: float = 0.75, max_matches: int = 15) -> List[VisualTarget]:
        """
        Finds ALL occurrences of an icon on screen (e.g. all Gold/Elixir collector bubbles).
        """
        icon_name = icon_name.lower().strip()
        template = self._cached_templates.get(icon_name)
        if template is None:
            return []

        screen_bgr, off_x, off_y = self.capture_screen_bgr(region)
        screen_gray = cv2.cvtColor(screen_bgr, cv2.COLOR_BGR2GRAY)
        tpl_gray = cv2.cvtColor(template[:, :, :3] if template.shape[2] == 4 else template, cv2.COLOR_BGR2GRAY)
        th, tw = tpl_gray.shape[:2]

        res = cv2.matchTemplate(screen_gray, tpl_gray, cv2.TM_CCOEFF_NORMED)
        locs = np.where(res >= threshold)
        
        matches: List[VisualTarget] = []
        taken_centers = []

        for pt in zip(*locs[::-1]):
            cx = off_x + pt[0] + tw // 2
            cy = off_y + pt[1] + th // 2
            
            # Non-max suppression: skip if too close to an already found center
            too_close = False
            for ox, oy in taken_centers:
                if abs(cx - ox) < tw * 0.6 and abs(cy - oy) < th * 0.6:
                    too_close = True
                    break
            if not too_close:
                taken_centers.append((cx, cy))
                score = float(res[pt[1], pt[0]])
                matches.append(VisualTarget(icon_name, cx, cy, (off_x + pt[0], off_y + pt[1], tw, th), score, source="multi-template"))
                if len(matches) >= max_matches:
                    break

        return matches

    def find_green_button(self, region: Optional[Tuple[int, int, int, int]] = None,
                          min_area: int = 800) -> Optional[VisualTarget]:
        """
        Finds bright green action buttons (like Clash Attack / OK / Upgrade) by color segmentation.
        """
        screen_bgr, off_x, off_y = self.capture_screen_bgr(region)
        hsv = cv2.cvtColor(screen_bgr, cv2.COLOR_BGR2HSV)

        # Clash green button HSV range
        lower_green = np.array([35, 90, 80])
        upper_green = np.array([85, 255, 255])
        mask = cv2.inRange(hsv, lower_green, upper_green)

        # Morphological clean up
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        best_cnt = None
        best_area = 0

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area > min_area:
                x, y, w, h = cv2.boundingRect(cnt)
                # Check aspect ratio typical for buttons (width > height)
                aspect = float(w) / max(1, h)
                if 1.2 <= aspect <= 5.0 and area > best_area:
                    best_area = area
                    best_cnt = (x, y, w, h)

        if best_cnt:
            x, y, w, h = best_cnt
            cx = off_x + x + w // 2
            cy = off_y + y + h // 2
            return VisualTarget("green_button", cx, cy, (off_x + x, off_y + y, w, h), 0.88, source="color-detection")

        return None

    def find_yellow_button(self, region: Optional[Tuple[int, int, int, int]] = None,
                           min_area: int = 700) -> Optional[VisualTarget]:
        """
        Finds yellow action buttons (like Battle, Find a Match, Next) by color segmentation.
        """
        screen_bgr, off_x, off_y = self.capture_screen_bgr(region)
        hsv = cv2.cvtColor(screen_bgr, cv2.COLOR_BGR2HSV)

        # Yellow button HSV range (golden amber to bright yellow)
        lower_yellow = np.array([15, 100, 100])
        upper_yellow = np.array([34, 255, 255])
        mask = cv2.inRange(hsv, lower_yellow, upper_yellow)

        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        best_cnt = None
        best_area = 0

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area > min_area:
                x, y, w, h = cv2.boundingRect(cnt)
                aspect = float(w) / max(1, h)
                if 1.0 <= aspect <= 5.5 and area > best_area:
                    best_area = area
                    best_cnt = (x, y, w, h)

        if best_cnt:
            x, y, w, h = best_cnt
            cx = off_x + x + w // 2
            cy = off_y + y + h // 2
            return VisualTarget("yellow_button", cx, cy, (off_x + x, off_y + y, w, h), 0.85, source="yellow-color-detection")

        return None

    def find_red_button(self, region: Optional[Tuple[int, int, int, int]] = None,
                        min_area: int = 500) -> Optional[VisualTarget]:
        """
        Finds red buttons (like Surrender / End Battle) by color segmentation.
        """
        screen_bgr, off_x, off_y = self.capture_screen_bgr(region)
        hsv = cv2.cvtColor(screen_bgr, cv2.COLOR_BGR2HSV)

        # Red button HSV range (handles hue wrap around 0 / 180)
        mask1 = cv2.inRange(hsv, np.array([0, 110, 90]), np.array([10, 255, 255]))
        mask2 = cv2.inRange(hsv, np.array([170, 110, 90]), np.array([180, 255, 255]))
        mask = cv2.bitwise_or(mask1, mask2)

        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        best_cnt = None
        best_area = 0

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area > min_area:
                x, y, w, h = cv2.boundingRect(cnt)
                aspect = float(w) / max(1, h)
                if 1.0 <= aspect <= 5.5 and area > best_area:
                    best_area = area
                    best_cnt = (x, y, w, h)

        if best_cnt:
            x, y, w, h = best_cnt
            cx = off_x + x + w // 2
            cy = off_y + y + h // 2
            return VisualTarget("red_button", cx, cy, (off_x + x, off_y + y, w, h), 0.88, source="red-color-detection")

        return None

    def is_base_loaded(self, region: Optional[Tuple[int, int, int, int]] = None) -> bool:
        """
        Checks if clouds have cleared and an enemy base is currently loaded on screen.
        Returns True if base graphics/terrain are visible rather than white matchmaking clouds.
        """
        screen_bgr, _, _ = self.capture_screen_bgr(region)
        hsv = cv2.cvtColor(screen_bgr, cv2.COLOR_BGR2HSV)

        # Average saturation and value across center area
        h, w = hsv.shape[:2]
        center_crop = hsv[int(h * 0.25):int(h * 0.75), int(w * 0.25):int(w * 0.75)]
        mean_s = np.mean(center_crop[:, :, 1])
        mean_v = np.mean(center_crop[:, :, 2])

        # Clouds in CoC are very high brightness (V > 210) and near zero saturation (S < 35).
        # When base terrain appears, saturation increases substantially (mean S > 45).
        return mean_s > 40 and mean_v < 240

    def save_new_template(self, name: str, image_crop: Image.Image) -> Path:
        """Saves a cropped region as a new icon template."""
        clean_name = "".join(c for c in name.lower().replace(" ", "_") if c.isalnum() or c == "_")
        target_path = self.templates_dir / f"{clean_name}.png"
        image_crop.save(target_path, format="PNG")
        self.load_all_templates()
        return target_path
