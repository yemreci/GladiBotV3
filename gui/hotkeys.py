from typing import Callable, Optional
from pynput import keyboard

class GlobalHotkeyManager:
    """Manages global hotkeys (e.g. F6 Start/Resume, F7 Pause, F8 Stop) across the OS."""

    def __init__(
        self,
        on_start_resume: Callable[[], None],
        on_pause: Callable[[], None],
        on_stop: Callable[[], None],
        key_start: str = "f6",
        key_pause: str = "f7",
        key_stop: str = "f8"
    ):
        self.on_start_resume = on_start_resume
        self.on_pause = on_pause
        self.on_stop = on_stop
        
        self.key_start = key_start.lower()
        self.key_pause = key_pause.lower()
        self.key_stop = key_stop.lower()
        
        self.listener: Optional[keyboard.GlobalHotKeys] = None

    def start(self):
        """Starts the global hotkey listener."""
        hotkey_map = {
            f"<{self.key_start}>": self.on_start_resume,
            f"<{self.key_pause}>": self.on_pause,
            f"<{self.key_stop}>": self.on_stop,
        }
        try:
            self.listener = keyboard.GlobalHotKeys(hotkey_map)
            self.listener.daemon = True
            self.listener.start()
        except Exception as e:
            print(f"Warning: Could not start global hotkey listener: {e}")

    def stop(self):
        """Stops the global hotkey listener."""
        if self.listener:
            try:
                self.listener.stop()
            except Exception:
                pass
            self.listener = None
