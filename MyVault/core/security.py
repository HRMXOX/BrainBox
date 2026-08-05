"""
core/security.py
مدیریت هش پسورد master (bcrypt) و رمزنگاری محتوای حساس (Fernet + PBKDF2HMAC).
کلید رمزنگاری از password + salt با PBKDF2HMAC استخراج می‌شود.
salt و hash در config.json کنار هم ولی به صورت جدا ذخیره می‌شوند.
"""

from __future__ import annotations
import base64
import json
import os
from pathlib import Path
from typing import Optional

import bcrypt
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

CONFIG_PATH = Path("config.json")
_PBKDF2_ITERATIONS = 600_000   # بر اساس ۲۰۲۴ OWASP
_SALT_BYTES = 16
_KEY_BYTES = 32


class SecurityVault:
    """امنیت برنامه: هش پسورد + رمزنگاری محتوا."""

    def __init__(self, config_path: Path | str = CONFIG_PATH) -> None:
        self.config_path = Path(config_path)
        self._config: dict = self._load_config()
        self._fernet: Optional[Fernet] = None  # بعد از unlock شدن

    # ──────────────────────────────────────────────
    # مدیریت config
    # ──────────────────────────────────────────────
    def _load_config(self) -> dict:
        if self.config_path.exists():
            with open(self.config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _save_config(self) -> None:
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(self._config, f, indent=2)

    # ──────────────────────────────────────────────
    # پسورد master
    # ──────────────────────────────────────────────
    def is_initialized(self) -> bool:
        return bool(self._config.get("master_hash"))

    def set_master_password(self, password: str) -> None:
        """اولین بار: salt و hash را می‌سازد."""
        if self.is_initialized():
            raise RuntimeError("master password قبلاً تنظیم شده.")
        if len(password) < 8:
            raise ValueError("پسورد حداقل باید ۸ کاراکتر باشد.")
        salt = os.urandom(_SALT_BYTES)
        pw_bytes = password.encode("utf-8")
        # bcrypt خودش salt را در hash embed می‌کند ولی salt جدا برای PBKDF2 لازم است
        bcrypt_hash = bcrypt.hashpw(pw_bytes, bcrypt.gensalt(rounds=12))
        self._config.update({
            "master_hash": bcrypt_hash.decode("utf-8"),
            "pbkdf2_salt": base64.b64encode(salt).decode("ascii"),
            "iterations": _PBKDF2_ITERATIONS,
        })
        self._save_config()

    def verify_master_password(self, password: str) -> bool:
        stored = self._config.get("master_hash")
        if not stored:
            return False
        try:
            return bcrypt.checkpw(password.encode("utf-8"),
                                  stored.encode("utf-8"))
        except (ValueError, TypeError):
            return False

    # ──────────────────────────────────────────────
    # کلید Fernet از password + salt
    # ──────────────────────────────────────────────
    def _derive_key(self, password: str) -> bytes:
        salt_b64 = self._config.get("pbkdf2_salt")
        if not salt_b64:
            raise RuntimeError("salt موجود نیست. master password stew 설정 نشده.")
        salt = base64.b64decode(salt_b64)
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=_KEY_BYTES,
            salt=salt,
            iterations=int(self._config.get("iterations", _PBKDF2_ITERATIONS)),
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode("utf-8")))
        return key

    def unlock(self, password: str) -> bool:
        """unlock بعد از verify موفق — کلید Fernet را در memory می‌سازد."""
        if not self.verify_master_password(password):
            return False
        self._fernet = Fernet(self._derive_key(password))
        return True

    def lock(self) -> None:
        self._fernet = None

    def is_unlocked(self) -> bool:
        return self._fernet is not None

    # ──────────────────────────────────────────────
    # رمزنگاری / دی‌کریپت
    # ──────────────────────────────────────────────
    def encrypt_text(self, text: str) -> str:
        if self._fernet is None:
            raise RuntimeError("ابتدا unlock کنید.")
        token = self._fernet.encrypt(text.encode("utf-8"))
        return token.decode("ascii")

    def decrypt_text(self, encrypted: str) -> str:
        if self._fernet is None:
            raise RuntimeError("ابتدا unlock کنید.")
        try:
            return self._fernet.decrypt(encrypted.encode("ascii")).decode("utf-8")
        except InvalidToken as exc:
            raise ValueError("داده رمزنگاری شده نامعتبر یا کلید اشتباه است.") from exc

    def change_master_password(self, old: str, new: str) -> bool:
        """تغییر پسورد master — لازم است تمام ciphertext هاưa re-encrypt شوند.
           caller مسئول re-encrypt کل دیتابیس است."""
        if not self.verify_master_password(old):
            return False
        if len(new) < 8:
            raise ValueError("پسورد جدید حداقل باید ۸ کاراکتر باشد.")
        # salt جدید
        salt = os.urandom(_SALT_BYTES)
        bcrypt_hash = bcrypt.hashpw(new.encode("utf-8"), bcrypt.gensalt(rounds=12))
        self._config.update({
            "master_hash": bcrypt_hash.decode("utf-8"),
            "pbkdf2_salt": base64.b64encode(salt).decode("ascii"),
            "iterations": _PBKDF2_ITERATIONS,
        })
        self._save_config()
        self._fernet = Fernet(self._derive_key(new))
        return True
