import customtkinter as ctk
import os
import sys
from tkinter import filedialog, messagebox
from .ui_components import BaseModuleFrame
from .logic import (process_clearance_add, process_missed_items,
                    process_movement, process_price_update, process_shipping)


class ClearanceFrame(BaseModuleFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, title="⚡ Кліренс додавання", **kwargs)
        self.entry_clr = self.create_file_selector("1. Файл Clearence Додавання:", 1, command=self.populate_stores)
        ctk.CTkLabel(self, text="2. Номер магазину:", anchor="w", font=ctk.CTkFont(weight="bold")).grid(row=3, column=0, padx=30, pady=(15,0), sticky="w")
        self.combo_store = ctk.CTkComboBox(self, values=["Оберіть файл..."], width=350, height=35)
        self.combo_store.grid(row=4, column=0, padx=30, pady=5, sticky="w")
        self.entry_inv = self.create_file_selector("3. Файл Звіт запасів:", 5)
        ctk.CTkLabel(self, text="4. Фільтр по локації:", anchor="w", font=ctk.CTkFont(weight="bold")).grid(row=7, column=0, padx=30, pady=(15,0), sticky="w")
        self.seg_loc = ctk.CTkSegmentedButton(self, values=["Загальна", "Склад", "Торговий зал"], height=40)
        self.seg_loc.set("Загальна")
        self.seg_loc.grid(row=8, column=0, padx=30, pady=10, sticky="ew")
        self.btn_run = ctk.CTkButton(self, text="ЗАПУСТИТИ ОБРОБКУ", height=60, font=ctk.CTkFont(size=18, weight="bold"), command=self.run)
        self.btn_run.grid(row=9, column=0, padx=30, pady=(30, 20), sticky="ew")

    def run(self):
        c_p, i_p = self.entry_clr.get(), self.entry_inv.get()
        lc = self.seg_loc.get()
        if not c_p or not i_p:
            messagebox.showwarning("Увага", "Оберіть обидва файли!")
            return
        st = self.valid_store()
        if st is None:
            return

        def work():
            return process_clearance_add(c_p, i_p, st, lc)

        def on_success(output):
            if not output:
                messagebox.showinfo("Інфо", "Нічого не знайдено.")
                return
            save_p = filedialog.asksaveasfilename(defaultextension=".txt", initialfile=f"Кліренс_{st}_{lc}.txt")
            if save_p:
                with open(save_p, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(output))
                messagebox.showinfo("Готово", f"Оброблено {len(output)} позицій.")

        self.run_in_thread(self.btn_run, work, on_success)


class MissedItemsFrame(BaseModuleFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, title="🔍 Пропущені товари", **kwargs)
        self.missed_data = None

        self.entry_inv = self.create_file_selector("1. Файл Звіт запасів:", 1)

        filter_frm = ctk.CTkFrame(self, fg_color="transparent")
        filter_frm.grid(row=3, column=0, padx=30, pady=10, sticky="ew")
        filter_frm.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkLabel(filter_frm, text="2. Дивізіон:", anchor="w", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, padx=5, sticky="w")
        self.combo_div = ctk.CTkComboBox(filter_frm, values=["Усі", "Одяг", "Взуття", "Аксесуари"], height=35)
        self.combo_div.grid(row=1, column=0, padx=5, pady=5, sticky="ew")

        ctk.CTkLabel(filter_frm, text="3. Стать:", anchor="w", font=ctk.CTkFont(weight="bold")).grid(row=0, column=1, padx=5, sticky="w")
        self.combo_gender = ctk.CTkComboBox(filter_frm, values=["Усі", "Men", "Women", "Unisex", "Junior", "Kids"], height=35)
        self.combo_gender.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        # Кнопка тепер виконує все одразу
        self.btn_run = ctk.CTkButton(self, text="🚀 СФОРМУВАТИ ТА ВІДКРИТИ EXCEL", height=80,
                                     fg_color="#27ae60", hover_color="#219150",
                                     font=ctk.CTkFont(size=20, weight="bold"), command=self.run)
        self.btn_run.grid(row=5, column=0, padx=30, pady=40, sticky="ew")

        ctk.CTkLabel(self, text="Програма автоматично знайде товари, які є на складі,\nале відсутні в залі, та відкриє їх у новому файлі.",
                     text_color="gray").grid(row=6, column=0, padx=30, pady=10)

    def run(self):
        inv_path = self.entry_inv.get()
        div = self.combo_div.get()
        gen = self.combo_gender.get()

        if not inv_path:
            messagebox.showwarning("Увага", "Оберіть файл звіту запасів!")
            return

        def work():
            return process_missed_items(inv_path, div, gen)

        def on_success(missed_data):
            self.missed_data = missed_data
            if missed_data.empty:
                messagebox.showinfo("Інфо", "Пропущених товарів не знайдено.")
                return

            save_p = filedialog.asksaveasfilename(
                defaultextension=".xlsx",
                initialfile=f"Пропущені_{div}_{gen}.xlsx",
                title="Зберегти звіт пропущені"
            )

            if save_p:
                missed_data.to_excel(save_p, index=False)
                messagebox.showinfo("Успіх", f"Знайдено {len(missed_data)} пропущених позицій.\nФайл збережено та буде відкрито.")
                self._open_file(save_p)

        self.run_in_thread(self.btn_run, work, on_success)

    def _open_file(self, save_p):
        try:
            if os.name == 'nt':  # Windows
                os.startfile(save_p)
            else:  # Linux / Mac
                import subprocess
                opener = 'open' if sys.platform == 'darwin' else 'xdg-open'
                subprocess.call([opener, save_p])
        except Exception:
            messagebox.showinfo("Готово", f"Файл збережено: {os.path.basename(save_p)}\n(Не вдалося відкрити автоматично)")


