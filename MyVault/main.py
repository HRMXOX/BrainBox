"""
main.py
نقطه ورود MyVault. فقط UI را run می‌کند.
"""

import sys
from pathlib import Path

# مطمئن شویم import از پوشه پروژه کار می‌کند
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
