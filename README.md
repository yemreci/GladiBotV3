# ⚔ GladiBot V3

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Playwright](https://img.shields.io/badge/Playwright-Automation-orange.svg)](https://playwright.dev/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey.svg)]()

A modular, event-driven automation framework and desktop application for *Gladiatus*, engineered with **Playwright**, **Python**, and a **Queue-Based Sequential Polling Worker** pattern.

---

## 🌟 Key Architecture & Highlights

- **Queue-Based Sequential Polling Worker**:
  - Replaces fragile, monolithic `while True: sleep(N)` loops with an event-driven task priority queue.
  - Slices wait intervals into interruptible ticks, allowing the bot to react to pause commands and page transitions in milliseconds.
- **Cooperative Pause & Resume (AHK-Style)**:
  - Seamless global hotkey controls (**F6**, **F7**, **F8**) that work system-wide even when minimized.
  - Pausing completes the current atomic interaction safely, preserving browser session state and preventing desynchronization.
- **Pluggable OOP Module System**:
  - Every in-game activity inherits from `BaseModule` with standardized evaluation (`evaluate`) and execution (`execute`) contracts.
  - Priority-based task dispatch ensures critical routines (e.g. healing) always precede secondary routines.
- **Modern Desktop GUI**:
  - Sleek, dark-themed control center built with Tkinter.
  - Live color-coded console logs (`[INFO]`, `[SUCCESS]`, `[WARNING]`, `[ERROR]`).
  - Runtime toggles for module activation and parameters.
- **Standalone Binary Packaging**:
  - Build script included to package the entire application into a standalone Windows `.exe` via PyInstaller.

---

## 📊 Module Roadmap

| Module | Status | Priority | Description |
| :--- | :---: | :---: | :--- |
| **Expedition** | 🟢 **Stable** | Priority 3 | Automated navigation, cooldown tracking, mob targeting, and reward/loot handling. |
| **Dungeon** | 🟡 *In Progress* | Priority 4 | Dungeon room progression and mob/boss combat *(Blueprint template ready)*. |
| **Auto-Heal** | 🟡 *In Progress* | Priority 1 | Real-time HP monitoring and automatic food/potion consumption *(Blueprint template ready)*. |
| **Auction House** | 🟡 *In Progress* | Priority 2 | Watcher for expiring items and automated bidding within gold thresholds *(Blueprint template ready)*. |

---

## 🖥️ System Architecture

```
                    ┌────────────────────────────┐
                    │      BaseModule (OOP)      │
                    └─────────────┬──────────────┘
                                  │
          ┌───────────────────────┼───────────────────────┐
          ▼                       ▼                       ▼
  [ExpeditionModule]      [DungeonModule]          [HealerModule]
          │                       │                       │
          └───────────────────────┼───────────────────────┘
                                  │ evaluate()
                                  ▼
┌──────────────────┐        ┌───────────┐         ┌─────────────────────────┐
│  Desktop GUI &   │        │  Priority │         │     BotWorker Loop      │
│  Global Hotkeys  ├───────►│ TaskQueue ├────────►│  Executes 1 Task at     │
│  (F6 / F7 / F8)  │Control │           │ Poll/Pop│  a time (Atomic & Safe) │
└──────────────────┘        └───────────┘         └────────────┬────────────┘
                                                               │
                                                               ▼
                                                  ┌─────────────────────────┐
                                                  │ Playwright Chrome Host  │
                                                  │ (Live Browser Session)  │
                                                  └─────────────────────────┘
```

---

## 🚀 Quickstart Guide

### Prerequisites
- **Python 3.10+** installed on your system.
- **Google Chrome** installed (used by Playwright via `channel="chrome"`).

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/GladiBotV3.git
   cd GladiBotV3
   ```

2. **Install required dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Install Playwright browser binaries (if needed):**
   ```bash
   playwright install
   ```

### Running the Bot

Start the desktop application:
```bash
python Gladibot.py
```

1. Click **`▶ Start (F6)`** in the GUI.
2. The browser will open the Gameforge lobby.
3. Log into your account manually and select your character to open your game tab.
4. The bot will automatically detect the game server tab (e.g. `s*.gladiatus.gameforge.com`) and begin processing enabled modules.

---

## 🎮 Hotkeys & Controls

| Command | Shortcut | Description |
| :--- | :---: | :--- |
| **Start / Resume** | **`F6`** | Launches the engine or resumes execution from a paused state. |
| **Pause** | **`F7`** | Atomically suspends the worker loop at the next safe boundary. |
| **Stop** | **`F8`** | Gracefully terminates tasks and closes the browser context. |

---

## 📦 Building a Standalone Executable (.exe)

You can compile the bot into a standalone Windows executable with PyInstaller:

```bash
python build_exe.py
```

Once compilation completes, the packaged application will be generated in:
```
dist/GladiBotV3/GladiBotV3.exe
```

---

## 🛠️ Developing New Modules

Adding a new feature is straightforward thanks to the modular OOP design:

1. Create a new file in `modules/` (e.g. `modules/arena.py`).
2. Subclass `BaseModule` from `modules.base`:

```python
from modules.base import BaseModule, BotTask, ActionResult

class ArenaModule(BaseModule):
    def __init__(self, enabled=True, priority=3):
        super().__init__(name="Arena", enabled=enabled, priority=priority)

    def evaluate(self, page, browser) -> BotTask | None:
        # Check cooldown / conditions on DOM
        return BotTask(name="Fight Arena", module_name=self.name, priority=self.priority, execute_fn=self.execute)

    def execute(self, page, browser, can_continue) -> ActionResult:
        # Perform humanized interactions
        return ActionResult(success=True, message="Arena match complete")
```

3. Register your module in `gui/app.py` and `core/worker.py`.

---

## ⚠️ Disclaimer

This project is developed for educational, architectural, and research purposes regarding browser automation, event loops, and UI testing with Playwright. Use of automation tools may violate the Terms of Service of third-party platforms. The authors and contributors assume no liability for misuse, account penalties, or bans resulting from the use of this software.

---

## 📄 License

Distributed under the [MIT License](LICENSE).
