"""
ui/login_window.py
پنجره لاگین — ساخت پسورد اولین بار یا ورود.
"""

from __future__ import annotations
import customtkinter as ctk

from core.security import SecurityVault


class LoginWindow(ctk.CTkToplevel):
    """پنجره لاگین modal. اگر master password هنوز تنظیم نشده، setup می‌کند."""

    def __init__(self, master, security: SecurityVault, on_success: callable):
        super().__init__(master)
        self.security = security
        self.on_success = on_success

        self.title("ورود به BrainBox")
        self.geometry("360x260")
        self.resizable(False, False)
        self.configure(fg_color=("#f5f5f5", "#181818"))

        # modal
        self.transient(master)
        self.grab_set()

        self._build_ui()

    def _build_ui(self) -> None:
        ctk.CTkLabel(
            self, text="BrainBox",
            font=ctk.CTkFont(family="B Nazanin", size=24, weight="bold"),
        ).pack(pady=(28, 8))

        if self.security.is_initialized():
            self._mode = "login"
            hint = "رمز را وارد کنید"
            btn_text = "ورود"
        else:
            self._mode = "setup"
            hint = "یک رمز اصلی (حداقل ۸ کاراکتر) بسازید"
            btn_text = "ایجاد و ورود"

        self.pwd_entry = ctk.CTkEntry(
            self, show="•", placeholder_text=hint, width=240,
            font=ctk.CTkFont(family="B Nazanin", size=16),
            justify="right",
        )
        self.pwd_entry.pack(pady=6)
        self.pwd_entry.bind("<Return>", lambda e: self._submit())

        self.error_lbl = ctk.CTkLabel(
            self, text="", text_color=("#cc0000", "#ff6b6b"),
            font=ctk.CTkFont(family="B Nazanin", size=18),
        )
        self.error_lbl.pack(pady=(0, 6))

        ctk.CTkButton(
            self, text=btn_text, width=200,
            font=ctk.CTkFont(family="B Nazanin", size=16),
            command=self._submit,
        ).pack(pady=4)

        self.pwd_entry.focus_set()

    def _submit(self) -> None:
        pwd = self.pwd_entry.get()
        if not pwd:
            self.error_lbl.configure(text="رمز خالیه.")
            return
        try:
            if self._mode == "setup":
                self.security.set_master_password(pwd)
            if self.security.unlock(pwd):
                self.on_success()
                self.destroy()
            else:
                self.error_lbl.configure(text="رمز اشتباه.")
        except ValueError as e:
            self.error_lbl.configure(text=str(e))
