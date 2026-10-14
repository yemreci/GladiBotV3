import time
import queue
import tkinter as tk
from tkinter import ttk, scrolledtext
from typing import Optional
from core.events import BotState, LogMessage
from core.worker import BotWorker
from modules.expedition import ExpeditionModule
from modules.dungeon import DungeonModule
from modules.healer import HealerModule
from modules.auction import AuctionModule
from gui.hotkeys import GlobalHotkeyManager
from config import BotConfig

class GladiBotApp(tk.Tk):
    """Modern Dark-Theme Desktop GUI for GladiBot."""

    def __init__(self, config: BotConfig):
        super().__init__()
        self.config = config
        
        self.title("GladiBot V3 - Modular Automation Engine")
        self.geometry("820x680")
        self.minsize(740, 580)
        self.configure(bg="#18181b")

        # Thread-safe message queue for UI updates
        self.ui_queue = queue.Queue()

        # Modules
        self.expedition_module = ExpeditionModule(
            enabled=self.config.expedition_enabled, 
            target_mob_index=self.config.expedition_mob_index
        )
        self.dungeon_module = DungeonModule(
            enabled=self.config.dungeon_enabled,
            restart_on_loss=self.config.dungeon_restart_on_loss
        )
        self.healer_module = HealerModule(
            enabled=self.config.healer_enabled, 
            min_hp_percent=self.config.min_hp_percent
        )
        self.auction_module = AuctionModule(
            enabled=self.config.auction_enabled, 
            max_bid_gold=self.config.max_bid_gold
        )

        # Worker instance
        self.worker = BotWorker(
            config=self.config,
            log_callback=self.queue_log,
            state_callback=self.queue_state
        )
        self.worker.register_modules([
            self.healer_module,
            self.auction_module,
            self.expedition_module,
            self.dungeon_module
        ])

        # Global Hotkeys (F6/F7/F8)
        self.hotkeys = GlobalHotkeyManager(
            on_start_resume=self.on_hotkey_start_resume,
            on_pause=self.on_pause_clicked,
            on_stop=self.on_stop_clicked,
            key_start=self.config.hotkey_start_resume,
            key_pause=self.config.hotkey_pause,
            key_stop=self.config.hotkey_stop
        )
        self.hotkeys.start()

        self._build_styles()
        self._build_ui()

        # Start periodic queue processor
        self.after(100, self._process_ui_queue)

        # Handle window close
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def _build_styles(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        
        # Configure frames and labels
        style.configure("TFrame", background="#18181b")
        style.configure("Card.TFrame", background="#27272a", relief="flat")
        style.configure("TLabel", background="#18181b", foreground="#f4f4f5", font=("Segoe UI", 10))
        style.configure("Card.TLabel", background="#27272a", foreground="#f4f4f5", font=("Segoe UI", 10))
        style.configure("Title.TLabel", background="#18181b", foreground="#fafafa", font=("Segoe UI", 15, "bold"))
        style.configure("Subtitle.TLabel", background="#18181b", foreground="#a1a1aa", font=("Segoe UI", 9))
        style.configure("Badge.TLabel", font=("Segoe UI", 10, "bold"), padding=4)
        style.configure("CardHeader.TLabel", background="#27272a", foreground="#38bdf8", font=("Segoe UI", 11, "bold"))
        
        # Checkbuttons
        style.configure("TCheckbutton", background="#27272a", foreground="#f4f4f5", font=("Segoe UI", 10))
        style.map("TCheckbutton",
                  background=[("active", "#27272a")],
                  foreground=[("active", "#ffffff")])

    def _build_ui(self):
        # Header container
        header_frame = ttk.Frame(self, padding=(16, 12))
        header_frame.pack(fill="x")

        ttk.Label(header_frame, text="⚔ GLADIBOT V3", style="Title.TLabel").pack(anchor="w")
        ttk.Label(header_frame, text="Queue-Based Sequential Automation • F6 Start/Resume • F7 Pause • F8 Stop", style="Subtitle.TLabel").pack(anchor="w")

        # Top Control & Status Card
        ctrl_card = ttk.Frame(self, style="Card.TFrame", padding=14)
        ctrl_card.pack(fill="x", padx=16, pady=6)

        # Status badge line
        status_row = ttk.Frame(ctrl_card, style="Card.TFrame")
        status_row.pack(fill="x", pady=(0, 10))

        ttk.Label(status_row, text="Current State:", style="Card.TLabel", font=("Segoe UI", 10, "bold")).pack(side="left")
        self.status_badge = tk.Label(
            status_row, 
            text="STOPPED", 
            bg="#3f3f46", 
            fg="#ffffff", 
            font=("Segoe UI", 9, "bold"), 
            padx=8, 
            pady=2, 
            relief="flat"
        )
        self.status_badge.pack(side="left", padx=8)

        # Buttons row
        btn_row = ttk.Frame(ctrl_card, style="Card.TFrame")
        btn_row.pack(fill="x")

        self.btn_start = tk.Button(
            btn_row, text="▶ Start (F6)", bg="#22c55e", fg="#ffffff", activebackground="#16a34a",
            font=("Segoe UI", 9, "bold"), relief="flat", padx=12, pady=6, cursor="hand2",
            command=self.on_start_clicked
        )
        self.btn_start.pack(side="left", padx=(0, 6))

        self.btn_pause = tk.Button(
            btn_row, text="⏸ Pause (F7)", bg="#f59e0b", fg="#ffffff", activebackground="#d97706",
            font=("Segoe UI", 9, "bold"), relief="flat", padx=12, pady=6, cursor="hand2",
            state="disabled", command=self.on_pause_clicked
        )
        self.btn_pause.pack(side="left", padx=6)

        self.btn_resume = tk.Button(
            btn_row, text="▶ Resume (F6)", bg="#06b6d4", fg="#ffffff", activebackground="#0891b2",
            font=("Segoe UI", 9, "bold"), relief="flat", padx=12, pady=6, cursor="hand2",
            state="disabled", command=self.on_resume_clicked
        )
        self.btn_resume.pack(side="left", padx=6)

        self.btn_stop = tk.Button(
            btn_row, text="⏹ Stop (F8)", bg="#ef4444", fg="#ffffff", activebackground="#dc2626",
            font=("Segoe UI", 9, "bold"), relief="flat", padx=12, pady=6, cursor="hand2",
            state="disabled", command=self.on_stop_clicked
        )
        self.btn_stop.pack(side="left", padx=6)

        self.btn_ready = tk.Button(
            btn_row, text="✔ I Have Logged In (Continue)", bg="#6366f1", fg="#ffffff", activebackground="#4f46e5",
            font=("Segoe UI", 9, "bold"), relief="flat", padx=12, pady=6, cursor="hand2",
            state="disabled", command=self.on_confirm_login_clicked
        )
        self.btn_ready.pack(side="right")

        # Modules Settings Frame
        mod_card = ttk.Frame(self, style="Card.TFrame", padding=14)
        mod_card.pack(fill="x", padx=16, pady=6)

        ttk.Label(mod_card, text="AUTOMATION MODULES & CONFIGURATION", style="CardHeader.TLabel").pack(anchor="w", pady=(0, 8))

        grid_frame = ttk.Frame(mod_card, style="Card.TFrame")
        grid_frame.pack(fill="x")

        # Expedition toggle
        self.var_exp = tk.BooleanVar(value=self.config.expedition_enabled)
        cb_exp = ttk.Checkbutton(grid_frame, text="Expeditions (Attack & Loot)", variable=self.var_exp, command=self.on_module_toggle)
        cb_exp.grid(row=0, column=0, sticky="w", padx=6, pady=4)

        ttk.Label(grid_frame, text="Mob Slot:", style="Card.TLabel").grid(row=0, column=1, sticky="e", padx=(10, 2))
        self.var_mob = tk.IntVar(value=self.config.expedition_mob_index)
        spin_mob = ttk.Spinbox(grid_frame, from_=1, to=4, width=3, textvariable=self.var_mob, command=self.on_module_toggle)
        spin_mob.grid(row=0, column=2, sticky="w", padx=2)

        # Dungeon toggle
        self.var_dungeon = tk.BooleanVar(value=self.config.dungeon_enabled)
        cb_dun = ttk.Checkbutton(grid_frame, text="Dungeons (Map & Bosses)", variable=self.var_dungeon, command=self.on_module_toggle)
        cb_dun.grid(row=0, column=3, sticky="w", padx=(20, 6), pady=4)

        self.var_dungeon_restart = tk.BooleanVar(value=self.config.dungeon_restart_on_loss)
        cb_dun_restart = ttk.Checkbutton(grid_frame, text="Restart on Loss", variable=self.var_dungeon_restart, command=self.on_module_toggle)
        cb_dun_restart.grid(row=0, column=4, sticky="w", padx=(6, 6), pady=4)

        # Healer toggle (WIP)
        self.var_heal = tk.BooleanVar(value=self.config.healer_enabled)
        cb_heal = ttk.Checkbutton(grid_frame, text="Auto-Heal [WIP]", variable=self.var_heal, command=self.on_module_toggle)
        cb_heal.grid(row=1, column=0, sticky="w", padx=6, pady=4)

        ttk.Label(grid_frame, text="Min HP %:", style="Card.TLabel").grid(row=1, column=1, sticky="e", padx=(10, 2))
        self.var_min_hp = tk.IntVar(value=self.config.min_hp_percent)
        spin_hp = ttk.Spinbox(grid_frame, from_=10, to=90, increment=5, width=4, textvariable=self.var_min_hp, command=self.on_module_toggle)
        spin_hp.grid(row=1, column=2, sticky="w", padx=2)

        # Auction toggle (WIP)
        self.var_auction = tk.BooleanVar(value=self.config.auction_enabled)
        cb_auc = ttk.Checkbutton(grid_frame, text="Auction Monitor [WIP]", variable=self.var_auction, command=self.on_module_toggle)
        cb_auc.grid(row=1, column=3, sticky="w", padx=(20, 6), pady=4)

        # Live Console Log Frame
        log_card = ttk.Frame(self, style="Card.TFrame", padding=12)
        log_card.pack(fill="both", expand=True, padx=16, pady=(6, 16))

        log_hdr = ttk.Frame(log_card, style="Card.TFrame")
        log_hdr.pack(fill="x", pady=(0, 6))

        ttk.Label(log_hdr, text="ACTIVITY LOG CONSOLE", style="CardHeader.TLabel").pack(side="left")
        btn_clear = tk.Button(
            log_hdr, text="Clear Log", bg="#3f3f46", fg="#e4e4e7", relief="flat", font=("Segoe UI", 8),
            command=self.clear_log, padx=8, pady=2
        )
        btn_clear.pack(side="right")

        self.log_text = scrolledtext.ScrolledText(
            log_card, bg="#09090b", fg="#e4e4e7", font=("Consolas", 9),
            insertbackground="#ffffff", relief="flat", borderwidth=0
        )
        self.log_text.pack(fill="both", expand=True)

        # Setup log tags
        self.log_text.tag_config("INFO", foreground="#93c5fd")
        self.log_text.tag_config("SUCCESS", foreground="#4ade80")
        self.log_text.tag_config("WARNING", foreground="#fcd34d")
        self.log_text.tag_config("ERROR", foreground="#f87171")
        self.log_text.tag_config("TIME", foreground="#71717a")

    def queue_log(self, text: str, level: str = "INFO"):
        """Thread-safe enqueue for logging."""
        timestamp = time.strftime("%H:%M:%S")
        self.ui_queue.put(("LOG", LogMessage(timestamp=timestamp, level=level, text=text)))

    def queue_state(self, state: BotState):
        """Thread-safe enqueue for state updates."""
        self.ui_queue.put(("STATE", state))

    def _process_ui_queue(self):
        """Processes logs and state changes on the Tkinter main thread."""
        while not self.ui_queue.empty():
            msg_type, data = self.ui_queue.get()
            if msg_type == "LOG":
                log_msg: LogMessage = data
                self.log_text.insert(tk.END, f"[{log_msg.timestamp}] ", "TIME")
                self.log_text.insert(tk.END, f"[{log_msg.level}] ", log_msg.level)
                self.log_text.insert(tk.END, f"{log_msg.text}\n")
                self.log_text.see(tk.END)
            elif msg_type == "STATE":
                self.update_state_ui(data)

        self.after(100, self._process_ui_queue)

    def update_state_ui(self, state: BotState):
        state_colors = {
            BotState.STOPPED: ("#3f3f46", "#ffffff"),
            BotState.STARTING: ("#3b82f6", "#ffffff"),
            BotState.LOGGING_IN: ("#8b5cf6", "#ffffff"),
            BotState.RUNNING: ("#22c55e", "#ffffff"),
            BotState.PAUSED: ("#f59e0b", "#000000"),
            BotState.WAITING_COOLDOWN: ("#06b6d4", "#ffffff"),
            BotState.ERROR: ("#ef4444", "#ffffff"),
        }
        bg, fg = state_colors.get(state, ("#3f3f46", "#ffffff"))
        self.status_badge.config(text=state.value, bg=bg, fg=fg)

        # Control button states
        if state == BotState.STOPPED or state == BotState.ERROR:
            self.btn_start.config(state="normal")
            self.btn_pause.config(state="disabled")
            self.btn_resume.config(state="disabled")
            self.btn_stop.config(state="disabled")
            self.btn_ready.config(state="disabled")
        elif state == BotState.LOGGING_IN:
            self.btn_start.config(state="disabled")
            self.btn_pause.config(state="disabled")
            self.btn_resume.config(state="disabled")
            self.btn_stop.config(state="normal")
            self.btn_ready.config(state="normal")
        elif state == BotState.RUNNING:
            self.btn_start.config(state="disabled")
            self.btn_pause.config(state="normal")
            self.btn_resume.config(state="disabled")
            self.btn_stop.config(state="normal")
            self.btn_ready.config(state="disabled")
        elif state == BotState.PAUSED:
            self.btn_start.config(state="disabled")
            self.btn_pause.config(state="disabled")
            self.btn_resume.config(state="normal")
            self.btn_stop.config(state="normal")
            self.btn_ready.config(state="disabled")

    def on_module_toggle(self):
        self.expedition_module.enabled = self.var_exp.get()
        self.expedition_module.target_mob_index = self.var_mob.get()
        self.dungeon_module.enabled = self.var_dungeon.get()
        self.dungeon_module.restart_on_loss = self.var_dungeon_restart.get()
        self.healer_module.enabled = self.var_heal.get()
        self.healer_module.min_hp_percent = self.var_min_hp.get()
        self.auction_module.enabled = self.var_auction.get()
        
        # Sync to config
        self.config.expedition_enabled = self.var_exp.get()
        self.config.expedition_mob_index = self.var_mob.get()
        self.config.dungeon_enabled = self.var_dungeon.get()
        self.config.dungeon_restart_on_loss = self.var_dungeon_restart.get()
        self.config.healer_enabled = self.var_heal.get()
        self.config.min_hp_percent = self.var_min_hp.get()
        self.config.auction_enabled = self.var_auction.get()
        self.config.save()

    def on_start_clicked(self):
        self.on_module_toggle()
        self.worker.start()

    def on_pause_clicked(self):
        self.worker.pause()

    def on_resume_clicked(self):
        self.worker.resume()

    def on_stop_clicked(self):
        self.worker.stop()

    def on_confirm_login_clicked(self):
        self.worker.confirm_login()

    def on_hotkey_start_resume(self):
        if self.worker.state == BotState.STOPPED:
            self.on_start_clicked()
        elif self.worker.state == BotState.PAUSED:
            self.on_resume_clicked()

    def clear_log(self):
        self.log_text.delete("1.0", tk.END)

    def on_close(self):
        self.hotkeys.stop()
        self.worker.stop()
        self.destroy()
