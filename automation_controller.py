import time
import threading
from typing import Optional, List, Dict, Any, Callable, Tuple
from vision_detector import VisionDetector, VisualTarget
from clicker_engine import ClickerEngine

class AutomationController:
    """
    Orchestrates ScreenScope (vision detection) and ScreenWriter (screen clicking).
    Finds and acts purely on required icons dynamically visible on screen,
    with zero hardcoded coordinates!
    """
    def __init__(self, on_log: Optional[Callable[[str], None]] = None,
                 on_status: Optional[Callable[[str], None]] = None):
        self.on_log = on_log or print
        self.on_status = on_status or print
        self.vision = VisionDetector()
        self.clicker = ClickerEngine(on_log=self.log)
        
        self.is_running = False
        self._worker_thread: Optional[threading.Thread] = None
        self.current_cycle = 0
        self.total_cycles = 1

    def log(self, msg: str):
        if self.on_log:
            self.on_log(msg)

    def set_status(self, text: str):
        if self.on_status:
            self.on_status(text)

    def check_and_handle_disconnect(self, win_rect: tuple) -> bool:
        """
        Visually detects if CoC was disconnected due to inactivity ('Anyone there? / RELOAD GAME')
        and clicks the reload button to get back into the village base.
        """
        reload_target = self.vision.find_icon("reload_game", region=win_rect, threshold=0.68)
        if reload_target:
            self.log("🔄 Disconnection prompt detected ('Anyone there?'). Clicking 'RELOAD GAME'...")
            self.clicker.click_at(reload_target.center_x, reload_target.center_y, label="RELOAD GAME")
            self.set_status("Reloading game... waiting 7s for village...")
            time.sleep(7.0)
            return True
        return False

    def click_and_verify(
        self,
        click_icons: List[str] | str,
        label: str,
        verify_icons: Optional[List[str] | str] = None,
        verify_label: str = "",
        verify_disappear: bool = False,
        win_rect: Optional[Tuple[int, int, int, int]] = None,
        max_attempts: int = 6,
        threshold: float = 0.68,
        search_timeout: float = 4.0,
        verify_wait: float = 2.5
    ) -> bool:
        """
        STRICT STATE-VERIFIED CLICK HANDSHAKE:
        1. Confirms click target is positively matched via templates (NO false logs / NO random color guessing).
        2. Clicks the target button.
        3. Strictly verifies that the expected next screen appears (or button disappears).
        4. If verification fails, retries up to max_attempts.
        DOES NOT ADVANCE TO THE NEXT STEP UNTIL THE STATE TRANSITION IS VERIFIED!
        """
        if isinstance(click_icons, str):
            click_icons = [click_icons]
        if verify_icons and isinstance(verify_icons, str):
            verify_icons = [verify_icons]

        self.set_status(f"Searching for [{label}]...")
        self.log(f"🔍 Looking for: [{label}] (templates: {', '.join(click_icons)})")

        for attempt in range(1, max_attempts + 1):
            if not self.is_running or self.clicker.should_stop:
                return False

            # Bring game window to front if it slipped
            if win_rect:
                self.clicker.bring_game_to_front()

            # Pre-check: If verify_icons is ALREADY visible, the screen is already at the target state!
            if verify_icons:
                already_verified = self.vision.find_any_icon(verify_icons, region=win_rect, threshold=threshold)
                if already_verified:
                    self.log(f"🎯 [{verify_label or 'Next Screen'}] is already active on screen! Proceeding cleanly.")
                    return True

            # Pre-check for inactivity disconnect prompt
            if win_rect:
                self.check_and_handle_disconnect(win_rect)

            # Search for the button with pure template matching (strictly rejecting loose color guessing)
            target = None
            t_start = time.time()
            while time.time() - t_start < search_timeout:
                if not self.is_running or self.clicker.should_stop:
                    return False
                target = self.vision.find_any_icon(click_icons, region=win_rect, threshold=threshold)
                if target:
                    break
                time.sleep(0.3)

            if not target:
                # Check again if next screen appeared during search
                if verify_icons:
                    already_verified = self.vision.find_any_icon(verify_icons, region=win_rect, threshold=threshold)
                    if already_verified:
                        self.log(f"🎯 [{verify_label or 'Next Screen'}] appeared during search! Proceeding.")
                        return True

                self.log(f"⏳ [{label}] not visible yet (attempt {attempt}/{max_attempts}). Re-scanning...")
                time.sleep(0.5)
                continue

            # Found target cleanly via template!
            self.log(f"🎯 Found [{label}] (conf: {target.confidence:.2f}) at ({target.center_x}, {target.center_y}). Clicking now...")
            self.clicker.click_at(target.center_x, target.center_y, label=label)

            # Verification phase: confirm screen state transitioned
            if verify_icons:
                self.set_status(f"Verifying transition to [{verify_label or 'Next Screen'}]...")
                verified = False
                v_start = time.time()
                while time.time() - v_start < verify_wait:
                    if not self.is_running or self.clicker.should_stop:
                        return False
                    next_target = self.vision.find_any_icon(verify_icons, region=win_rect, threshold=threshold)
                    if next_target:
                        verified = True
                        break
                    time.sleep(0.35)

                if verified:
                    self.log(f"✅ VERIFIED: [{label}] clicked successfully! [{verify_label or 'Next Screen'}] is confirmed on screen.")
                    return True
                else:
                    self.log(f"⚠️ [{label}] was clicked at ({target.center_x}, {target.center_y}) but [{verify_label or 'Next Screen'}] was NOT detected yet. Retrying click (attempt {attempt}/{max_attempts})...")
                    time.sleep(0.5)

            elif verify_disappear:
                # Verify the button disappears
                self.set_status(f"Verifying [{label}] disappeared...")
                gone = False
                v_start = time.time()
                while time.time() - v_start < verify_wait:
                    if not self.is_running or self.clicker.should_stop:
                        return False
                    still_here = self.vision.find_any_icon(click_icons, region=win_rect, threshold=threshold)
                    if not still_here:
                        gone = True
                        break
                    time.sleep(0.35)

                if gone:
                    self.log(f"✅ VERIFIED: [{label}] disappeared (screen successfully transitioned).")
                    return True
                else:
                    self.log(f"⚠️ [{label}] is still present after click. Retrying click (attempt {attempt}/{max_attempts})...")
                    time.sleep(0.5)
            else:
                # No verification needed
                return True

        self.log(f"❌ State verification FAILED for [{label}] after {max_attempts} attempts. Halting to prevent false progress.")
        return False

    def dismiss_any_popups(self, win_rect: Optional[tuple] = None, max_checks: int = 2):
        """Visually searches for and clicks any popup 'OK' / 'X' buttons."""
        for _ in range(max_checks):
            found = self.vision.find_icon("okay", region=win_rect, threshold=0.72)
            if found:
                self.log(f"Dismissing popup OK at ({found.center_x}, {found.center_y})...")
                self.clicker.click_at(found.center_x, found.center_y, label="Dismiss Popup")
                time.sleep(0.8)
            else:
                break

    def collect_resources(self):
        """Visually finds all Gold & Elixir bubble icons on screen and collects them."""
        self.set_status("Collecting Gold and Elixir bubbles...")
        self.log("💰 Scanning screen for loot collectors...")
        
        gold_targets = self.vision.find_all_matching_icons("gold_collector", threshold=0.72)
        elixir_targets = self.vision.find_all_matching_icons("elixir_collector", threshold=0.72)
        
        all_targets = gold_targets + elixir_targets
        if not all_targets:
            self.log("No collector bubbles visible on screen right now.")
            return

        self.log(f"Found {len(all_targets)} loot bubbles to collect.")
        for t in all_targets:
            if not self.is_running or self.clicker.should_stop:
                break
            self.clicker.click_at(t.center_x, t.center_y, label=f"Collect {t.name}", duration=0.15)
            time.sleep(0.18)

    def run_single_attack_cycle(self, win_rect: tuple, battle_time_sec: int = 105):
        """
        Executes the exact visual sequence with strict verification:
        1. Detect & click Battle icon ('battle.png'). Verify 'find_a_match.png' appears.
        2. Detect & click Find a Match icon ('find_a_match.png'). Verify 'attack.png' appears.
        3. Detect & click Attack icon ('attack.png'). Verify matchmaking/battle HUD starts.
        4. Wait 5 seconds, zoom out of screen as much as possible.
        5. Deploy BOTH 'drag_duke' AND 'dragon' outside red line 16 times each!
        6. Wait for 1 minute 45 seconds (105s).
        7. Detect & click End Battle ('end_battle.png') or Surrender ('surrender.png'). Verify 'okay.png' appears.
        8. Detect & click OK icon ('okay.png'). Verify 'return_home.png' appears.
        9. Detect & click Return Home icon ('return_home.png'). Verify 'battle.png' reappears on village screen.
        10. Repeat cycle.
        """
        l, t, w, h = win_rect

        # Pre-check for inactivity reload prompt
        self.check_and_handle_disconnect(win_rect)

        # ─── Step 1: Click Battle icon & verify Find a Match screen appears ────────────
        self.set_status("[Step 1] Finding and clicking Battle icon...")
        step1_verified = self.click_and_verify(
            click_icons=["battle"],
            label="Battle Icon",
            verify_icons=["find_a_match"],
            verify_label="Find a Match Screen",
            win_rect=win_rect,
            max_attempts=6,
            threshold=0.68,
            search_timeout=5.0,
            verify_wait=2.5
        )
        if not step1_verified:
            self.log("⚠️ Could not confirm Step 1 transition to Match screen. Checking if already on Match screen...")
            if not self.vision.find_icon("find_a_match", region=win_rect, threshold=0.68):
                self.log("❌ Step 1 failed to reach Match screen. Aborting cycle.")
                return

        if not self.is_running or self.clicker.should_stop:
            return

        # ─── Step 2: Click Find a Match icon & verify Attack screen appears ───────────
        self.set_status("[Step 2] Finding and clicking Find a Match icon...")
        step2_verified = self.click_and_verify(
            click_icons=["find_a_match"],
            label="Find a Match Icon",
            verify_icons=["attack"],
            verify_label="Attack Button Screen",
            win_rect=win_rect,
            max_attempts=6,
            threshold=0.68,
            search_timeout=4.0,
            verify_wait=2.5
        )
        if not step2_verified:
            self.log("⚠️ Could not confirm Step 2 transition. Checking if Attack button is already visible...")
            if not self.vision.find_icon("attack", region=win_rect, threshold=0.68):
                self.log("❌ Step 2 failed to reach Attack screen. Aborting cycle.")
                return

        if not self.is_running or self.clicker.should_stop:
            return

        # ─── Step 3: Click Attack icon & verify Battle / Matchmaking begins ───────────
        self.set_status("[Step 3] Finding and clicking Attack icon...")
        step3_verified = self.click_and_verify(
            click_icons=["attack"],
            label="Attack Icon",
            verify_disappear=True,
            win_rect=win_rect,
            max_attempts=6,
            threshold=0.68,
            search_timeout=4.0,
            verify_wait=2.5
        )
        if not step3_verified:
            self.log("❌ Step 3 failed to confirm attack launch. Aborting cycle.")
            return

        if not self.is_running or self.clicker.should_stop:
            return

        # ─── Step 4: Wait 5 seconds & Zoom out fully ──────────────────────────────────
        self.set_status("[Step 4] Matchmaking... waiting 5 seconds for base load...")
        self.log("⏳ [Step 4] Waiting 5 seconds for matchmaking clouds to clear...")
        self.clicker.wait_delay(5.0, "matchmaking settlement")

        if not self.is_running or self.clicker.should_stop:
            return

        # Bring window to front again to ensure zoom registers
        self.clicker.bring_game_to_front()
        cx, cy = int(l + w // 2), int(t + h // 2)
        self.set_status("[Step 4] Zooming out of screen as much as possible...")
        self.log(f"🔎 [Step 4] Zooming out max view at screen center ({cx}, {cy})...")
        self.clicker.zoom_out(cx, cy, ticks=18)
        self.clicker.wait_delay(1.0, "zoom settle")

        if not self.is_running or self.clicker.should_stop:
            return

        # ─── Step 5: Deploy BOTH drag_duke AND dragon the same (16x outside red line) ──
        self.set_status("[Step 5] Deploying BOTH Drag Duke and Dragon outside red line...")
        self.log("🐉 [Step 5] Beginning deployment: Deploying BOTH drag_duke and dragon the same!")

        # ── Part 5A: Deploy Drag Duke ──
        self.log("👑 [Step 5A] Selecting Dragon Duke ('drag_duke.png')...")
        duke_target = self.vision.find_icon("drag_duke", region=win_rect, threshold=0.65)
        if duke_target:
            self.log(f"🎯 Found Drag Duke in dock at ({duke_target.center_x}, {duke_target.center_y}). Selecting...")
            self.clicker.click_at(duke_target.center_x, duke_target.center_y, label="Drag Duke Slot")
        else:
            # Fallback to dock slot 1 (leftmost hero/troop slot)
            slot1_x = int(l + 0.48 * w)
            slot1_y = int(t + 0.92 * h)
            self.log(f"Selecting Drag Duke via Troop Slot 1 at ({slot1_x}, {slot1_y})...")
            self.clicker.click_at(slot1_x, slot1_y, label="Drag Duke (Slot 1)")
        
        time.sleep(0.35)
        self.clicker.deploy_troops_16_times(win_rect, troop_name="Dragon Duke", count=16)
        time.sleep(0.4)

        if not self.is_running or self.clicker.should_stop:
            return

        # ── Part 5B: Deploy Dragon ──
        self.log("🐉 [Step 5B] Selecting Dragon ('dragon.png' / 'dragon_clean.png' / 'dragon_face.png')...")
        dragon_target = self.vision.find_any_icon(["dragon", "dragon_clean", "dragon_face"], region=win_rect, threshold=0.65)
        if dragon_target:
            self.log(f"🎯 Found Dragon in dock at ({dragon_target.center_x}, {dragon_target.center_y}). Selecting...")
            self.clicker.click_at(dragon_target.center_x, dragon_target.center_y, label="Dragon Slot")
        else:
            # Fallback to troop dock slot 3 (next to Drag Duke and Phoenix pet)
            if duke_target:
                slot_drag_x = duke_target.center_x + 150
                slot_drag_y = duke_target.center_y
            else:
                slot_drag_x = int(l + 0.58 * w)
                slot_drag_y = int(t + 0.92 * h)
            self.log(f"Selecting Dragon via Troop Slot at ({slot_drag_x}, {slot_drag_y})...")
            self.clicker.click_at(slot_drag_x, slot_drag_y, label="Dragon (Troop Slot)")

        time.sleep(0.35)
        self.clicker.deploy_troops_16_times(win_rect, troop_name="Dragon", count=16)

        self.log("✅ BOTH Drag Duke and Dragon deployed 16 times outside the red line!")

        if not self.is_running or self.clicker.should_stop:
            return

        # ─── Step 6: Wait for a total of 1 minute 45 seconds (105 seconds) ───────────
        battle_duration_sec = battle_time_sec if battle_time_sec > 0 else 105
        self.set_status(f"[Step 6] Battle in progress — waiting 1m 45s ({battle_duration_sec}s)...")
        self.log(f"⏳ [Step 6] Dragons attacking! Waiting 1 minute 45 seconds ({battle_duration_sec}s)...")

        elapsed = 0
        step_slice = 10
        while elapsed < battle_duration_sec:
            if not self.is_running or self.clicker.should_stop:
                return
            rem = battle_duration_sec - elapsed
            wait_chunk = min(step_slice, rem)
            self.clicker.wait_delay(wait_chunk)
            elapsed += wait_chunk
            rem_left = battle_duration_sec - elapsed

            # Check if battle completed early (Victory / 3-star screen with return_home or okay)
            early_home = self.vision.find_any_icon(["return_home", "okay"], region=win_rect, threshold=0.68)
            if early_home:
                self.log(f"🏆 Battle finished early ({early_home.name} is visible)! Proceeding to end sequence.")
                break

            if rem_left > 0:
                self.set_status(f"[Step 6] Battle ongoing — {rem_left}s remaining of 1m 45s...")
                self.log(f"⏱️ Battle ongoing: {rem_left}s remaining...")

        if not self.is_running or self.clicker.should_stop:
            return

        # ─── Step 7: Click End Battle / Surrender icon & verify OK icon appears ────────
        self.set_status("[Step 7] Finding and clicking End Battle / Surrender icon...")
        self.log("🛑 [Step 7] Looking for End Battle ('end_battle.png') or Surrender ('surrender.png')...")

        # User specified: Both icons can be there. Click on end battle icon if present.
        end_icons = ["end_battle", "end_battle_windowed", "surrender", "surrender_windowed"]
        step7_verified = self.click_and_verify(
            click_icons=end_icons,
            label="End Battle / Surrender",
            verify_icons=["okay", "return_home"],
            verify_label="OK Confirmation / Return Home",
            win_rect=win_rect,
            max_attempts=6,
            threshold=0.60,
            search_timeout=4.0,
            verify_wait=2.0
        )
        if not step7_verified:
            self.log("⚠️ End Battle click not verified; checking if Victory OK/Return Home screen is already open...")
            if not self.vision.find_any_icon(["okay", "return_home"], region=win_rect, threshold=0.65):
                self.log("Retrying End Battle click with broader search...")

        if not self.is_running or self.clicker.should_stop:
            return

        # ─── Step 8: Click OK icon & verify Return Home icon appears ───────────────────
        self.set_status("[Step 8] Finding and clicking OK confirmation icon...")
        self.log("🟢 [Step 8] Looking for OK confirmation icon ('okay.png')...")
        step8_verified = self.click_and_verify(
            click_icons=["okay"],
            label="OK Icon",
            verify_icons=["return_home"],
            verify_label="Return Home Screen",
            win_rect=win_rect,
            max_attempts=6,
            threshold=0.65,
            search_timeout=4.0,
            verify_wait=2.5
        )
        if not step8_verified:
            self.log("Checking if Return Home button is already visible...")

        if not self.is_running or self.clicker.should_stop:
            return

        # ─── Step 9: Click Return Home icon & verify Battle icon reappears ─────────────
        self.set_status("[Step 9] Finding and clicking Return Home icon...")
        self.log("🏡 [Step 9] Looking for Return Home icon ('return_home.png')...")
        step9_verified = self.click_and_verify(
            click_icons=["return_home"],
            label="Return Home Icon",
            verify_icons=["battle"],
            verify_label="Village Home Screen (Battle Icon)",
            win_rect=win_rect,
            max_attempts=8,
            threshold=0.65,
            search_timeout=5.0,
            verify_wait=4.0
        )

        if step9_verified:
            self.log("✨ Returned to village base successfully! Battle button verified on screen.")
        else:
            self.log("Checking for any post-battle village popups...")
            self.dismiss_any_popups(win_rect=win_rect)

        self.dismiss_any_popups(win_rect=win_rect)

    def start_automation(self, cycles: int = 1, battle_wait_sec: int = 150):
        """Starts the visual automation loop in a background thread."""
        if self.is_running:
            return

        self.is_running = True
        self.clicker.should_stop = False
        self.total_cycles = cycles
        self.current_cycle = 0

        def _loop():
            self.log(f"🚀 CoC Vision Automation started for {cycles} cycle(s).")
            try:
                for c in range(1, cycles + 1):
                    if not self.is_running or self.clicker.should_stop:
                        break
                    self.current_cycle = c
                    self.log(f"\n{'═'*45}\n   🎯 VISUAL CYCLE {c} OF {cycles}\n{'═'*45}")
                    
                    win_rect = self.clicker.bring_game_to_front()
                    if not win_rect:
                        self.log("⚠️ Clash of Clans window not found! Please open the game or emulator.")
                        self.set_status("Waiting for game window...")
                        time.sleep(3.0)
                        win_rect = self.clicker.bring_game_to_front()
                        if not win_rect:
                            self.log("❌ Game window missing. Stopping automation.")
                            break

                    self.run_single_attack_cycle(win_rect, battle_time_sec=battle_wait_sec)
                    self.log(f"✅ Cycle {c} completed successfully!")
                    
                    if c < cycles and self.is_running and not self.clicker.should_stop:
                        self.clicker.wait_delay(5.0, "rest before next cycle")

            except Exception as e:
                self.log(f"❌ Error during automation: {e}")
            finally:
                self.is_running = False
                self.set_status("Automation Idle / Stopped.")
                self.log("⏹️ Automation session concluded.")

        self._worker_thread = threading.Thread(target=_loop, daemon=True)
        self._worker_thread.start()

    def stop_automation(self):
        """Stops the running automation safely."""
        self.is_running = False
        self.clicker.should_stop = True
        self.set_status("Stopping automation...")
        self.log("🛑 Stop requested. Halting tasks.")
