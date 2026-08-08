

from __future__ import annotations
import json
import zipfile
import tempfile
import os
from datetime import datetime
from tkinter import filedialog, messagebox

import customtkinter as ctk

from core.database import DatabaseManager
from core.security import SecurityVault
from ui.components import ItemCard
from ui.login_window import LoginWindow


IDLE_TIMEOUT_MS = 5 * 60 * 1000   
HEX_KEY = 0       
APP_FONT = ("B Nazanin", 13)


class MainWindow(ctk.CTk):
    def __init__(self, db_path: str = "vault.db"):
        super().__init__()
        self.db = DatabaseManager(db_path)
        self.security = SecurityVault()

        self.title(" BrainBox ")
        self.geometry("900x600")
        self.minsize(700, 500)
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self._current_category_id: int | None = None
        self._current_query: str = ""
        self._last_activity_ts: float = 0

        self._build_ui()
        self._bind_idle_events()

      
        self.after(100, self._ensure_unlocked)
        self.after(10_000, self._check_idle)     

 
    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

    
        header = ctk.CTkFrame(self, fg_color=("#eaeaea", "#222222"),
                              corner_radius=0, height=64)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(1, weight=1)

        self.search_entry = ctk.CTkEntry(
            header, placeholder_text="جستجو",
            font=APP_FONT, justify="right", height=38,
        )
        self.search_entry.grid(row=0, column=1, padx=10, pady=12, sticky="ew")
        self.search_entry.bind("<KeyRelease>", self._on_search)

        self.add_btn = ctk.CTkButton(
            header, text=" افزودن آیتم",
            font=APP_FONT, width=130, height=38,
            command=self._open_add_dialog,
        )
        self.add_btn.grid(row=0, column=2, padx=(0, 10), pady=12)

 
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.grid(row=1, column=0, sticky="nsew")
        body.grid_columnconfigure(0, weight=1)
        body.grid_columnconfigure(1, weight=0)
        body.grid_rowconfigure(0, weight=1)


        self.content_frame = ctk.CTkScrollableFrame(
            body, label_text="",
            fg_color=("#f9f9f9", "#1a1a1a"),
        )
        self.content_frame.grid(row=0, column=0, sticky="nsew", padx=(6, 0))
        self.content_frame.grid_columnconfigure(0, weight=1)

  
        self.sidebar = ctk.CTkScrollableFrame(
            body, width=200, label_text="دسته‌بندی‌ها",
            fg_color=("#f0f0f0", "#242424"),
        )
        self.sidebar.grid(row=0, column=1, sticky="ns", padx=(0, 6))
        self.sidebar.grid_columnconfigure(0, weight=1)

       
        footer = ctk.CTkFrame(self, height=40, fg_color=("#e0e0e0", "#1f1f1f"),
                              corner_radius=0)
        footer.grid(row=2, column=0, sticky="ew")
        ctk.CTkButton(
            footer, text=" بکاپ گیری",
            font=APP_FONT, width=130, height=28,
            command=self._do_backup,
        ).pack(side="right", padx=8, pady=6)
        ctk.CTkButton(
            footer, text="قفل برنامه",
            font=APP_FONT, width=110, height=28,
            fg_color=("#cc3333", "#7a1f1f"),
            command=self._manual_lock,
        ).pack(side="right", padx=4, pady=6)

        self._render_categories()

    def _render_categories(self) -> None:
        for w in self.sidebar.winfo_children():
            w.destroy()
        cats = self.db.list_categories()
   
        all_btn = ctk.CTkButton(
            self.sidebar, text="🗂 همه",
            font=APP_FONT, height=32,
            fg_color="transparent",
            border_width=1, border_color=("#cccccc", "#444444"),
            text_color=("#222", "#eee"),
            command=lambda: self._select_category(None),
        )
        all_btn.pack(fill="x", padx=4, pady=4)
        for c in cats:
            btn = ctk.CTkButton(
                self.sidebar,
                text=f"{c['icon'] or ''} {c['name']}",
                font=APP_FONT, height=32,
                fg_color="transparent",
                border_width=1, border_color=("#cccccc", "#444444"),
                text_color=("#222", "#eee"),
                command=lambda cid=c["id"]: self._select_category(cid),
            )
            btn.pack(fill="x", padx=4, pady=4)


    def _select_category(self, cat_id: int | None) -> None:
        self._current_category_id = cat_id
        if cat_id is None:
            items = self.db.get_all_items()
        else:
            items = self.db.get_items_by_category(cat_id)
        self._render_items(items)

    def _on_search(self, _event=None) -> None:
        q = self.search_entry.get().strip()
        self._current_query = q
        if q:
            items = self.db.search(q)
        elif self._current_category_id is None:
            items = self.db.get_all_items()
        else:
            items = self.db.get_items_by_category(self._current_category_id)
        self._render_items(items)

    def _render_items(self, items: list[dict]) -> None:
        for w in self.content_frame.winfo_children():
            w.destroy()
        if not items:
            ctk.CTkLabel(
                self.content_frame, text="موردی یافت نشد ",
                font=ctk.CTkFont(family="B Nazanin", size=22),
            ).pack(pady=80)
            return
        for it in items:
            content = it["content"]
     
            if it["item_type"] == "password" and self.security.is_unlocked():
                try:
                    content = self.security.decrypt_text(it["content"])
                except ValueError:
                    content = "<قفل شد>"
            card = ItemCard(
                self.content_frame,
                item_id=it["id"],
                title=it["title"],
                content=content,
                item_type=it["item_type"],
                tags=it.get("tags") or "",
                on_delete=self._delete_item,
            )
            card.pack(fill="x", padx=8, pady=6)

    def _delete_item(self, item_id: int) -> None:
        if messagebox.askyesno("تأیید", "میخواید آیتم حذف شه؟ "):
            self.db.delete_item(item_id)
            self._on_search()

    
    def _open_add_dialog(self) -> None:
        if not self.security.is_unlocked():
            self._ensure_unlocked()
            return
        dlg = ctk.CTkToplevel(self)
        dlg.title("افزودن آیتم")
        dlg.geometry("420x420")
        dlg.transient(self)
        dlg.grab_set()
        dlg.configure(fg_color=("#f5f5f5", "#181818"))

        ctk.CTkLabel(dlg, text=" اضافه کردن آیتم جدید",
                     font=ctk.CTkFont(family="B Nazanin", size=20, weight="bold")
                     ).pack(pady=10)

        cats = self.db.list_categories()
        cat_names = [f"{c['icon']} {c['name']}" for c in cats]
        cat_ids = [c["id"] for c in cats]

        
        type_var = ctk.StringVar(value="note")
        ctk.CTkLabel(dlg, text="نوع:", font=APP_FONT).pack(anchor="e", padx=20)
        type_seg = ctk.CTkSegmentedButton(
            dlg, values=["note", "link", "password"],
            variable=type_var, font=APP_FONT,
        )
        type_seg.pack(fill="x", padx=20, pady=4)

        
        ctk.CTkLabel(dlg, text="دسته‌بندی:", font=APP_FONT).pack(anchor="e",
                                                                   padx=20, pady=(8, 0))
        cat_var = ctk.StringVar(value=cat_names[0] if cat_names else "")
        cat_menu = ctk.CTkOptionMenu(dlg, variable=cat_var, values=cat_names,
                                    font=APP_FONT)
        cat_menu.pack(fill="x", padx=20, pady=4)

        
        ctk.CTkLabel(dlg, text="عنوان", font=APP_FONT).pack(anchor="e", padx=20,
                                                               pady=(8, 0))
        title_entry = ctk.CTkEntry(dlg, font=APP_FONT, justify="right")
        title_entry.pack(fill="x", padx=20, pady=4)

        
        ctk.CTkLabel(dlg, text="محتوا", font=APP_FONT).pack(anchor="e", padx=20,
                                                              pady=(8, 0))
        content_box = ctk.CTkTextbox(dlg, font=APP_FONT, height=120,
                                    wrap="word")
        content_box.pack(fill="both", expand=True, padx=20, pady=4)

        
        ctk.CTkLabel(dlg, text="تگ‌ها:", font=APP_FONT).pack(anchor="e",
                                                                        padx=20, pady=(8, 0))
        tags_entry = ctk.CTkEntry(dlg, font=APP_FONT, justify="right")
        tags_entry.pack(fill="x", padx=20, pady=4)

        def save():
            title = title_entry.get().strip()
            content = content_box.get("1.0", "end").strip()
            if not title or not content:
                return
            tp = type_var.get()
            
            if tp == "password":
                content = self.security.encrypt_text(content)
            idx = cat_names.index(cat_var.get()) if cat_var.get() in cat_names else 0
            cat_id = cat_ids[idx] if cat_ids else None
            tags = [t.strip() for t in tags_entry.get().split(",") if t.strip()]
            self.db.add_item(
                category_id=cat_id, title=title,
                content=content, item_type=tp, tags=tags,
            )
            dlg.destroy()
            self._on_search()

        ctk.CTkButton(dlg, text="save", font=APP_FONT, command=save
                      ).pack(pady=10)

   
    def _bind_idle_events(self) -> None:
        """reset تایمر هر activity‌ای."""
        for seq in ("<Motion>", "<Key>", "<Button>", "<ButtonRelease>"):
            self.bind_all(seq, self._touch, add="+")

    def _touch(self, _event=None) -> None:
        self._last_activity_ts = self.winfo_exists() and self._now_ms()

    @staticmethod
    def _now_ms() -> float:
        import time
        return time.time() * 1000

    def _check_idle(self) -> None:
        
        if self.security.is_unlocked():
            idle = self._now_ms() - max(self._last_activity_ts, 0)
            if idle >= IDLE_TIMEOUT_MS:
                self._do_lock()
        self.after(10_000, self._check_idle)

    def _manual_lock(self) -> None:
        self._do_lock()

    def _do_lock(self) -> None:
        self.security.lock()
        self._render_items([])   
        self._ensure_unlocked()

    def _ensure_unlocked(self) -> None:
        if self.security.is_unlocked():
            return
        LoginWindow(self, self.security, on_success=self._after_unlock)

    def _after_unlock(self) -> None:
        self._last_activity_ts = self._now_ms()
        self._select_category(None)


    def _do_backup(self) -> None:
        if not self.security.is_unlocked():
            messagebox.showwarning("قفل", "ابتدا وارد شوید.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".zip",
            initialfile=f"myvault_backup_{datetime.now():%Y%m%d_%H%M}.zip",
            filetypes=[("ZIP", "*.zip"), ("JSON", "*.json")],
        )
        if not path:
            return
        try:
            data = self.db.export_plaintext_dict()
            
            for item in data["items"]:
                if item["item_type"] == "password":
                    try:
                        item["content"] = self.security.decrypt_text(item["content"])
                    except ValueError:
                        pass

            if path.endswith(".zip"):
                with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
                    zf.writestr("vault_export.json",
                                json.dumps(data, ensure_ascii=False, indent=2))
            else:
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            messagebox.showinfo("موفق", f"پشتیبان ذخیره شد:\n{path}")
        except Exception as e:
            messagebox.showerror("خطا", str(e))

    
    def destroy(self):
        try:
            self.db.close()
        finally:
            super().destroy()
