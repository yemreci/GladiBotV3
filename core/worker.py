import time
import queue
import threading
from typing import List, Callable, Optional
from core.events import BotState
from core.browser import BrowserManager
from modules.base import BaseModule, BotTask, ActionResult
from config import BotConfig

class BotWorker:
    """
    Queue-Based Sequential Polling Worker.
    Runs in a dedicated thread to ensure Playwright's sync API remains 100% thread-safe.
    Implements cooperative Pause and Resume so that actions pause cleanly without breaking state.
    """

    def __init__(self, config: BotConfig, log_callback: Callable[[str, str], None], state_callback: Callable[[BotState], None]):
        self.config = config
        self.log = log_callback
        self.set_state_cb = state_callback
        
        self.state: BotState = BotState.STOPPED
        self.browser_manager = BrowserManager(url=config.lobby_url)
        
        self.modules: List[BaseModule] = []
        self.task_queue: queue.PriorityQueue = queue.PriorityQueue()
        
        # Thread control events
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        self._login_confirmed_event = threading.Event()

    def set_state(self, new_state: BotState):
        self.state = new_state
        if self.set_state_cb:
            self.set_state_cb(new_state)

    def register_modules(self, modules: List[BaseModule]):
        self.modules = modules

    def start(self):
        """Starts the worker thread."""
        if self._thread and self._thread.is_alive():
            self.log("Worker is already running.", "WARNING")
            return

        self._stop_event.clear()
        self._pause_event.clear()
        self._login_confirmed_event.clear()
        
        self._thread = threading.Thread(target=self._worker_loop, name="GladiBotWorker", daemon=True)
        self._thread.start()

    def pause(self):
        """Pauses the worker without destroying browser or queue state."""
        if self.state in (BotState.RUNNING, BotState.WAITING_COOLDOWN):
            self._pause_event.set()
            self.set_state(BotState.PAUSED)
            self.log("[F7 / PAUSE] Bot paused cleanly. Worker standing by.", "WARNING")

    def resume(self):
        """Resumes the worker from the paused state."""
        if self.state == BotState.PAUSED:
            self._pause_event.clear()
            self.set_state(BotState.RUNNING)
            self.log("[F6 / RESUME] Bot resumed. Polling active modules.", "SUCCESS")

    def stop(self):
        """Stops the worker and shuts down browser gracefully."""
        self._stop_event.set()
        self._pause_event.clear()
        self._login_confirmed_event.set()  # Unblock login wait if waiting
        self.set_state(BotState.STOPPED)
        self.log("[F8 / STOP] Bot stopping...", "INFO")

    def confirm_login(self):
        """Called by GUI / User once manual login is completed in the browser."""
        self._login_confirmed_event.set()

    def _can_continue(self) -> bool:
        """Helper callback passed to modules to check if action should halt."""
        return not self._stop_event.is_set() and not self._pause_event.is_set()

    def _wait_while_paused(self):
        """Sleeps efficiently while paused until resumed or stopped."""
        while self._pause_event.is_set() and not self._stop_event.is_set():
            self.browser_manager.pump_events(timeout_ms=200)

    def _wait_with_interrupt(self, seconds: float):
        """Sleeps in small increments to respond immediately to pause or stop requests."""
        elapsed = 0.0
        step = 0.25
        while elapsed < seconds:
            if self._stop_event.is_set():
                return
            if self._pause_event.is_set():
                self._wait_while_paused()
            wait_slice = min(step, seconds - elapsed)
            self.browser_manager.pump_events(timeout_ms=int(wait_slice * 1000))
            elapsed += wait_slice

    def _worker_loop(self):
        """Main lifecycle of the worker thread."""
        try:
            self.set_state(BotState.STARTING)
            self.log("Initializing browser environment...", "INFO")
            
            lobby_page = self.browser_manager.initialize(log_callback=self.log)
            self.log("Browser opened. Please log in manually and open the game tab (_blank).", "INFO")
            self.set_state(BotState.LOGGING_IN)
            self.log("Click 'Ready / Continue' in the UI once you are on your character's game page.", "WARNING")

            # Wait for user confirmation or auto-detection
            while not self._login_confirmed_event.is_set() and not self._stop_event.is_set():
                # Pump Playwright driver IPC events so context.pages and listeners update in real-time
                self.browser_manager.pump_events(timeout_ms=400)

                # Check if game page exists
                page = self.browser_manager.find_game_page()
                if page:
                    self.log(f"Detected game tab: {page.url}", "SUCCESS")
                    break

            if self._stop_event.is_set():
                return

            # Extra pump in case tab just finished opening when user clicked button
            self.browser_manager.pump_events(timeout_ms=300)
            game_page = self.browser_manager.find_game_page()
            if not game_page:
                self.log("Could not find Gladiatus game tab. Ensure you clicked into the game.", "ERROR")
                self.set_state(BotState.ERROR)
                return

            self.log(f"Active tab locked: {game_page.url}", "SUCCESS")
            self.set_state(BotState.RUNNING)
            self.log("Queue-Based Sequential Poller started. Ready to automate!", "SUCCESS")

            # ----------------- Main Polling & Worker Loop -----------------
            while not self._stop_event.is_set():
                # 1. Handle Pause state
                if self._pause_event.is_set():
                    self._wait_while_paused()
                    if self._stop_event.is_set():
                        break

                # 2. Check and replenish Task Queue from Modules
                if self.task_queue.empty():
                    for module in sorted(self.modules, key=lambda m: m.priority):
                        if not self._can_continue():
                            break
                        if not module.enabled:
                            continue
                        
                        task = module.evaluate(game_page, self.browser_manager)
                        if task:
                            self.log(f"Enqueued Task: [{task.name}] (Priority {task.priority})", "INFO")
                            self.task_queue.put(task)

                # 3. Process next Task in Queue
                if not self.task_queue.empty() and self._can_continue():
                    task: BotTask = self.task_queue.get()
                    self.log(f"Executing: {task.name}...", "INFO")
                    
                    # Execute task
                    result: ActionResult = task.execute_fn(
                        game_page, 
                        self.browser_manager, 
                        self._can_continue
                    )

                    if result.success:
                        self.log(f"[SUCCESS] {result.message}", "SUCCESS")
                    else:
                        self.log(f"[NOTICE] {result.message}", "WARNING")

                # 4. Wait for next poll interval (interruptible)
                if self._can_continue():
                    self._wait_with_interrupt(self.config.poll_interval_seconds)

        except Exception as e:
            self.log(f"Unexpected worker crash: {e}", "ERROR")
            self.set_state(BotState.ERROR)
        finally:
            self.log("Cleaning up browser session...", "INFO")
            self.browser_manager.close()
            self.set_state(BotState.STOPPED)
            self.log("Bot stopped completely.", "INFO")
