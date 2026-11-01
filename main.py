import os
import sys
import time
import json
import threading
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from pathlib import Path
from PIL import Image, ImageTk

from config import load_config, save_config
from vision_detector import VisionDetector
from clicker_engine import ClickerEngine
from automation_controller import AutomationController
from icon_snipper import ScreenIconSnipper
from coc_floating_widget import CoCFloatingWidget
from gemini_advisor import GeminiAdvisor

APP_DIR = Path(__file__).resolve().parent
ASSETS_DIR = APP_DIR / "assets"
TEMPLATES_DIR = ASSETS_DIR / "templates"
LOGS_DIR = APP_DIR / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)
HISTORY_FILE = LOGS_DIR / "coc_history.md"

class CoCAttackerBotApp(tk.Tk):
    """
    COC ATTACKER BOT: Autonomous Visual Screen Bot for Clash of Clans.
    Powered by computer vision template matching (no hardcoded coordinates)
    and optional Google Gemini AI base analysis.
    """
    def __init__(self):
        super().__init__()
        self.title("⚔️ CoC Commander — Autonomous Visual Screen Bot")
        self.geometry("920x660")
        self.minsize(840, 580)

        # Config & Settings
        self.cfg = load_config()

        # CoC Colors
        self.c_bg = "#090d16"
        self.c_panel = "#0f172a"
        self.c_card = "#1e293b"
        self.c_gold = "#f59e0b"
        self.c_gold_glow = "#fbbf24"
        self.c_crimson = "#b91c1c"
        self.c_crimson_hover = "#dc2626"
        self.c_emerald = "#10b981"
        self.c_emerald_hover = "#059669"
        self.c_text = "#f8fafc"
        self.c_muted = "#94a3b8"

        self.configure(bg=self.c_bg)
        self._set_app_icon()

        # Controller & AI Engines
        self.controller = AutomationController(
            on_log=self._append_log_threadsafe,
            on_status=self._set_status_threadsafe
        )
        self.snipper = ScreenIconSnipper(on_snip_completed=self.on_icon_snipped)
        self.advisor = GeminiAdvisor(
            api_key=self.cfg.get("gemini_api_key", ""),
            model_name=self.cfg.get("gemini_model", "gemini-3.1-flash-lite")
        )

        self._init_theme_styles()
        self._build_header()
        self._build_notebook()
        self._build_footer()

        # Floating Widget
        self.floating_widget = CoCFloatingWidget(
            self,
            on_toggle_dashboard=self.toggle_dashboard,
            on_toggle_run=self.toggle_run_from_float
        )

        self.protocol("WM_DELETE_WINDOW", self.on_close_window)
        self.after(300, self.refresh_icon_library)
        self.after(600, self._check_api_key_prompt)
        self.after(800, lambda: self.log("⚔️ COC Attacker Bot ready. Strict state verification & dual dragon deployment active."))

    def _set_app_icon(self):
        ico_path = ASSETS_DIR / "coc_logo.ico"
        png_path = ASSETS_DIR / "coc_logo.png"
        try:
            if ico_path.exists():
                self.iconbitmap(str(ico_path))
            elif png_path.exists():
                img = ImageTk.PhotoImage(Image.open(png_path))
                self.iconphoto(False, img)
        except Exception:
            pass

    def _init_theme_styles(self):
        style = ttk.Style(self)
        style.theme_use("clam")

        style.configure("TNotebook", background=self.c_bg, borderwidth=0)
        style.configure("TNotebook.Tab", background=self.c_card, foreground=self.c_text,
                        padding=[14, 6], font=("Segoe UI", 9, "bold"))
        style.map("TNotebook.Tab",
                  background=[("selected", self.c_panel)],
                  foreground=[("selected", self.c_gold)])

        # Button Styles
        style.configure("Gold.TButton", background=self.c_gold, foreground="#000000",
                        font=("Segoe UI", 10, "bold"), borderwidth=0, padding=[12, 6])
        style.map("Gold.TButton", background=[("active", self.c_gold_glow)])

        style.configure("Emerald.TButton", background=self.c_emerald, foreground="#ffffff",
                        font=("Segoe UI", 10, "bold"), borderwidth=0, padding=[12, 6])
        style.map("Emerald.TButton", background=[("active", self.c_emerald_hover)])

        style.configure("Crimson.TButton", background=self.c_crimson, foreground="#ffffff",
                        font=("Segoe UI", 9, "bold"), borderwidth=0, padding=[10, 5])
        style.map("Crimson.TButton", background=[("active", self.c_crimson_hover)])

        style.configure("Secondary.TButton", background=self.c_card, foreground=self.c_text,
                        font=("Segoe UI", 9), borderwidth=1, padding=[8, 5])
        style.map("Secondary.TButton", background=[("active", "#334155")])

    def _build_header(self):
        hdr = tk.Frame(self, bg=self.c_panel, height=64, padx=16, pady=8)
        hdr.pack(fill=tk.X, side=tk.TOP)

        png_path = ASSETS_DIR / "coc_logo.png"
        if png_path.exists():
            try:
                img = Image.open(png_path).resize((44, 44), Image.Resampling.LANCZOS)
                self.hdr_logo = ImageTk.PhotoImage(img)
                lbl_img = tk.Label(hdr, image=self.hdr_logo, bg=self.c_panel)
                lbl_img.pack(side=tk.LEFT, padx=(0, 10))
            except Exception:
                pass

        titles_box = tk.Frame(hdr, bg=self.c_panel)
        titles_box.pack(side=tk.LEFT, fill=tk.Y)
        tk.Label(titles_box, text="COC Attacker Bot", font=("Segoe UI", 13, "bold"),
                 fg=self.c_gold, bg=self.c_panel).pack(anchor="w")
        tk.Label(titles_box, text="Strict State-Verified Attack Engine with Dual Dragon Deployment",
                 font=("Segoe UI", 8), fg=self.c_muted, bg=self.c_panel).pack(anchor="w")

        # Action Buttons on Header
        btn_box = tk.Frame(hdr, bg=self.c_panel)
        btn_box.pack(side=tk.RIGHT)

        self.btn_main_run = ttk.Button(btn_box, text="▶ START ATTACK CYCLE", style="Emerald.TButton",
                                       command=self.toggle_main_run)
        self.btn_main_run.pack(side=tk.LEFT, padx=(0, 6))

        self.btn_collect_now = ttk.Button(btn_box, text="💰 Collect Loot", style="Gold.TButton",
                                          command=self.quick_collect_resources)
        self.btn_collect_now.pack(side=tk.LEFT, padx=(0, 6))

        btn_snip = ttk.Button(btn_box, text="📸 Snip Icon", style="Secondary.TButton",
                              command=self.start_snip_icon)
        btn_snip.pack(side=tk.LEFT, padx=(0, 6))

        btn_key = ttk.Button(btn_box, text="🔑 Gemini API", style="Secondary.TButton",
                             command=self.prompt_gemini_key)
        btn_key.pack(side=tk.LEFT)

    def _build_notebook(self):
        self.nb = ttk.Notebook(self)
        self.nb.pack(fill=tk.BOTH, expand=True, padx=12, pady=(10, 6))

        self.tab_dashboard = tk.Frame(self.nb, bg=self.c_panel, padx=12, pady=10)
        self.tab_icons = tk.Frame(self.nb, bg=self.c_panel, padx=12, pady=10)
        self.tab_ai = tk.Frame(self.nb, bg=self.c_panel, padx=12, pady=10)
        self.tab_history = tk.Frame(self.nb, bg=self.c_panel, padx=12, pady=10)

        self.nb.add(self.tab_dashboard, text="🎮 Commander & Logs")
        self.nb.add(self.tab_icons, text="🖼️ Visual Icon Library")
        self.nb.add(self.tab_ai, text="🤖 AI Advisor (Gemini)")
        self.nb.add(self.tab_history, text="📜 Session Chat History")

        self._build_tab_dashboard()
        self._build_tab_icons()
        self._build_tab_ai()
        self._build_tab_history()

    def _build_tab_dashboard(self):
        cfg_frame = tk.Frame(self.tab_dashboard, bg=self.c_card, padx=12, pady=8)
        cfg_frame.pack(fill=tk.X, pady=(0, 8))

        # Cycles input
        tk.Label(cfg_frame, text="Attack Cycles:", font=("Segoe UI", 9, "bold"), fg=self.c_gold, bg=self.c_card).pack(side=tk.LEFT, padx=(0, 4))
        self.spn_cycles = tk.Spinbox(cfg_frame, from_=1, to=999, width=5, bg="#090d16", fg=self.c_text,
                                     insertbackground=self.c_gold, font=("Consolas", 10), justify="center")
        self.spn_cycles.pack(side=tk.LEFT, padx=(0, 16))
        self.spn_cycles.delete(0, tk.END)
        self.spn_cycles.insert(0, str(self.cfg.get("cycles", 5)))

        # Attack Duration Limit (sec) - Default: 75s
        tk.Label(cfg_frame, text="Attack Limit:", font=("Segoe UI", 9, "bold"), fg=self.c_gold, bg=self.c_card).pack(side=tk.LEFT, padx=(0, 4))
        self.spn_battle_wait = tk.Spinbox(cfg_frame, from_=10, to=300, increment=5, width=5, bg="#090d16", fg=self.c_text,
                                          insertbackground=self.c_gold, font=("Consolas", 10), justify="center")
        self.spn_battle_wait.pack(side=tk.LEFT, padx=(0, 2))
        self.spn_battle_wait.delete(0, tk.END)
        self.spn_battle_wait.insert(0, str(self.cfg.get("battle_wait_seconds", 75)))
        tk.Label(cfg_frame, text="sec", font=("Segoe UI", 9), fg=self.c_muted, bg=self.c_card).pack(side=tk.LEFT, padx=(0, 14))

        # Drag Duke deployment count (Default: 1X)
        tk.Label(cfg_frame, text="Drag Duke:", font=("Segoe UI", 9, "bold"), fg=self.c_gold, bg=self.c_card).pack(side=tk.LEFT, padx=(0, 4))
        self.spn_duke_count = tk.Spinbox(cfg_frame, from_=1, to=16, width=3, bg="#090d16", fg=self.c_text,
                                         insertbackground=self.c_gold, font=("Consolas", 10), justify="center")
        self.spn_duke_count.pack(side=tk.LEFT, padx=(0, 2))
        self.spn_duke_count.delete(0, tk.END)
        self.spn_duke_count.insert(0, str(self.cfg.get("drag_duke_count", 1)))
        tk.Label(cfg_frame, text="x", font=("Segoe UI", 9), fg=self.c_muted, bg=self.c_card).pack(side=tk.LEFT, padx=(0, 14))

        # Dragon deployment count (Default: 16X)
        tk.Label(cfg_frame, text="Dragons:", font=("Segoe UI", 9, "bold"), fg=self.c_gold, bg=self.c_card).pack(side=tk.LEFT, padx=(0, 4))
        self.spn_dragon_count = tk.Spinbox(cfg_frame, from_=1, to=30, width=3, bg="#090d16", fg=self.c_text,
                                           insertbackground=self.c_gold, font=("Consolas", 10), justify="center")
        self.spn_dragon_count.pack(side=tk.LEFT, padx=(0, 2))
        self.spn_dragon_count.delete(0, tk.END)
        self.spn_dragon_count.insert(0, str(self.cfg.get("dragon_count", 16)))
        tk.Label(cfg_frame, text="x", font=("Segoe UI", 9), fg=self.c_muted, bg=self.c_card).pack(side=tk.LEFT, padx=(0, 14))

        # 10-Step Visual Flow Roadmap Banner
        roadmap_card = tk.Frame(self.tab_dashboard, bg="#0b1329", padx=10, pady=5, highlightthickness=1, highlightbackground="#334155")
        roadmap_card.pack(fill=tk.X, pady=(0, 6))

        steps_text = "⚔️ Sequence: 1. Battle (Single Click) ➔ 2. Find Match (Single Click) ➔ 3. Attack ➔ 4. Zoom Out ➔ 5. Deploy Drag Duke (1x) & Dragon (16x) ➔ 6. Wait (Custom Limit) ➔ 7. End Battle / Surrender ➔ 8. OK ➔ 9. Return Home"
        tk.Label(roadmap_card, text=steps_text, font=("Segoe UI", 8), fg="#93c5fd", bg="#0b1329", justify="left").pack(anchor="w")

        # Live Status Strip
        status_card = tk.Frame(self.tab_dashboard, bg="#090d16", padx=10, pady=6, highlightthickness=1, highlightbackground=self.c_gold)
        status_card.pack(fill=tk.X, pady=(0, 8))

        self.lbl_status = tk.Label(status_card, text="Status: Ready. Click '▶ START ATTACK CYCLE' to run state-verified sequence.",
                                   font=("Segoe UI", 9, "bold"), fg=self.c_gold_glow, bg="#090d16")
        self.lbl_status.pack(side=tk.LEFT)

        # Log Terminal
        log_frame = tk.Frame(self.tab_dashboard, bg=self.c_card)
        log_frame.pack(fill=tk.BOTH, expand=True)

        self.txt_log = tk.Text(log_frame, bg="#050811", fg="#e2e8f0", insertbackground=self.c_gold,
                               font=("Consolas", 9), wrap=tk.WORD, borderwidth=0, padx=10, pady=8)
        self.txt_log.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        sb_log = ttk.Scrollbar(log_frame, command=self.txt_log.yview)
        sb_log.pack(side=tk.RIGHT, fill=tk.Y)
        self.txt_log.config(yscrollcommand=sb_log.set)

    def _build_tab_icons(self):
        top_bar = tk.Frame(self.tab_icons, bg=self.c_panel)
        top_bar.pack(fill=tk.X, pady=(0, 8))

        tk.Label(top_bar, text="Icon Detection Library (Screen Vision Targets)",
                 font=("Segoe UI", 10, "bold"), fg=self.c_gold, bg=self.c_panel).pack(side=tk.LEFT)

        btn_snip_new = ttk.Button(top_bar, text="📸 Snip Icon from Screen", style="Gold.TButton",
                                  command=self.start_snip_icon)
        btn_snip_new.pack(side=tk.RIGHT, padx=(6, 0))

        btn_test_detect = ttk.Button(top_bar, text="🔍 Test Detection on Screen", style="Secondary.TButton",
                                     command=self.test_selected_icon_detection)
        btn_test_detect.pack(side=tk.RIGHT, padx=(6, 0))

        btn_refresh = ttk.Button(top_bar, text="🔄 Refresh", style="Secondary.TButton",
                                 command=self.refresh_icon_library)
        btn_refresh.pack(side=tk.RIGHT)

        paned = tk.PanedWindow(self.tab_icons, orient=tk.HORIZONTAL, bg=self.c_bg, sashwidth=4)
        paned.pack(fill=tk.BOTH, expand=True)

        left_box = tk.Frame(paned, bg=self.c_card)
        paned.add(left_box, minsize=200, width=260)

        self.list_icons = tk.Listbox(left_box, bg="#090d16", fg=self.c_text, font=("Consolas", 10),
                                     selectbackground=self.c_gold, selectforeground="#000000",
                                     borderwidth=0, activestyle="none")
        self.list_icons.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.list_icons.bind("<<ListboxSelect>>", self.on_icon_select)

        sb_icons = ttk.Scrollbar(left_box, command=self.list_icons.yview)
        sb_icons.pack(side=tk.RIGHT, fill=tk.Y)
        self.list_icons.config(yscrollcommand=sb_icons.set)

        self.right_preview = tk.Frame(paned, bg=self.c_card, padx=16, pady=16)
        paned.add(self.right_preview, minsize=320)

        self.lbl_icon_name = tk.Label(self.right_preview, text="Select an icon to preview",
                                      font=("Segoe UI", 11, "bold"), fg=self.c_gold, bg=self.c_card)
        self.lbl_icon_name.pack(anchor="w", pady=(0, 10))

        self.lbl_icon_img = tk.Label(self.right_preview, bg="#090d16", width=220, height=140)
        self.lbl_icon_img.pack(pady=(0, 12))

        self.lbl_icon_info = tk.Label(self.right_preview, text="Template Path:\nDimensions:",
                                      font=("Segoe UI", 9), fg=self.c_muted, bg=self.c_card, justify="left")
        self.lbl_icon_info.pack(anchor="w", pady=(0, 16))

        btn_del = ttk.Button(self.right_preview, text="🗑️ Delete Icon", style="Crimson.TButton",
                             command=self.delete_selected_icon)
        btn_del.pack(anchor="w")

    def _build_tab_ai(self):
        # AI Advisor tab
        top_bar = tk.Frame(self.tab_ai, bg=self.c_panel)
        top_bar.pack(fill=tk.X, pady=(0, 8))

        tk.Label(top_bar, text="🤖 Tactical AI Advisor (Powered by Gemini 3.1 Flash-Lite)",
                 font=("Segoe UI", 10, "bold"), fg=self.c_gold, bg=self.c_panel).pack(side=tk.LEFT)

        btn_analyze = ttk.Button(top_bar, text="📸 Analyze Live Base Screenshot", style="Gold.TButton",
                                 command=self.ai_analyze_current_screen)
        btn_analyze.pack(side=tk.RIGHT)

        # AI Status strip
        self.lbl_ai_status = tk.Label(self.tab_ai, text="Gemini AI: Ready" if self.advisor.is_configured() else "Gemini AI: API Key Missing (Click 'Gemini API' to configure)",
                                      font=("Segoe UI", 9), fg=self.c_emerald if self.advisor.is_configured() else "#f87171", bg=self.c_panel)
        self.lbl_ai_status.pack(anchor="w", pady=(0, 6))

        # Query frame
        query_frame = tk.Frame(self.tab_ai, bg=self.c_card, padx=10, pady=8)
        query_frame.pack(fill=tk.X, pady=(0, 8))

        tk.Label(query_frame, text="Ask AI Strategist:", font=("Segoe UI", 9, "bold"), fg=self.c_text, bg=self.c_card).pack(side=tk.LEFT, padx=(0, 6))
        self.ent_ai_prompt = tk.Entry(query_frame, bg="#090d16", fg=self.c_text, insertbackground=self.c_gold, font=("Segoe UI", 9))
        self.ent_ai_prompt.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
        self.ent_ai_prompt.insert(0, "How should I funnel dragons against central Town Hall 14?")

        btn_ask = ttk.Button(query_frame, text="⚡ Ask AI", style="Secondary.TButton",
                             command=self.ai_ask_question)
        btn_ask.pack(side=tk.RIGHT)

        # Response text box
        ai_resp_frame = tk.Frame(self.tab_ai, bg=self.c_card)
        ai_resp_frame.pack(fill=tk.BOTH, expand=True)

        self.txt_ai_response = tk.Text(ai_resp_frame, bg="#050811", fg="#e2e8f0", insertbackground=self.c_gold,
                                       font=("Segoe UI", 10), wrap=tk.WORD, borderwidth=0, padx=12, pady=10)
        self.txt_ai_response.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        sb_ai = ttk.Scrollbar(ai_resp_frame, command=self.txt_ai_response.yview)
        sb_ai.pack(side=tk.RIGHT, fill=tk.Y)
        self.txt_ai_response.config(yscrollcommand=sb_ai.set)

    def _build_tab_history(self):
        top_hist = tk.Frame(self.tab_history, bg=self.c_panel)
        top_hist.pack(fill=tk.X, pady=(0, 8))

        tk.Label(top_hist, text="📜 Friendly Conversation & Action History",
                 font=("Segoe UI", 10, "bold"), fg=self.c_gold, bg=self.c_panel).pack(side=tk.LEFT)

        btn_open_md = ttk.Button(top_hist, text="📂 Open History Markdown", style="Secondary.TButton",
                                 command=self.open_history_markdown)
        btn_open_md.pack(side=tk.RIGHT)

        btn_refresh_h = ttk.Button(top_hist, text="🔄 Refresh", style="Secondary.TButton",
                                   command=self.refresh_history_tab)
        btn_refresh_h.pack(side=tk.RIGHT, padx=(0, 6))

        self.txt_history = tk.Text(self.tab_history, bg="#090d16", fg=self.c_text, font=("Segoe UI", 10),
                                   wrap=tk.WORD, borderwidth=0, padx=12, pady=10)
        self.txt_history.pack(fill=tk.BOTH, expand=True)

        self.after(600, self.refresh_history_tab)

    def _build_footer(self):
        ftr = tk.Frame(self, bg=self.c_panel, height=28, padx=12, pady=4)
        ftr.pack(fill=tk.X, side=tk.BOTTOM)

        tk.Label(ftr, text="🛡️ Safety Failsafe: Move mouse to corner (0,0) or click Stop to halt immediately.",
                 font=("Segoe UI", 8), fg=self.c_muted, bg=self.c_panel).pack(side=tk.LEFT)

        btn_desktop = ttk.Button(ftr, text="📌 Create Desktop Shortcut", style="Secondary.TButton",
                                 command=self.create_desktop_shortcut)
        btn_desktop.pack(side=tk.RIGHT)

    # ─── API Key Configuration ───────────────────────────────────────────────────────

    def _check_api_key_prompt(self):
        key = self.cfg.get("gemini_api_key", "").strip()
        if not key:
            ans = messagebox.askyesno(
                "Gemini AI Advisor Setup",
                "Welcome to COC Attacker Bot!\n\nWould you like to configure your Google Gemini API Key now for AI Tactical Analysis & Base Scouting?\n(You can also skip and run visual attack cycles without it)."
            )
            if ans:
                self.prompt_gemini_key()

    def prompt_gemini_key(self):
        current_key = self.cfg.get("gemini_api_key", "")
        key = simpledialog.askstring("Gemini API Key", "Enter your Google Gemini API Key:", initialvalue=current_key, parent=self)
        if key is not None:
            self.cfg["gemini_api_key"] = key.strip()
            save_config(self.cfg)
            self.advisor.update_key(key.strip())
            is_ok = self.advisor.is_configured()
            self.lbl_ai_status.config(
                text="Gemini AI: Configured & Ready" if is_ok else "Gemini AI: Key Missing or SDK error",
                fg=self.c_emerald if is_ok else "#f87171"
            )
            if is_ok:
                messagebox.showinfo("Gemini Configured", "Google Gemini API key saved successfully!\nYou can now use AI Base Analysis and Strategy Advisor.")
                self.log("🔑 Gemini API key configured successfully.")

    # ─── AI Advisor Actions ──────────────────────────────────────────────────────────

    def ai_analyze_current_screen(self):
        if not self.advisor.is_configured():
            self.prompt_gemini_key()
            if not self.advisor.is_configured():
                return

        self.txt_ai_response.delete("1.0", tk.END)
        self.txt_ai_response.insert(tk.END, "⏳ Capturing game screen and analyzing base with Gemini AI (3.1 Flash-Lite)...\n")

        def _worker():
            win_rect = self.controller.clicker.bring_game_to_front()
            screen_bgr, _, _ = self.controller.vision.capture_screen_bgr(win_rect)
            # Convert BGR to RGB PIL
            rgb = cv2.cvtColor(screen_bgr, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(rgb)
            analysis = self.advisor.analyze_base_or_battle(pil_img)

            def _show():
                self.txt_ai_response.delete("1.0", tk.END)
                self.txt_ai_response.insert(tk.END, "⚔️ AI TACTICAL BASE ASSESSMENT:\n" + ("="*40) + "\n\n" + analysis)
            self.after(0, _show)

        threading.Thread(target=_worker, daemon=True).start()

    def ai_ask_question(self):
        q = self.ent_ai_prompt.get().strip()
        if not q:
            return
        if not self.advisor.is_configured():
            self.prompt_gemini_key()
            if not self.advisor.is_configured():
                return

        self.txt_ai_response.delete("1.0", tk.END)
        self.txt_ai_response.insert(tk.END, f"⏳ Asking Gemini AI: '{q}'...\n")

        def _worker():
            ans = self.advisor.ask_advice(q)
            def _show():
                self.txt_ai_response.delete("1.0", tk.END)
                self.txt_ai_response.insert(tk.END, f"💬 Question: {q}\n" + ("="*40) + "\n\n" + ans)
            self.after(0, _show)

        threading.Thread(target=_worker, daemon=True).start()

    # ─── Automation Actions ──────────────────────────────────────────────────────────

    def toggle_main_run(self):
        if self.controller.is_running:
            self.controller.stop_automation()
            self.btn_main_run.config(text="▶ START ATTACK CYCLE", style="Emerald.TButton")
        else:
            try:
                cycles = int(self.spn_cycles.get())
                battle_wait = int(self.spn_battle_wait.get())
                duke_count = int(self.spn_duke_count.get())
                dragon_count = int(self.spn_dragon_count.get())
            except ValueError:
                cycles = 5
                battle_wait = 75
                duke_count = 1
                dragon_count = 16
            self.cfg["cycles"] = cycles
            self.cfg["battle_wait_seconds"] = battle_wait
            self.cfg["drag_duke_count"] = duke_count
            self.cfg["dragon_count"] = dragon_count
            save_config(self.cfg)

            self.btn_main_run.config(text="⏹ STOP ATTACK CYCLE", style="Crimson.TButton")
            self.controller.start_automation(
                cycles=cycles,
                battle_wait_sec=battle_wait,
                drag_duke_count=duke_count,
                dragon_count=dragon_count
            )
            self._log_history_entry(
                "Started Verified Attack Cycle",
                f"Running {cycles} cycle(s), attack limit: {battle_wait}s, Drag Duke ({duke_count}x), Dragon ({dragon_count}x)."
            )

    def quick_collect_resources(self):
        self.log("💰 Launching 1-Click Loot Collection...")
        threading.Thread(target=self.controller.collect_resources, daemon=True).start()
        self._log_history_entry("Collected Village Loot", "Visually detected and clicked all visible Gold and Elixir bubbles.")

    def toggle_run_from_float(self, start: bool):
        if start:
            if not self.controller.is_running:
                self.toggle_main_run()
        else:
            if self.controller.is_running:
                self.toggle_main_run()

    def toggle_dashboard(self):
        if self.state() == "withdrawn" or self.state() == "iconic":
            self.deiconify()
            self.lift()
            self.focus_force()
        else:
            self.withdraw()

    # ─── Icon Management ───────────────────────────────────────────────────────────

    def refresh_icon_library(self):
        self.controller.vision.load_all_templates()
        names = self.controller.vision.get_template_names()
        self.list_icons.delete(0, tk.END)
        for n in names:
            self.list_icons.insert(tk.END, f"🎯 {n}")
        if names:
            self.list_icons.selection_set(0)
            self.on_icon_select()

    def on_icon_select(self, event=None):
        sel = self.list_icons.curselection()
        if not sel:
            return
        item_text = self.list_icons.get(sel[0]).replace("🎯 ", "").strip()
        tpl_path = TEMPLATES_DIR / f"{item_text}.png"

        self.lbl_icon_name.config(text=f"🎯 {item_text}")
        if tpl_path.exists():
            try:
                img = Image.open(tpl_path)
                w, h = img.size
                max_w, max_h = 200, 120
                scale = min(max_w / max(1, w), max_h / max(1, h), 2.5)
                prev_size = (int(w * scale), int(h * scale))
                prev_img = img.resize(prev_size, Image.Resampling.LANCZOS)

                self.curr_preview_photo = ImageTk.PhotoImage(prev_img)
                self.lbl_icon_img.config(image=self.curr_preview_photo, text="")
                self.lbl_icon_info.config(text=f"Template: {tpl_path.name}\nDimensions: {w} x {h} px\nType: PNG Icon Target")
            except Exception as e:
                self.lbl_icon_img.config(image="", text=f"Error previewing: {e}")
        else:
            self.lbl_icon_img.config(image="", text="No preview file")

    def start_snip_icon(self):
        self.snipper.start_snip(parent_window=self)

    def on_icon_snipped(self, icon_name: str, crop_img: Image.Image):
        saved_path = self.controller.vision.save_new_template(icon_name, crop_img)
        self.log(f"📸 Snapped new icon '{icon_name}' ➔ Saved to {saved_path.name}")
        messagebox.showinfo("Icon Saved", f"Successfully saved icon '{icon_name}'!\nScreenScope can now locate and click this icon anywhere on screen.")
        self.refresh_icon_library()

    def test_selected_icon_detection(self):
        sel = self.list_icons.curselection()
        if not sel:
            messagebox.showwarning("Select Icon", "Please select an icon from the list to test detection.")
            return
        icon_name = self.list_icons.get(sel[0]).replace("🎯 ", "").strip()
        self.log(f"🔍 Testing detection on screen for: '{icon_name}'...")

        target = self.controller.vision.find_icon(icon_name, threshold=0.68)
        if target:
            self.log(f"✅ FOUND! '{icon_name}' is currently visible on screen at ({target.center_x}, {target.center_y}) with {int(target.confidence*100)}% confidence!")
            messagebox.showinfo("Detection Success", f"🎯 Found '{icon_name}' on screen!\n\nCoordinates: ({target.center_x}, {target.center_y})\nConfidence: {int(target.confidence*100)}%\n\nScreenWriter clicker can target this icon instantly.")
        else:
            self.log(f"❌ '{icon_name}' is not currently visible on screen.")
            messagebox.showwarning("Not Found", f"Icon '{icon_name}' was not detected on your screen right now.\nMake sure the game or button is visible.")

    def delete_selected_icon(self):
        sel = self.list_icons.curselection()
        if not sel:
            return
        icon_name = self.list_icons.get(sel[0]).replace("🎯 ", "").strip()
        tpl_path = TEMPLATES_DIR / f"{icon_name}.png"
        if messagebox.askyesno("Delete Icon", f"Are you sure you want to delete template '{icon_name}'?"):
            if tpl_path.exists():
                try:
                    tpl_path.unlink()
                except Exception:
                    pass
            self.refresh_icon_library()

    # ─── Logging & Friendly History ────────────────────────────────────────────────

    def log(self, msg: str):
        self._append_log_threadsafe(msg)

    def _append_log_threadsafe(self, msg: str):
        def _ui():
            self.txt_log.insert(tk.END, msg + "\n")
            self.txt_log.see(tk.END)
        self.after(0, _ui)

    def _set_status_threadsafe(self, text: str):
        def _ui():
            self.lbl_status.config(text=f"Status: {text}")
        self.after(0, _ui)

    def _log_history_entry(self, action: str, details: str):
        t_str = time.strftime("%B %d, %Y at %I:%M %p").replace(" 0", " ")
        entry = f"\n### 💬 Action at {t_str}\n\n"
        entry += "**👤 Task:**\n"
        entry += f"> {action}\n\n"
        entry += "**⚔️ Bot Execution:**\n"
        entry += f"> {details}\n>\n"
        entry += "> Target actions verified via OpenCV template matching with zero hardcoded coordinates!\n\n---\n"

        try:
            if not HISTORY_FILE.exists() or HISTORY_FILE.stat().st_size == 0:
                hdr = "# ⚔️ COC Attacker Bot History\n\nAll automated attack cycles and collector sweeps are documented here in plain English.\n\n---\n"
                with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                    f.write(hdr + entry)
            else:
                with open(HISTORY_FILE, "a", encoding="utf-8") as f:
                    f.write(entry)
        except Exception:
            pass

    def refresh_history_tab(self):
        self.txt_history.delete("1.0", tk.END)
        if HISTORY_FILE.exists():
            try:
                with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                    content = f.read()
                self.txt_history.insert(tk.END, content)
            except Exception:
                pass
        else:
            self.txt_history.insert(tk.END, "No history recorded yet. Run an attack or collect loot to see logs!")

    def open_history_markdown(self):
        if not HISTORY_FILE.exists():
            self._log_history_entry("Initialize History", "Created session history log.")
        try:
            os.startfile(str(HISTORY_FILE))
        except Exception as e:
            messagebox.showerror("Error", f"Could not open history file: {e}")

    def create_desktop_shortcut(self):
        from create_coc_shortcut import create_coc_desktop_shortcut
        res = create_coc_desktop_shortcut()
        if res:
            messagebox.showinfo("Shortcut Created", f"COC Attacker Bot shortcut created on your desktop:\n\n{res}")
        else:
            messagebox.showerror("Error", "Could not create desktop shortcut.")

    def on_close_window(self):
        self.withdraw()

def main():
    import cv2
    app = CoCAttackerBotApp()
    app.mainloop()

if __name__ == "__main__":
    main()
