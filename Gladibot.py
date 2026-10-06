import sys
import argparse
from config import BotConfig
from gui.app import GladiBotApp

def main():
    parser = argparse.ArgumentParser(description="GladiBot V3 - Modular Automation Engine")
    parser.add_argument("--cli", action="store_true", help="Run in CLI headless/console mode instead of GUI")
    args = parser.parse_args()

    config = BotConfig.load()

    # Launch GUI
    app = GladiBotApp(config)
    app.mainloop()

if __name__ == "__main__":
    main()