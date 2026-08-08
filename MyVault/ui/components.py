

from __future__ import annotations
import customtkinter as ctk
import pyperclip
import webbrowser


class ItemCard(ctk.CTkFrame):
    """کارت نمایش آیتم — note / link / password."""

    def __init__(
        self,
        master,
        item_id: int,
        title: str,
        content: str,          
        item_type: str,
        tags: str = "",
        on_delete: callable = None,
        **kwargs,
    ):
        super().__init__(master, **kwargs)
        self.item_id = item_id
        self.title_text = title
        self.content_text = content
        self.item_type = item_type
        self.on_delete = on_delete

        self.configure(
            corner_radius=14,
            border_width=1,
            border_color=("#d0d0d0", "#2a2a2a"),
            fg_color=("#f7f7f7", "#1e1e1e"),
        )

        self.grid_columnconfigure(0, weight=1)

        
        self.title_lbl = ctk.CTkLabel(
            self, text=title,
            font=ctk.CTkFont(family="B Nazanin", size=16, weight="bold"),
            anchor="e", justify="right",
        )
        self.title_lbl.grid(row=0, column=0, columnspan=3,
                            padx=12, pady=(10, 4), sticky="ew")

        if tags:
            self.tags_lbl = ctk.CTkLabel(
                self, text=f"🏷 {tags}",
                font=ctk.CTkFont(family="B Nazanin", size=11),
                text_color=("#666666", "#9aa0a6"),
                anchor="e", justify="right",
            )
            self.tags_lbl.grid(row=1, column=0, columnspan=3,
                               padx=12, pady=(0, 4), sticky="ew")

        
        row = 2
        if item_type == "password":
            self.pwd_lbl = ctk.CTkLabel(
                self, text="•" * 12,
                font=ctk.CTkFont(family="Consolas", size=14),
                anchor="e",
            )
            self.pwd_lbl.grid(row=row, column=0, padx=12, pady=6, sticky="ew")

            self.copy_btn = ctk.CTkButton(
                self, text=" copy", width=70,
                font=ctk.CTkFont(family="B Nazanin", size=12),
                command=self._copy_password,
            )
            self.copy_btn.grid(row=row, column=1, padx=6, pady=6)

        elif item_type == "link":
            self.link_lbl = ctk.CTkLabel(
                self, text=content,
                font=ctk.CTkFont(family="B Nazanin", size=13),
                text_color=("#0066cc", "#66b3ff"),
                anchor="e", wraplength=300,
            )
            self.link_lbl.grid(row=row, column=0, padx=12, pady=6, sticky="ew")

            self.open_btn = ctk.CTkButton(
                self, text=" باز کردن", width=90,
                font=ctk.CTkFont(family="B Nazanin", size=12),
                command=self._open_link,
            )
            self.open_btn.grid(row=row, column=1, padx=6, pady=6)

        else:  
            self.note_lbl = ctk.CTkLabel(
                self, text=content,
                font=ctk.CTkFont(family="B Nazanin", size=13),
                anchor="e", justify="right", wraplength=380,
            )
            self.note_lbl.grid(row=row, column=0, columnspan=2,
                               padx=12, pady=6, sticky="ew")

        
        self.del_btn = ctk.CTkButton(
            self, text="delet", width=40,
            font=ctk.CTkFont(size=13),
            fg_color=("#cc3333", "#8b0000"),
            hover_color=("#a32424", "#600000"),
            command=self._do_delete,
        )
        self.del_btn.grid(row=row, column=2, padx=6, pady=6)

   
    def _copy_password(self) -> None:
        pyperclip.copy(self.content_text)
        self.copy_btn.configure(text="کپی شد")
        self.after(2000, lambda: self.copy_btn.configure(text=" copy"))

    def _open_link(self) -> None:
        url = self.content_text
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        webbrowser.open_new_tab(url)

    def _do_delete(self) -> None:
        if self.on_delete:
            self.on_delete(self.item_id)
        self.destroy()
