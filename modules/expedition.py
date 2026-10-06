import time
import random
from typing import Optional, Callable
from playwright.sync_api import Page
from modules.base import BaseModule, BotTask, ActionResult

class ExpeditionModule(BaseModule):
    """Automates expeditions, attack executions, and reward/loot selections."""

    def __init__(self, enabled: bool = True, priority: int = 3, target_mob_index: int = 1):
        super().__init__(name="Expedition", enabled=enabled, priority=priority)
        self.target_mob_index = target_mob_index  # 1-indexed: 1 = first mob, etc.

    def evaluate(self, page: Page, browser) -> Optional[BotTask]:
        if not self.enabled:
            return None

        # Check local cooldown timer first
        if time.time() < self.next_allowed_time:
            return None

        try:
            # 1. Check points
            points_el = page.locator("#expeditionpoints_value_point")
            if points_el.is_visible():
                try:
                    points = int(points_el.inner_text().strip())
                    if points <= 0:
                        return None
                except ValueError:
                    pass

            # 2. Check cooldown bar
            cooldown_div = page.locator("#cooldown_bar_text_expedition")
            if cooldown_div.is_visible():
                text = cooldown_div.inner_text().strip()
                # Turkish: "Keşif Seferi`ne geç", English: "Go on an expedition", or empty cooldown timer
                is_ready = ("Keşif Seferi`ne geç" in text or 
                            "Keşif Seferine Geç" in text or 
                            "expedition" in text.lower() or 
                            text == "")

                if is_ready:
                    return BotTask(
                        name="Run Expedition",
                        module_name=self.name,
                        priority=self.priority,
                        execute_fn=self.execute
                    )
        except Exception:
            pass

        return None

    def execute(self, page: Page, browser, can_continue: Callable[[], bool]) -> ActionResult:
        if not can_continue():
            return ActionResult(success=False, message="Aborted before start (paused or stopped)")

        try:
            # Step 1: Click the cooldown bar link to navigate to expedition
            cooldown_link = page.locator(".cooldown_bar_link").first
            if cooldown_link.is_visible():
                browser.human_move_and_click(page, ".cooldown_bar_link", pause_checker=can_continue)
            else:
                nav = page.locator("#snavi_expedition")
                if nav.is_visible():
                    browser.human_move_and_click(page, "#snavi_expedition", pause_checker=can_continue)

            browser.human_delay(1.5, 2.5, pause_checker=can_continue)
            if not can_continue():
                return ActionResult(success=False, message="Paused during navigation")

            # Step 2: Target the expedition box
            # e.g., first box or configured index
            box_selector = f".expedition_box:nth-child({self.target_mob_index}) .expedition_button.awesome-button"
            attack_btn = page.locator(box_selector).first

            if not attack_btn.is_visible():
                # Fallback to any button containing 'Saldır' or 'Attack'
                attack_btn = page.locator(".expedition_button").filter(has_text="Saldır").first
                if not attack_btn.is_visible():
                    attack_btn = page.locator(".expedition_button").filter(has_text="Attack").first

            if not attack_btn.is_visible():
                return ActionResult(success=False, message="Attack button not found on expedition page")

            # Step 3: Click attack
            box = attack_btn.bounding_box()
            if box:
                page.mouse.move(
                    box["x"] + random.randint(5, max(6, int(box["width"] - 5))),
                    box["y"] + random.randint(5, max(6, int(box["height"] - 5))),
                    steps=random.randint(10, 18)
                )
            attack_btn.click()
            self.last_run_time = time.time()
            self.next_allowed_time = time.time() + 45.0  # Safe default until cooldown div updates

            # Step 4: Handle possible loot / reward popup
            browser.human_delay(1.0, 2.0, pause_checker=can_continue)
            loot_buttons = page.locator(".loot-button")
            if loot_buttons.count() >= 2:
                second_loot = loot_buttons.nth(1)
                if second_loot.is_visible():
                    loot_box = second_loot.bounding_box()
                    if loot_box:
                        page.mouse.move(
                            loot_box["x"] + random.randint(3, max(4, int(loot_box["width"] - 3))),
                            loot_box["y"] + random.randint(3, max(4, int(loot_box["height"] - 3))),
                            steps=random.randint(6, 12)
                        )
                    second_loot.click()
                    browser.human_delay(1.0, 1.5, pause_checker=can_continue)

            return ActionResult(
                success=True, 
                message="Expedition attack completed and loot checked",
                cooldown_seconds=48.0
            )

        except Exception as e:
            return ActionResult(success=False, message=f"Expedition error: {e}", retry_delay_seconds=15.0)
