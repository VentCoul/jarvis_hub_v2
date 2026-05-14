import customtkinter as ctk
from tkinter import filedialog

class BaseModuleFrame(ctk.CTkFrame):
    def __init__(self, master, title, **kwargs):
        super().__init__(master, **kwargs)
        self.grid_columnconfigure(0, weight=1)
        
        self.header = ctk.CTkLabel(self, text=title, font=ctk.CTkFont(size=26, weight="bold"))
        self.header.grid(row=0, column=0, padx=20, pady=(30, 20))

    def create_file_selector(self, label_text, row, placeholder="Оберіть файл...", command=None):
        ctk.CTkLabel(self, text=label_text, anchor="w", font=ctk.CTkFont(weight="bold")).grid(row=row, column=0, padx=30, pady=(15,0), sticky="w")
        
        frm = ctk.CTkFrame(self, fg_color="transparent")
        frm.grid(row=row+1, column=0, padx=30, pady=5, sticky="ew")
        frm.grid_columnconfigure(0, weight=1)
        
        entry = ctk.CTkEntry(frm, placeholder_text=placeholder, height=35)
        entry.grid(row=0, column=0, sticky="ew", padx=(0,10))
        
        btn = ctk.CTkButton(frm, text="Огляд", width=100, height=35, 
                            command=lambda: self._browse_file(entry, command))
        btn.grid(row=0, column=1)
        return entry

    def _browse_file(self, entry_widget, callback):
        path = filedialog.askopenfilename()
        if path:
            entry_widget.delete(0, "end")
            entry_widget.insert(0, path)
            if callback:
                callback(path)
