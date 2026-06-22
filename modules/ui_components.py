import os
import threading
import customtkinter as ctk
import pandas as pd
from tkinter import filedialog, messagebox

PLACEHOLDER = "Оберіть файл..."


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

    # ---- Shared helpers (used by multiple module frames) ----

    def populate_stores(self, path):
        """Reads a Total Clearance file and fills self.combo_store with store IDs."""
        try:
            df = pd.read_excel(path)
            s_col = '# Mall' if '# Mall' in df.columns else ('Store' if 'Store' in df.columns else df.columns[1])
            stores = [str(s) for s in sorted(df[s_col].unique().tolist())]
            self.combo_store.configure(values=stores)
            self.combo_store.set(stores[0])
        except Exception as e:
            messagebox.showerror("Помилка", f"Не вдалося прочитати як Total Clearance: {e}")

    def valid_store(self):
        """Returns the selected store id, or None (with a warning) if not chosen."""
        st = self.combo_store.get()
        if not st or st == PLACEHOLDER:
            messagebox.showwarning("Увага", "Спочатку оберіть файл кліренсу та номер магазину!")
            return None
        return st

    def save_lines(self, data, filename):
        """Saves a list of 'barcode;qty' lines to a user-chosen .txt file (UTF-8)."""
        path = filedialog.asksaveasfilename(defaultextension=".txt", initialfile=filename)
        if path:
            with open(path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(data))
            messagebox.showinfo("Готово", f"Дані збережено у {os.path.basename(path)}")

    def run_in_thread(self, button, work, on_success):
        """
        Runs `work()` (heavy, no UI access) in a background thread so the window
        does not freeze. `on_success(result)` runs back on the main thread; any
        exception is shown via messagebox on the main thread.
        Tkinter is not thread-safe — only the main-thread callbacks touch widgets.
        """
        original_text = button.cget("text")
        button.configure(state="disabled", text="⏳ Обробка...")

        def finish(callback):
            button.configure(state="normal", text=original_text)
            callback()

        def worker():
            try:
                result = work()
            except Exception as e:
                self.after(0, lambda: finish(lambda: messagebox.showerror("Помилка", str(e))))
                return
            self.after(0, lambda: finish(lambda: on_success(result)))

        threading.Thread(target=worker, daemon=True).start()
