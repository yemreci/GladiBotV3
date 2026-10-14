from config import BotConfig
from gui.app import GladiBotApp

def main():
    config = BotConfig.load()

    app = GladiBotApp(config)
    app.mainloop()

if __name__ == "__main__":
    main()