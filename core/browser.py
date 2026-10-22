import random
import time
import re
from typing import Optional, List, Any, Union
from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext, Locator, TimeoutError as PlaywrightTimeoutError

class BrowserManager:
    """Manages the Playwright browser lifecycle, tabs, and human-like interactions."""

    def __init__(self, url: str = "https://lobby.gladiatus.gameforge.com/en_GB/hub"):
        self.url = url
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.game_page: Optional[Page] = None
        self.tracked_pages: List[Page] = []
        self.log_callback = None
        self._is_initialized = False

    def log(self, message: str, level: str = "INFO"):
        """Logs a message to the UI console and stdout."""
        if self.log_callback:
            try:
                self.log_callback(message, level)
            except Exception:
                pass
        print(f"[{level}] {message}")

    def initialize(self, log_callback=None):
        """Starts Playwright and launches the browser."""
        self.log_callback = log_callback
        if self.log_callback:
            self.log("Launching Chrome browser...", "INFO")

        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(
            channel="chrome",
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--start-maximized"
            ]
        )
        self.context = self.browser.new_context(
            no_viewport=True,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        
        # Block slow/failing tracking scripts (e.g. pixelzirkus / pz.js) to speed up page loads
        self._setup_request_blocking(self.context)

        # Listen for new pages / tabs opening (e.g. clicking play / _blank in lobby)
        self.context.on("page", self._on_page_created)

        lobby_page = self.context.new_page()
        self._on_page_created(lobby_page)
        
        lobby_page.goto(self.url)
        self._is_initialized = True
        return lobby_page

    def _setup_request_blocking(self, context: BrowserContext):
        """
        Blocks slow or failing tracking scripts (such as pixelzirkus pz.js) across all tabs.
        Aborts matching requests immediately with ERR_BLOCKED_BY_CLIENT (matches uBlock Origin)
        and injects a harmless stub so game pages never hit undefined function errors.
        """
        blocked_pattern = re.compile(r"pixelzirkus\.gameforge\.com|/static/js/pz\.js")

        def handle_route(route):
            try:
                route.abort("blockedbyclient")
            except Exception:
                pass

        context.route(blocked_pattern, handle_route)

        # Safe defuser / stub in case inline game scripts call window.pz(...)
        try:
            context.add_init_script(
                "window.pz = window.pz || function() {}; window.pixelzirkus = window.pixelzirkus || function() {};"
            )
        except Exception:
            pass


    def _on_page_created(self, page: Page):
        """Internal callback whenever a new tab or window is opened."""
        if page not in self.tracked_pages:
            self.tracked_pages.append(page)
            page.on("close", lambda: self._on_page_closed(page))

    def _on_page_closed(self, page: Page):
        """Internal callback when a tab is closed."""
        if page in self.tracked_pages:
            self.tracked_pages.remove(page)
        if self.game_page is page:
            self.game_page = None

    def get_any_open_page(self) -> Optional[Page]:
        """Returns any currently open page to pump Playwright events."""
        for p in reversed(self.tracked_pages):
            try:
                if not p.is_closed():
                    return p
            except Exception:
                continue

        if self.context:
            for p in reversed(self.context.pages):
                try:
                    if not p.is_closed():
                        return p
                except Exception:
                    continue

        if self.browser:
            for ctx in self.browser.contexts:
                for p in reversed(ctx.pages):
                    try:
                        if not p.is_closed():
                            return p
                    except Exception:
                        continue
        return None

    def pump_events(self, timeout_ms: int = 500):
        """
        Pumps Playwright's internal event loop and message dispatcher.
        Never use time.sleep() directly when waiting for browser events, because time.sleep()
        blocks the Python thread and prevents Playwright from processing targetCreated/page events!
        """
        # 1. First try waiting for a new page event if context is active
        if self.context:
            try:
                new_p = self.context.wait_for_event("page", timeout=timeout_ms)
                if new_p:
                    self._on_page_created(new_p)
                    return
            except PlaywrightTimeoutError:
                pass
            except Exception:
                pass

        # 2. Otherwise use wait_for_timeout on an active open page to pump driver IPC
        active_p = self.get_any_open_page()
        if active_p and not active_p.is_closed():
            try:
                active_p.wait_for_timeout(timeout_ms)
                return
            except Exception:
                pass

        # 3. Fallback only if no pages exist at all
        time.sleep(timeout_ms / 1000.0)


    @staticmethod
    def is_game_page(page: Page) -> bool:
        """
        Strictly determines whether a given page is an active Gladiatus game tab.
        Strictly rejects lobby/hub pages and blank tabs.
        """
        try:
            if page.is_closed():
                return False
            url = page.url.lower()

            # Strictly reject lobby, hub, or blank tabs
            if any(term in url for term in ["lobby", "hub", "about:blank"]):
                return False

            # Must contain in-game indicator:
            # 1. Any server starting with 's' (e.g., https://s58-tr..., https://s1-en..., https://s201...)
            # 2. Or query/path indicators: 'mod=' or '/game/'
            has_server_prefix = bool(re.search(r"://s\d+.*\.gladiatus\.", url))
            has_game_mod = "mod=" in url or "/game/" in url

            if (has_server_prefix and "gladiatus" in url) or has_game_mod:
                return True

            # If URL is a gladiatus server but still loading, check if game elements are present
            if "gladiatus" in url:
                try:
                    if page.locator("#cooldown_bar_text_expedition, #header_values_hp_percent, #snavi_expedition").count() > 0:
                        return True
                except Exception:
                    pass

        except Exception:
            pass
        return False

    def find_game_page(self) -> Optional[Page]:
        """
        Finds the active Gladiatus game page across all browser contexts and tracked pages.
        Returns None if only the lobby/hub is open.
        """
        if not self.browser:
            return None

        # Collect all unique open pages
        all_pages: List[Page] = []
        for ctx in self.browser.contexts:
            for p in ctx.pages:
                if p not in all_pages:
                    all_pages.append(p)
        for p in self.tracked_pages:
            if p not in all_pages:
                all_pages.append(p)

        # Look in reverse (newest tabs first)
        for p in reversed(all_pages):
            try:
                if not p.is_closed() and self.is_game_page(p):
                    self.game_page = p
                    return p
            except Exception:
                continue

        return None

    def human_delay(self, min_sec: float = 0.5, max_sec: float = 1.5, page: Optional[Page] = None, pause_checker=None):
        """
        Sleeps with a randomized delay using Playwright's wait_for_timeout
        to keep the event loop active without blocking message dispatch.
        """
        target = random.uniform(min_sec, max_sec)
        elapsed = 0.0
        slice_sec = 0.1
        target_page = page or self.game_page or self.get_any_open_page()

        while elapsed < target:
            if pause_checker and not pause_checker():
                return
            step = min(slice_sec, target - elapsed)
            step_ms = int(step * 1000)

            if target_page and not target_page.is_closed():
                try:
                    target_page.wait_for_timeout(step_ms)
                except Exception:
                    time.sleep(step)
            else:
                time.sleep(step)
            elapsed += step

    def human_move_and_click(self, page: Page, target: Any, pause_checker=None) -> bool:
        """Simulates realistic human mouse movement with bezier-like steps and randomized clicking."""
        if pause_checker and not pause_checker():
            return False

        try:
            if isinstance(target, str):
                element = page.locator(target).first
            else:
                element = target.first if hasattr(target, "first") else target

            if not element.is_visible():
                return False

            box = element.bounding_box()
            if box:
                # Add random offset inside element
                pad_x = min(5, box["width"] * 0.2)
                pad_y = min(5, box["height"] * 0.2)
                target_x = box["x"] + random.uniform(pad_x, max(pad_x, box["width"] - pad_x))
                target_y = box["y"] + random.uniform(pad_y, max(pad_y, box["height"] - pad_y))
                
                # Move in randomized steps
                steps = random.randint(6, 16)
                page.mouse.move(target_x, target_y, steps=steps)
                self.human_delay(0.15, 0.4, page=page, pause_checker=pause_checker)

            element.click()
            return True
        except Exception:
            return False

    def close(self):
        """Closes browser and cleans up Playwright."""
        try:
            if self.context:
                self.context.close()
            if self.browser:
                self.browser.close()
            if self.playwright:
                self.playwright.stop()
        except Exception:
            pass
        finally:
            self.game_page = None
            self.tracked_pages.clear()
            self.context = None
            self.browser = None
            self.playwright = None
            self._is_initialized = False