class MovementFrame(BaseModuleFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, title="📦 Переведення в ТЗ", **kwargs)
        self.promo_out, self.reg_out, self.all_out = [], [], []
        self.entry_clr = self.create_file_selector("1. Файл Total Clearence:", 1, command=self.populate_stores)
        ctk.CTkLabel(self, text="2. Номер магазину:", anchor="w", font=ctk.CTkFont(weight="bold")).grid(row=3, column=0, padx=30, pady=(15,0), sticky="w")
        self.combo_store = ctk.CTkComboBox(self, values=["Оберіть файл..."], width=350, height=35)
        self.combo_store.grid(row=4, column=0, padx=30, pady=5, sticky="w")
        self.entry_inv = self.create_file_selector("3. Файл Звіт запасів:", 5)
        self.entry_scan = self.create_file_selector("4. Файл сканування (txt):", 7)
        self.btn_run = ctk.CTkButton(self, text="🔥 ОБРОБИТИ ДАНІ", height=60, font=ctk.CTkFont(size=18, weight="bold"), command=self.run)
        self.btn_run.grid(row=9, column=0, padx=30, pady=(25, 10), sticky="ew")
        save_frm = ctk.CTkFrame(self, fg_color="transparent")
        save_frm.grid(row=10, column=0, padx=30, pady=5, sticky="ew")
        save_frm.grid_columnconfigure((0,1), weight=1)
        self.btn_sp = ctk.CTkButton(save_frm, text="💾 КЛІРЕНС", state="disabled", height=45, fg_color="#d35400", command=self.save_promo)
        self.btn_sp.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        self.btn_sr = ctk.CTkButton(save_frm, text="💾 НЕ КЛІРЕНС", state="disabled", height=45, command=self.save_regular)
        self.btn_sr.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.btn_sa = ctk.CTkButton(self, text="💾 ЗБЕРЕГТИ УСІ ШК", state="disabled", height=45, fg_color="#27ae60", command=self.save_all)
        self.btn_sa.grid(row=11, column=0, padx=30, pady=5, sticky="ew")

    def run(self):
        c_p, i_p, s_p = self.entry_clr.get(), self.entry_inv.get(), self.entry_scan.get()
        if not all([c_p, i_p, s_p]):
            messagebox.showwarning("Увага", "Оберіть усі вхідні файли!")
            return
        st = self.valid_store()
        if st is None:
            return

        def work():
            return process_movement(c_p, i_p, s_p, st)

        def on_success(result):
            self.promo_out, self.reg_out, self.all_out = result
            promo_qty = sum(int(item.split(';')[1]) for item in self.promo_out)
            reg_qty = sum(int(item.split(';')[1]) for item in self.reg_out)
            self.btn_sp.configure(state="normal", text=f"💾 КЛІРЕНС ({promo_qty})")
            self.btn_sr.configure(state="normal", text=f"💾 НЕ КЛІРЕНС ({reg_qty})")
            self.btn_sa.configure(state="normal", text=f"💾 УСІ ШК ({len(self.all_out)})")
            messagebox.showinfo("Готово", "Дані оброблено!")

        self.run_in_thread(self.btn_run, work, on_success)

    def save_promo(self): self.save_lines(self.promo_out, f"КЛІРЕНС_{self.combo_store.get()}.txt")
    def save_regular(self): self.save_lines(self.reg_out, f"НЕ_КЛІРЕНС_{self.combo_store.get()}.txt")
    def save_all(self): self.save_lines(self.all_out, f"УСІ_ШК_{self.combo_store.get()}.txt")


