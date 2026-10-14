# GladiBot V3 - Workspace Conventions & Agent Rules

This document defines core behavioral constraints, coding patterns, and DOM conventions for all AI agents working in this repository.

## 1. Architectural Patterns
- **OOP Modularity**: Every game activity must subclass `BaseModule` from `modules.base`.
  - `evaluate(page, browser) -> Optional[BotTask]`: Fast, non-destructive DOM inspection. Returns `None` if on cooldown or conditions are not met.
  - `execute(page, browser, can_continue) -> ActionResult`: Carries out the action sequence. Must check `can_continue()` at step boundaries.
- **Queue-Based Sequential Poller**: Tasks are prioritized (`Healer: 1`, `Auction: 2`, `Expedition: 3`, `Dungeon: 4`). No continuous blocking loops.
- **Thread Safety**: Playwright runs exclusively in `BotWorker` thread. GUI and hotkeys communicate strictly via thread-safe `queue.Queue` and `threading.Event`.

## 2. Playwright & Browser Rules
- **No Blocking `time.sleep()`**: Never use Python's `time.sleep()` when waiting on browser state or inside delays. Use `page.wait_for_timeout(ms)` or `browser_manager.pump_events(ms)` to allow the Playwright driver IPC event loop to process browser events.
- **Humanized Interactions**: All clicks and inputs must simulate human cursor movement with randomized bezier-like steps, bounding box offsets, and randomized human delays.
- **Cooperative Pause**: Respect `can_continue()` between sub-steps so the bot pauses cleanly at transaction boundaries without corrupting page DOM state.

## 3. Gladiatus DOM & Multilingual Selectors
- **Attribute-First Matching**: When targeting buttons, always prefer resilient attributes (`name="dif2"`, `name="cancel"`, `class="map_label"`, IDs) before matching localized text.
- **Multilingual Support**: If text matching is necessary, support keyword lists covering Turkish, English, German, and Spanish rather than static single-language strings.
- **Server URL Matching**: Never hardcode specific server numbers. Use generic prefix matching `://s\d+.*\.gladiatus\.` and verify non-lobby status (`lobby`, `hub` strictly excluded).
- **Combat & Reports**: Dungeon combat loss/defeat is explicitly detected by the presence of `div.reportLose` / `.reportLose`.
- **Dungeon Encounters**: Active fightable encounters inside `#content` are identified by elements/images containing `onclick*="startFight"` (e.g. `startFight('2', '11226204');...`).
