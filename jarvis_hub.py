# jarvis_hub.py
"""
Retail Management System - Main Entry Point.
Modular application for automating retail operations and report processing.
"""

import customtkinter as ctk
from modules.frames import (ClearanceFrame, MissedItemsFrame, MovementFrame, 
                            PriceUpdateFrame, ShippingFrame)
from modules.constants import THEME_CONFIG

class JarvisHub(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Window Setup
        self.title("Retail Management System v2.10 (Jarvis Edition)")
        self.geometry("1150x850")
        
        # Application Theme
        ctk.set_appearance_mode(THEME_CONFIG["appearance"])
        ctk.set_default_color_theme(THEME_CONFIG["color_theme"])

        # Grid Layout
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # UI Initialization
        self.active_module_frame = None
        self._init_sidebar()
        self._init_content_area()
        self.show_home()

    def _init_sidebar(self):
        """Initializes the navigation sidebar."""
        self.nav_frame = ctk.CTkFrame(self, width=280, corner_radius=0)
        self.nav_frame.grid(row=0, column=0, sticky="nsew")
        self.nav_frame.grid_rowconfigure(8, weight=1)

        self.logo_label = ctk.CTkLabel(self.nav_frame, text="🦾 Retail HUB", 
                                        font=ctk.CTkFont(size=26, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(40, 40))

        self.buttons = []
        nav_items = [
            ("⚡ Кліренс", self.show_clearance),
            ("🔍 Пропущені", self.show_missed),
            ("📦 Переведення", self.show_movement),
            ("🏷️ Переоцінка", self.show_price_update),
            ("🚚 Відправка", self.show_shipping)
        ]

        for i, (text, cmd) in enumerate(nav_items, start=1):
            btn = ctk.CTkButton(self.nav_frame, text=text, 
                                font=ctk.CTkFont(size=15, weight="bold"),
                                height=45, corner_radius=10, fg_color="transparent",
                                anchor="w", command=cmd)
            btn.grid(row=i, column=0, padx=20, pady=5, sticky="ew")
            self.buttons.append(btn)

        # Settings
        self.mode_menu = ctk.CTkOptionMenu(self.nav_frame, values=["Dark", "Light", "System"],
                                           command=ctk.set_appearance_mode)
        self.mode_menu.grid(row=10, column=0, padx=20, pady=20)

    def _init_content_area(self):
        """Initializes the main content container."""
        self.content_container = ctk.CTkFrame(self, corner_radius=15)
        self.content_container.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")
        self.content_container.grid_columnconfigure(0, weight=1)
        self.content_container.grid_rowconfigure(0, weight=1)

    def _switch_frame(self, frame_class, btn_index):
        """Helper to switch between module frames."""
        # Update sidebar buttons
        for i, btn in enumerate(self.buttons):
            btn.configure(fg_color="#1F6AA5" if i == btn_index else "transparent")
        
        # Destroy old frame and load new one
        if self.active_module_frame:
            self.active_module_frame.destroy()
        
        self.active_module_frame = frame_class(self.content_container, fg_color="transparent")
        self.active_module_frame.pack(fill="both", expand=True)

    def show_home(self):
        if self.active_module_frame: self.active_module_frame.destroy()
        
        home = ctk.CTkFrame(self.content_container, fg_color="transparent")
        home.pack(expand=True)
        ctk.CTkLabel(home, text="🦾", font=ctk.CTkFont(size=120)).pack()
        ctk.CTkLabel(home, text="Retail Management System", font=ctk.CTkFont(size=32, weight="bold")).pack(pady=10)
        ctk.CTkLabel(home, text="Оберіть інструмент для початку роботи", font=ctk.CTkFont(size=18), text_color="gray").pack()
        self.active_module_frame = home

    def show_clearance(self): self._switch_frame(ClearanceFrame, 0)
    def show_missed(self): self._switch_frame(MissedItemsFrame, 1)
    def show_movement(self): self._switch_frame(MovementFrame, 2)
    def show_price_update(self): self._switch_frame(PriceUpdateFrame, 3)
    def show_shipping(self): self._switch_frame(ShippingFrame, 4)

if __name__ == "__main__":
    app = JarvisHub()
    app.mainloop()
