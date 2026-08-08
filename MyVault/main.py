
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent))

import customtkinter as ctk
from ui.app_window import MainWindow


def main() -> None:
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    app = MainWindow()
    app.mainloop()


if __name__ == "__main__":
    main()
