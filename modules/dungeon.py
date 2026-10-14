import re
import time
import random
from typing import Optional, Callable, List
from playwright.sync_api import Page, Locator
from modules.base import BaseModule, BotTask, ActionResult

class DungeonModule(BaseModule):
    """
    Automates dungeon encounters, handling room progression, difficulty selection (dif2),
    and optional restart-on-defeat functionality.
    """

    # Multilingual keywords for flexible button and state matching
    READY_KEYWORDS = [
        "zindan`a geç", "zindana geç", "zindana git", "zindana gir",
        "to the dungeon", "enter dungeon", "go to dungeon", "dungeon",
        "zum dungeon", "dungeon betreten", "al calabozo"
    ]

    DIFFICULTY_KEYWORDS = [
        "ileri", "advanced", "fortgeschritten", "avanzado", "diff2", "dif2"
    ]

    EXIT_BUTTON_KEYWORDS = [
        "çık", "zindan`dan çık", "zindandan çık", "zindan'dan çık",
        "leave", "exit", "cancel", "quit", "abandon",
        "verlassen", "abbrechen", "salir", "abandonar"
    ]

    LOSS_KEYWORDS = [
        "kaybettin", "mağlubiyet", "mağlup",
        "defeat", "defeated", "you lost", "lost the battle",
        "verloren", "niederlage", "derrota", "défaite"
    ]

    def __init__(self, enabled: bool = False, priority: int = 4, restart_on_loss: bool = False):
        super().__init__(name="Dungeon", enabled=enabled, priority=priority)
        self.restart_on_loss = restart_on_loss

    def evaluate(self, page: Page, browser) -> Optional[BotTask]:
        """Checks dungeon points and cooldown bar to determine if a run is ready."""
        if not self.enabled:
            return None

        # Check local cooldown timer first
        if time.time() < self.next_allowed_time:
            return None

        try:
            # 1. Check available dungeon points
            points_el = page.locator("#dungeonpoints_value_point")
            if points_el.is_visible():
                try:
                    points = int(points_el.inner_text().strip())
                    if points <= 0:
                        return None
                except ValueError:
                    pass

            # 2. Check cooldown bar
            cooldown_div = page.locator("#cooldown_bar_text_dungeon")
            if cooldown_div.is_visible():
                text = cooldown_div.inner_text().strip().lower()

                # If there's an active timer (e.g. 04:12), it's not ready
                if re.search(r"\d+:\d+", text):
                    return None

                # Ready if empty or matches any multilingual ready keyword
                is_ready = (text == "" or any(kw in text for kw in self.READY_KEYWORDS))

                if is_ready:
                    return BotTask(
                        name="Run Dungeon",
                        module_name=self.name,
                        priority=self.priority,
                        execute_fn=self.execute
                    )
        except Exception:
            pass

        return None

    def execute(self, page: Page, browser, can_continue: Callable[[], bool]) -> ActionResult:
        """Executes one dungeon combat step, handles initiation, and restarts on loss if enabled."""
        if not can_continue():
            return ActionResult(success=False, message="Dungeon aborted before start (paused or stopped)")

        try:
            # Step 1: Navigate to dungeon via cooldown bar link
            browser.log("[Dungeon] Navigating to dungeon via cooldown link...", "INFO")
            self._navigate_to_dungeon(page, browser, can_continue)
            browser.human_delay(1.5, 2.5, page=page, pause_checker=can_continue)
            if not can_continue():
                return ActionResult(success=False, message="Paused during dungeon navigation")

            # Step 2: Check for active encounters (startFight / map_label)
            browser.log("[Dungeon] Scanning #content for active encounters (images with startFight in onclick)...", "INFO")
            target_encounter = self._find_target_encounter(page)

            # If no encounter exists, check if dungeon needs initiation (dif2)
            if not target_encounter:
                browser.log("[Dungeon] No active startFight encounter found. Checking if difficulty button (dif2) exists...", "INFO")
                dif_button = self._find_difficulty_button(page)
                if dif_button and dif_button.is_visible():
                    browser.log("[Dungeon] Clicking difficulty button (dif2) to initiate dungeon...", "INFO")
                    browser.human_move_and_click(page, dif_button, pause_checker=can_continue)
                    browser.human_delay(2.0, 3.0, page=page, pause_checker=can_continue)
                    if not can_continue():
                        return ActionResult(success=False, message="Paused after initiating dungeon")

                    # Re-check for encounters after initiation
                    browser.log("[Dungeon] Dungeon initiated! Scanning for newly rendered startFight encounters...", "INFO")
                    target_encounter = self._find_target_encounter(page)

            if not target_encounter:
                browser.log("[Dungeon] Neither startFight encounter nor difficulty initiation button (dif2) found.", "WARNING")
                return ActionResult(
                    success=False,
                    message="Neither startFight encounter nor difficulty initiation button (dif2) found in dungeon.",
                    retry_delay_seconds=30.0
                )

            # Step 3: Click target encounter to attack
            browser.log("[Dungeon] Engaging target encounter (clicking startFight element)...", "INFO")
            browser.human_move_and_click(page, target_encounter, pause_checker=can_continue)
            self.last_run_time = time.time()
            self.next_allowed_time = time.time() + 45.0  # Default safe cooldown
            browser.log("[Dungeon] Dungeon attack sent successfully!", "SUCCESS")

            browser.human_delay(2.0, 3.0, page=page, pause_checker=can_continue)
            if not can_continue():
                return ActionResult(success=True, message="Dungeon encounter clicked (paused afterwards)")

            # Step 4: Handle possible loot / reward popup (similar to expedition)
            self._check_and_claim_loot(page, browser, can_continue)

            # Step 5: Check for loss / defeat if restart_on_loss is enabled
            if self.restart_on_loss:
                browser.log("[Dungeon] Checking combat outcome for defeat (.reportLose)...", "INFO")
                if self._is_defeat(page):
                    browser.log("[Dungeon] Defeat detected! 'Restart on Loss' is enabled. Restarting dungeon...", "WARNING")
                    # Navigate back to dungeon page regardless of cooldown
                    browser.human_delay(1.0, 1.5, page=page, pause_checker=can_continue)
                    self._navigate_to_dungeon(page, browser, can_continue)
                    browser.human_delay(1.5, 2.5, page=page, pause_checker=can_continue)

                    # Find and click "Zindan`dan çık" (Leave dungeon) button
                    exit_button = self._find_exit_button(page)
                    if exit_button and exit_button.is_visible():
                        browser.log("[Dungeon] Clicking 'Zindan`dan çık' (Leave dungeon) button...", "INFO")
                        browser.human_move_and_click(page, exit_button, pause_checker=can_continue)
                        browser.human_delay(1.5, 2.5, page=page, pause_checker=can_continue)

                        # Re-initiate dungeon with dif2
                        dif_button = self._find_difficulty_button(page)
                        if dif_button and dif_button.is_visible():
                            browser.log("[Dungeon] Re-initiating dungeon with dif2...", "INFO")
                            browser.human_move_and_click(page, dif_button, pause_checker=can_continue)
                            browser.human_delay(1.5, 2.5, page=page, pause_checker=can_continue)
                            browser.log("[Dungeon] Dungeon reset and re-initiated successfully!", "SUCCESS")

                    return ActionResult(
                        success=True,
                        message="Dungeon encounter executed. Matchup was a defeat -> Exited and reinitiated with dif2.",
                        cooldown_seconds=60.0
                    )
                else:
                    browser.log("[Dungeon] Combat victory or ongoing. No restart needed.", "SUCCESS")

            return ActionResult(
                success=True,
                message="Dungeon encounter attack executed successfully.",
                cooldown_seconds=60.0
            )

        except Exception as e:
            browser.log(f"[Dungeon] Error occurred: {e}", "ERROR")
            return ActionResult(success=False, message=f"Dungeon error: {e}", retry_delay_seconds=20.0)

    # ----------------- Helper Methods -----------------

    def _navigate_to_dungeon(self, page: Page, browser, can_continue: Callable[[], bool]):
        """Navigates to the dungeon view via cooldown bar or sidebar navigation."""
        # Check cooldown bar link inside cooldown_bar_text_dungeon or cooldown_bar_dungeon
        candidates = [
            "#cooldown_bar_dungeon .cooldown_bar_link",
            "#cooldown_bar_text_dungeon a",
            ".cooldown_bar_link",
            "#snavi_dungeon"
        ]
        for sel in candidates:
            loc = page.locator(sel).first
            if loc.is_visible():
                browser.human_move_and_click(page, loc, pause_checker=can_continue)
                return

    def _find_target_encounter(self, page: Page) -> Optional[Locator]:
        """
        Finds any visible fightable dungeon encounter.
        Checks for:
        1. Elements / images inside #content with onclick containing 'startFight'
        2. Any element on the page with onclick containing 'startFight'
        3. div.map_label or .map_label elements
        """
        # Primary: CSS attribute selector for startFight inside #content
        startfight_selectors = [
            '#content img[onclick*="startFight"]',
            '#content [onclick*="startFight"]',
            '[onclick*="startFight"]',
            'div.map_label, .map_label'
        ]

        for sel in startfight_selectors:
            try:
                elements = page.locator(sel).all()
                for el in elements:
                    if el.is_visible():
                        return el
            except Exception:
                continue

        # Secondary fallback: inspect all images and interactive elements inside #content
        try:
            candidates = page.locator("#content img, #content a, #content area, #content div").all()
            for el in candidates:
                try:
                    if not el.is_visible():
                        continue
                    onclick_val = (el.get_attribute("onclick") or "").lower()
                    if "startfight" in onclick_val:
                        return el
                except Exception:
                    continue
        except Exception:
            pass

        return None

    def _find_difficulty_button(self, page: Page) -> Optional[Locator]:
        """
        Finds the advanced difficulty button (dif2 / İleri Düzeyde / Advanced).
        Prioritizes HTML attribute matching (name='dif2') over language-specific strings.
        """
        # Primary: exact name attribute
        by_name = page.locator('input[name="dif2"], button[name="dif2"]').first
        if by_name.is_visible():
            return by_name

        # Secondary: button with dif in name
        by_partial_name = page.locator('input[name*="dif"]').all()
        for btn in by_partial_name:
            if btn.is_visible():
                return btn

        # Tertiary: multilingual button value matching
        for kw in self.DIFFICULTY_KEYWORDS:
            by_val = page.locator(f'input[type="submit"][value*="{kw}" i], button:has-text("{kw}")').first
            if by_val.is_visible():
                return by_val

        return None

    def _find_exit_button(self, page: Page) -> Optional[Locator]:
        """
        Finds the 'Zindan`dan çık' / 'Leave dungeon' button.
        Uses name attribute checks first, then falls back to multilingual matching on .button1.
        """
        # Attribute check (e.g. cancelDungeon, abort, cancel)
        attr_candidates = [
            'input[name*="cancel"]',
            'input[name*="abort"]',
            'input[name*="exit"]',
            'input[name*="leave"]',
            'form[action*="cancel"] input[type="submit"]'
        ]
        for sel in attr_candidates:
            btn = page.locator(sel).first
            if btn.is_visible():
                return btn

        # Class .button1 with multilingual keyword matching
        buttons = page.locator("input.button1, button.button1, .button1").all()
        for btn in buttons:
            try:
                if not btn.is_visible():
                    continue
                val = (btn.get_attribute("value") or "").lower()
                text = (btn.inner_text() or "").lower()
                combined = f"{val} {text}"
                if any(kw in combined for kw in self.EXIT_BUTTON_KEYWORDS):
                    return btn
            except Exception:
                continue

        return None

    def _is_defeat(self, page: Page) -> bool:
        """Determines if the recent combat resulted in a defeat / loss by checking for div.reportLose."""
        try:
            # Primary check: existence of div with class 'reportLose'
            report_lose = page.locator("div.reportLose, .reportLose")
            if report_lose.count() > 0:
                return True

            # Secondary fallback: check report header text
            report_header = page.locator("#reportHeader, .reportHeader, .reportResult").first
            if report_header.is_visible():
                text = report_header.inner_text().lower()
                if any(kw in text for kw in self.LOSS_KEYWORDS):
                    return True
        except Exception:
            pass
        return False

    def _check_and_claim_loot(self, page: Page, browser, can_continue: Callable[[], bool]):
        """Detects and selects loot reward if a loot popup appeared."""
        try:
            loot_buttons = page.locator(".loot-button")
            if loot_buttons.count() >= 2:
                browser.log("[Dungeon] Reward/loot popup detected! Selecting second option...", "INFO")
                second_loot = loot_buttons.nth(1)
                if second_loot.is_visible():
                    browser.human_move_and_click(page, second_loot, pause_checker=can_continue)
                    browser.human_delay(1.0, 1.5, page=page, pause_checker=can_continue)
                    browser.log("[Dungeon] Second loot reward claimed successfully!", "SUCCESS")
        except Exception:
            pass