class PriceUpdateFrame(BaseModuleFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, title="🏷️ Переоцінка", **kwargs)
        self.promo_out, self.reg_out = [], []
        self.entry_price = self.create_file_selector("1. Файл Переоцінки (XLS):", 1)
        self.entry_clr = self.create_file_selector("2. Файл Total Clearence:", 3, command=self.populate_stores)
        ctk.CTkLabel(self, text="3. Номер магазину:", anchor="w", font=ctk.CTkFont(weight="bold")).grid(row=5, column=0, padx=30, pady=(15,0), sticky="w")
        self.combo_store = ctk.CTkComboBox(self, values=["Оберіть файл..."], width=350, height=35)
        self.combo_store.grid(row=6, column=0, padx=30, pady=5, sticky="w")
        self.entry_inv = self.create_file_selector("4. Файл Звіт запасів:", 7)
        self.btn_run = ctk.CTkButton(self, text="🚀 ОБРОБИТИ ПЕРЕОЦІНКУ", height=60, font=ctk.CTkFont(size=18, weight="bold"), command=self.run)
        self.btn_run.grid(row=9, column=0, padx=30, pady=(30, 10), sticky="ew")
        save_frm = ctk.CTkFrame(self, fg_color="transparent")
        save_frm.grid(row=10, column=0, padx=30, pady=5, sticky="ew")
        save_frm.grid_columnconfigure((0,1), weight=1)
        self.btn_sp = ctk.CTkButton(save_frm, text="💾 АКЦІЙНІ", state="disabled", height=45, fg_color="#d35400", command=self.save_promo)
        self.btn_sp.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        self.btn_sr = ctk.CTkButton(save_frm, text="💾 ЗВИЧАЙНІ", state="disabled", height=45, command=self.save_regular)
        self.btn_sr.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

    def run(self):
        p_p, c_p, i_p = self.entry_price.get(), self.entry_clr.get(), self.entry_inv.get()
        if not all([p_p, c_p, i_p]):
            messagebox.showwarning("Увага", "Оберіть усі три файли!")
            return
        st = self.valid_store()
        if st is None:
            return

        def work():
            return process_price_update(p_p, c_p, i_p, st)

        def on_success(result):
            self.promo_out, self.reg_out = result
            self.btn_sp.configure(state="normal", text=f"💾 АКЦІЙНІ ({len(self.promo_out)})")
            self.btn_sr.configure(state="normal", text=f"💾 ЗВИЧАЙНІ ({len(self.reg_out)})")
            messagebox.showinfo("Готово", f"Оброблено!\nАкційних: {len(self.promo_out)}\nЗвичайних: {len(self.reg_out)}")

        self.run_in_thread(self.btn_run, work, on_success)

    def save_promo(self): self.save_lines(self.promo_out, f"Акційні_{self.combo_store.get()}.txt")
    def save_regular(self): self.save_lines(self.reg_out, f"Звичайні_{self.combo_store.get()}.txt")


class ShippingFrame(BaseModuleFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, title="🚚 Відправка товару", **kwargs)
        self.result_wb = None
        self.entry_scan = self.create_file_selector("1. Файл сканування (ТЗД .txt):", 1)
        self.entry_inv = self.create_file_selector("2. Файл Звіт запасів:", 3)
        self.entry_temp = self.create_file_selector("3. Шаблон (Excel):", 5)
        ctk.CTkLabel(self, text="4. Номер документу:", anchor="w", font=ctk.CTkFont(weight="bold")).grid(row=7, column=0, padx=30, pady=(15,0), sticky="w")
        self.entry_doc = ctk.CTkEntry(self, width=350, height=35, placeholder_text="Наприклад: ПЕР005697")
        self.entry_doc.grid(row=8, column=0, padx=30, pady=5, sticky="w")
        self.btn_run = ctk.CTkButton(self, text="⚙️ НАПОВНИТИ ШАБЛОН", height=60, font=ctk.CTkFont(size=18, weight="bold"), command=self.run)
        self.btn_run.grid(row=9, column=0, padx=30, pady=30, sticky="ew")
        self.btn_save = ctk.CTkButton(self, text="💾 ЗБЕРЕГТИ РЕЗУЛЬТАТ", state="disabled", height=50, fg_color="#27ae60", command=self.save)
        self.btn_save.grid(row=10, column=0, padx=30, pady=5, sticky="ew")

    def run(self):
        s_p, i_p, t_p, doc = self.entry_scan.get(), self.entry_inv.get(), self.entry_temp.get(), self.entry_doc.get().strip()
        if not all([s_p, i_p, t_p, doc]):
            messagebox.showwarning("Увага", "Оберіть усі файли та введіть номер документу!")
            return

        def work():
            return process_shipping(s_p, i_p, t_p, doc)

        def on_success(wb):
            self.result_wb = wb
            if wb is None:
                messagebox.showinfo("Інфо", "Файл сканування порожній.")
                return
            self.btn_save.configure(state="normal")
            messagebox.showinfo("Готово", "Шаблон наповнено даними!")

        self.run_in_thread(self.btn_run, work, on_success)

    def save(self):
        if self.result_wb is None: return
        path = filedialog.asksaveasfilename(defaultextension=".xlsx", initialfile=f"Відправка_{self.entry_doc.get()}.xlsx")
        if path:
            try:
                self.result_wb.save(path)
                messagebox.showinfo("Готово", f"Файл збережено: {os.path.basename(path)}")
            except Exception as e: messagebox.showerror("Помилка збереження", str(e))
