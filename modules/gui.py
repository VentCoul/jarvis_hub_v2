"""
PySide6 GUI — Apple-inspired Retail Hub.
Home screen → Wizard flow → Results screen.
"""

import os
import sys
import threading
from functools import partial

from PySide6.QtCore import Qt, Signal, QObject, QMimeData, QSize
from PySide6.QtGui import QFont, QDragEnterEvent, QDropEvent, QIcon, QFontDatabase
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QLabel, QPushButton, QStackedWidget, QComboBox,
    QLineEdit, QFileDialog, QMessageBox, QSizePolicy, QFrame,
    QScrollArea, QSpacerItem,
)

from .theme import LIGHT, DARK, build_stylesheet
from .logic import (
    process_clearance_add, process_missed_items,
    process_movement, process_price_update, process_shipping,
)

import pandas as pd


# ─── Signals bridge (thread → main) ────────────────────────────────────

class WorkerSignals(QObject):
    finished = Signal(object)
    error = Signal(str)


def run_in_thread(work_fn, on_success, on_error):
    """Run work_fn() in a background thread, deliver result via Qt signals."""
    sig = WorkerSignals()
    sig.finished.connect(on_success)
    sig.error.connect(on_error)

    def _worker():
        try:
            result = work_fn()
            sig.finished.emit(result)
        except Exception as e:
            sig.error.emit(str(e))

    t = threading.Thread(target=_worker, daemon=True)
    t.start()
    return sig  # prevent GC


# ─── Reusable widgets ──────────────────────────────────────────────────

class DropZone(QFrame):
    """Drag-and-drop file zone with click-to-browse fallback."""
    file_dropped = Signal(str)

    def __init__(self, label="Перетягніть файл сюди", hint="або натисніть щоб обрати .xlsx / .xls",
                 file_filter="Excel files (*.xlsx *.xls);;All files (*)", parent=None):
        super().__init__(parent)
        self.file_filter = file_filter
        self._path = None
        self.setAcceptDrops(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(110)
        self.setProperty("class", "dropzone")

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(4)

        self.icon_label = QLabel("☁")
        self.icon_label.setAlignment(Qt.AlignCenter)
        self.icon_label.setFont(QFont("", 32))
        self.icon_label.setProperty("class", "tertiary")
        layout.addWidget(self.icon_label)

        self.text_label = QLabel(label)
        self.text_label.setAlignment(Qt.AlignCenter)
        self.text_label.setFont(QFont("", 14, QFont.Medium))
        layout.addWidget(self.text_label)

        self.hint_label = QLabel(hint)
        self.hint_label.setAlignment(Qt.AlignCenter)
        self.hint_label.setProperty("class", "tertiary")
        self.hint_label.setFont(QFont("", 12))
        layout.addWidget(self.hint_label)

        self._update_style(False)

    def path(self):
        return self._path

    def set_file(self, path):
        if not path:
            return
        self._path = path
        name = os.path.basename(path)
        size_kb = os.path.getsize(path) / 1024
        size_str = f"{size_kb / 1024:.1f} MB" if size_kb > 1024 else f"{size_kb:.0f} KB"
        self.icon_label.setText("📄")
        self.text_label.setText(name)
        self.hint_label.setText(f"{size_str} — завантажено")
        self._update_style(True)
        self.file_dropped.emit(path)

    def _update_style(self, filled):
        t = QApplication.instance()._current_theme
        if filled:
            self.setStyleSheet(f"""
                DropZone {{
                    border: 2px solid {t['drop_filled_border']};
                    border-radius: 14px;
                    background: {t['drop_filled_bg']};
                }}
            """)
        else:
            self.setStyleSheet(f"""
                DropZone {{
                    border: 2px dashed {t['drop_border']};
                    border-radius: 14px;
                    background: {t['drop_bg']};
                }}
                DropZone:hover {{
                    border-color: {t['accent']};
                }}
            """)

    def mousePressEvent(self, event):
        path, _ = QFileDialog.getOpenFileName(self, "Оберіть файл", "", self.file_filter)
        if path:
            self.set_file(path)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if path:
                self.set_file(path)
                break

    def reset(self):
        self._path = None
        self.icon_label.setText("☁")
        self.text_label.setText("Перетягніть файл сюди")
        self.hint_label.setText("або натисніть щоб обрати")
        self._update_style(False)


class ModuleCard(QFrame):
    """Clickable card for the home screen."""
    clicked = Signal()

    def __init__(self, icon, name, desc, color, parent=None):
        super().__init__(parent)
        self.color = color
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(120)
        self.setProperty("class", "module-card")

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(8)

        icon_lbl = QLabel(icon)
        icon_lbl.setAlignment(Qt.AlignCenter)
        icon_lbl.setFont(QFont("", 28))
        icon_lbl.setStyleSheet(f"color: {color};")
        layout.addWidget(icon_lbl)

        name_lbl = QLabel(name)
        name_lbl.setAlignment(Qt.AlignCenter)
        name_lbl.setFont(QFont("", 14, QFont.Medium))
        layout.addWidget(name_lbl)

    def mousePressEvent(self, event):
        self.clicked.emit()

    def apply_theme(self, t):
        self.setStyleSheet(f"""
            ModuleCard {{
                background: {t['card_bg']};
                border: 0.5px solid {t['card_border']};
                border-radius: 14px;
            }}
            ModuleCard:hover {{
                background: {t['card_hover']};
            }}
        """)


class StepIndicator(QWidget):
    """Horizontal step dots: done / active / pending."""

    def __init__(self, steps, parent=None):
        super().__init__(parent)
        self.step_labels = steps
        self.current = 0
        self._build()

    def _build(self):
        self.layout_h = QHBoxLayout(self)
        self.layout_h.setAlignment(Qt.AlignLeft)
        self.layout_h.setSpacing(0)
        self.dots = []
        self.labels = []
        self.lines = []

        for i, name in enumerate(self.step_labels):
            dot = QLabel()
            dot.setFixedSize(24, 24)
            dot.setAlignment(Qt.AlignCenter)
            dot.setFont(QFont("", 11, QFont.Medium))
            self.dots.append(dot)
            self.layout_h.addWidget(dot)

            lbl = QLabel(name)
            lbl.setFont(QFont("", 13, QFont.Medium))
            self.labels.append(lbl)
            self.layout_h.addWidget(lbl)

            if i < len(self.step_labels) - 1:
                line = QFrame()
                line.setFixedSize(32, 1)
                self.lines.append(line)
                self.layout_h.addSpacing(6)
                self.layout_h.addWidget(line)
                self.layout_h.addSpacing(6)

    def set_step(self, idx):
        self.current = idx
        t = QApplication.instance()._current_theme
        for i, (dot, lbl) in enumerate(zip(self.dots, self.labels)):
            if i < idx:  # done
                dot.setText("✓")
                dot.setStyleSheet(f"background: {t['success']}; color: white; border-radius: 12px; font-size: 13px;")
                lbl.setStyleSheet(f"color: {t['success']};")
            elif i == idx:  # active
                dot.setText(str(i + 1))
                dot.setStyleSheet(f"background: {t['accent']}; color: white; border-radius: 12px;")
                lbl.setStyleSheet(f"color: {t['text_primary']};")
            else:  # pending
                dot.setText(str(i + 1))
                dot.setStyleSheet(f"background: {t['bg_tertiary']}; color: {t['text_tertiary']}; border-radius: 12px;")
                lbl.setStyleSheet(f"color: {t['text_tertiary']};")
        for line in self.lines:
            line.setStyleSheet(f"background: {t['border']};")


class MetricCard(QFrame):
    """Big number + label card for results."""

    def __init__(self, value, label, color, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setContentsMargins(16, 16, 16, 16)

        val_lbl = QLabel(str(value))
        val_lbl.setAlignment(Qt.AlignCenter)
        val_lbl.setFont(QFont("", 28, QFont.Medium))
        val_lbl.setStyleSheet(f"color: {color};")
        layout.addWidget(val_lbl)

        txt_lbl = QLabel(label)
        txt_lbl.setAlignment(Qt.AlignCenter)
        txt_lbl.setProperty("class", "tertiary")
        txt_lbl.setFont(QFont("", 12))
        layout.addWidget(txt_lbl)

        self.val_lbl = val_lbl

    def apply_theme(self, t):
        self.setStyleSheet(f"""
            MetricCard {{
                background: {t['bg_secondary']};
                border-radius: 12px;
            }}
        """)


# ─── Pages ──────────────────────────────────────────────────────────────

class HomePage(QWidget):
    module_selected = Signal(str)

    MODULES = [
        ("⚡", "Кліренс", "", "mod_clearance", "clearance"),
        ("🔍", "Пропущені", "", "mod_missed", "missed"),
        ("📦", "Переведення", "", "mod_movement", "movement"),
        ("🏷", "Переоцінка", "", "mod_price", "price"),
        ("🚚", "Відправка", "", "mod_shipping", "shipping"),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(8)
        layout.setContentsMargins(40, 40, 40, 40)

        # Hero
        icon_lbl = QLabel("🦾")
        icon_lbl.setAlignment(Qt.AlignCenter)
        icon_lbl.setFont(QFont("", 48))
        layout.addWidget(icon_lbl)

        title = QLabel("Retail Hub")
        title.setAlignment(Qt.AlignCenter)
        title.setProperty("class", "title")
        layout.addWidget(title)

        sub = QLabel("Оберіть інструмент для роботи")
        sub.setAlignment(Qt.AlignCenter)
        sub.setProperty("class", "subtitle")
        layout.addWidget(sub)

        layout.addSpacing(24)

        # Cards grid
        grid = QGridLayout()
        grid.setSpacing(12)
        self.cards = []

        for i, (icon, name, desc, color_key, module_id) in enumerate(self.MODULES):
            card = ModuleCard(icon, name, desc, "")  # color applied in apply_theme
            card._color_key = color_key
            card._module_id = module_id
            card.clicked.connect(partial(self.module_selected.emit, module_id))
            row, col = divmod(i, 3)
            grid.addWidget(card, row, col)
            self.cards.append(card)

        layout.addLayout(grid)
        layout.addStretch()

        # Theme toggle at bottom
        self.theme_btn = QPushButton("☀  Light")
        self.theme_btn.setFixedWidth(120)
        bottom = QHBoxLayout()
        bottom.addStretch()
        bottom.addWidget(self.theme_btn)
        bottom.addStretch()
        layout.addLayout(bottom)

    def apply_theme(self, t):
        for card in self.cards:
            card.color = t[card._color_key]
            card.findChild(QLabel).setStyleSheet(f"color: {t[card._color_key]};")
            card.apply_theme(t)
        icon = "☀  Light" if t['name'] == 'dark' else "🌙  Dark"
        self.theme_btn.setText(icon)


class WizardPage(QWidget):
    """Generic wizard page — each module subclasses or configures this."""
    go_home = Signal()
    show_results = Signal(str, object)  # module_id, result_data

    def __init__(self, module_id, title, icon, color_key, steps_def, parent=None):
        super().__init__(parent)
        self.module_id = module_id
        self.color_key = color_key
        self._worker_sig = None

        outer = QVBoxLayout(self)
        outer.setContentsMargins(40, 28, 40, 28)
        outer.setSpacing(0)

        # Back
        back_btn = QPushButton("← Головна")
        back_btn.setFlat(True)
        back_btn.setCursor(Qt.PointingHandCursor)
        back_btn.setStyleSheet("font-size: 13px; padding: 0; text-align: left;")
        back_btn.clicked.connect(self.go_home.emit)
        outer.addWidget(back_btn, alignment=Qt.AlignLeft)
        outer.addSpacing(16)

        # Header
        hdr = QHBoxLayout()
        icon_lbl = QLabel(icon)
        icon_lbl.setFont(QFont("", 28))
        self._icon_lbl = icon_lbl
        hdr.addWidget(icon_lbl)
        title_lbl = QLabel(title)
        title_lbl.setProperty("class", "title")
        hdr.addWidget(title_lbl)
        hdr.addStretch()
        outer.addLayout(hdr)
        outer.addSpacing(4)

        self.subtitle = QLabel("")
        self.subtitle.setProperty("class", "subtitle")
        outer.addWidget(self.subtitle)
        outer.addSpacing(20)

        # Stepper
        self.stepper = StepIndicator(steps_def)
        outer.addWidget(self.stepper)
        outer.addSpacing(20)

        # Content area (stacked for steps)
        self.step_stack = QStackedWidget()
        outer.addWidget(self.step_stack, stretch=1)

        # Action button
        outer.addSpacing(16)
        self.action_btn = QPushButton("Далі →")
        self.action_btn.setProperty("class", "accent")
        self.action_btn.setMinimumHeight(48)
        self.action_btn.setFont(QFont("", 15, QFont.Medium))
        outer.addWidget(self.action_btn)

    def apply_theme(self, t):
        self._icon_lbl.setStyleSheet(f"color: {t[self.color_key]};")
        self.stepper.set_step(self.stepper.current)
        back = self.findChild(QPushButton)
        if back and back.isFlat():
            back.setStyleSheet(f"color: {t['accent']}; font-size: 13px; padding: 0;")

    def set_step(self, idx, subtitle=""):
        self.stepper.set_step(idx)
        self.step_stack.setCurrentIndex(idx)
        self.subtitle.setText(subtitle)

    def _run_processing(self, work_fn):
        self.action_btn.setEnabled(False)
        self.action_btn.setText("⏳ Обробка...")
        self._worker_sig = run_in_thread(
            work_fn,
            on_success=self._on_success,
            on_error=self._on_error,
        )

    def _on_success(self, result):
        self.action_btn.setEnabled(True)
        self.action_btn.setText("Далі →")
        self.show_results.emit(self.module_id, result)

    def _on_error(self, msg):
        self.action_btn.setEnabled(True)
        self.action_btn.setText("Далі →")
        QMessageBox.critical(self, "Помилка", msg)


class ResultsPage(QWidget):
    go_home = Signal()
    go_back_to_wizard = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(40, 28, 40, 28)
        outer.setSpacing(0)

        top_row = QHBoxLayout()
        back_btn = QPushButton("← Головна")
        back_btn.setFlat(True)
        back_btn.setCursor(Qt.PointingHandCursor)
        back_btn.clicked.connect(self.go_home.emit)
        top_row.addWidget(back_btn)
        top_row.addStretch()
        self.retry_btn = QPushButton("↻  Повторити")
        self.retry_btn.setCursor(Qt.PointingHandCursor)
        self.retry_btn.clicked.connect(self.go_back_to_wizard.emit)
        top_row.addWidget(self.retry_btn)
        outer.addLayout(top_row)
        outer.addSpacing(16)

        self.title_lbl = QLabel("Результати")
        self.title_lbl.setProperty("class", "title")
        outer.addWidget(self.title_lbl)

        self.sub_lbl = QLabel("")
        self.sub_lbl.setProperty("class", "subtitle")
        outer.addWidget(self.sub_lbl)
        outer.addSpacing(24)

        self.metrics_layout = QHBoxLayout()
        self.metrics_layout.setSpacing(12)
        outer.addLayout(self.metrics_layout)
        outer.addSpacing(24)

        self.buttons_layout = QHBoxLayout()
        self.buttons_layout.setSpacing(8)
        outer.addLayout(self.buttons_layout)
        outer.addStretch()

        self._metric_cards = []
        self._buttons = []
        self._back_btn = back_btn
        self._last_module_id = None

    def apply_theme(self, t):
        self._back_btn.setStyleSheet(f"color: {t['accent']}; font-size: 13px; padding: 0;")
        for mc in self._metric_cards:
            mc.apply_theme(t)

    def show_results(self, title, subtitle, metrics, save_actions, theme, module_id=None):
        """
        metrics: [(value, label, color_key), ...]
        save_actions: [(label, tint_key, text_color_key, callback), ...]
        """
        self._last_module_id = module_id
        self.title_lbl.setText(title)
        self.sub_lbl.setText(subtitle)

        # Clear old
        for mc in self._metric_cards:
            mc.setParent(None)
        self._metric_cards.clear()
        for b in self._buttons:
            b.setParent(None)
        self._buttons.clear()

        t = theme

        for val, label, color_key in metrics:
            mc = MetricCard(val, label, t[color_key])
            mc.apply_theme(t)
            self.metrics_layout.addWidget(mc)
            self._metric_cards.append(mc)

        for i, (label, tint_key, text_key, callback) in enumerate(save_actions):
            btn = QPushButton(f"↓  {label}")
            btn.setMinimumHeight(48)
            btn.setFont(QFont("", 14, QFont.Medium))
            btn.setCursor(Qt.PointingHandCursor)
            is_primary = (i == len(save_actions) - 1) and len(save_actions) > 1
            if is_primary:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: {t['accent']};
                        color: white;
                        border: none;
                        border-radius: 12px;
                    }}
                    QPushButton:hover {{ background: {t['accent_hover']}; }}
                """)
            else:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: {t[tint_key]};
                        color: {t[text_key]};
                        border: none;
                        border-radius: 12px;
                    }}
                    QPushButton:hover {{ background: {t[tint_key]}; }}
                """)
            btn.clicked.connect(callback)
            self.buttons_layout.addWidget(btn)
            self._buttons.append(btn)


# ─── Module wizard builders ─────────────────────────────────────────────

def _save_lines(parent, data, filename):
    path, _ = QFileDialog.getSaveFileName(parent, "Зберегти", filename, "Text files (*.txt)")
    if path:
        with open(path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(data))
        QMessageBox.information(parent, "Готово", f"Збережено {len(data)} рядків у {os.path.basename(path)}")


def _save_excel(parent, df, filename):
    path, _ = QFileDialog.getSaveFileName(parent, "Зберегти", filename, "Excel files (*.xlsx)")
    if path:
        df.to_excel(path, index=False)
        QMessageBox.information(parent, "Готово", f"Збережено {len(df)} рядків у {os.path.basename(path)}")
        try:
            if sys.platform == 'darwin':
                os.system(f'open "{path}"')
            elif sys.platform == 'win32':
                os.startfile(path)
        except Exception:
            pass


def _save_workbook(parent, wb, filename):
    path, _ = QFileDialog.getSaveFileName(parent, "Зберегти", filename, "Excel files (*.xlsx)")
    if path:
        wb.save(path)
        QMessageBox.information(parent, "Готово", f"Збережено: {os.path.basename(path)}")


def _populate_stores(combo, path):
    try:
        df = pd.read_excel(path)
        s_col = '# Mall' if '# Mall' in df.columns else ('Store' if 'Store' in df.columns else df.columns[1])
        stores = [str(s) for s in sorted(df[s_col].unique().tolist())]
        combo.clear()
        for s in stores:
            combo.addItem(s)
    except Exception:
        pass


def _make_loc_buttons(app):
    loc_group = []
    for loc_name in ["Загальна", "Склад", "Торговий зал"]:
        b = QPushButton(loc_name)
        b.setCheckable(True)
        b.setCursor(Qt.PointingHandCursor)
        loc_group.append(b)

    def style():
        t = app._current_theme
        for b in loc_group:
            if b.isChecked():
                b.setStyleSheet(f"""
                    QPushButton {{
                        background: {t['accent']};
                        color: white;
                        border: none;
                        border-radius: 10px;
                    }}
                """)
            else:
                b.setStyleSheet("")

    def on_click(clicked):
        if clicked.text() == "Загальна":
            for b in loc_group:
                b.setChecked(b == clicked)
        else:
            loc_group[0].setChecked(False)
            if not any(b.isChecked() for b in loc_group[1:]):
                loc_group[0].setChecked(True)
        style()

    for b in loc_group:
        b.clicked.connect(partial(on_click, b))

    loc_group[0].setChecked(True)
    style()
    return loc_group, style


def _selected_locs(loc_group):
    if loc_group[0].isChecked():
        return ["Загальна"]
    return [b.text() for b in loc_group[1:] if b.isChecked()]


def build_clearance_wizard(parent_stack, results_page, app):
    wiz = WizardPage("clearance", "Кліренс додавання", "⚡", "mod_clearance",
                      ["Файли", "Запуск"])

    # Step 0: Files
    s0 = QWidget()
    s0l = QVBoxLayout(s0)
    s0l.setContentsMargins(0, 0, 0, 0)
    for lbl_t in ["ФАЙЛ CLEARANCE ДОДАВАННЯ"]:
        lbl = QLabel(lbl_t); lbl.setProperty("class", "section"); s0l.addWidget(lbl)
    s0l.addSpacing(6)
    drop_clr = DropZone("Перетягніть Total Clearance", "або натисніть — .xlsx / .xls")
    s0l.addWidget(drop_clr)
    s0l.addSpacing(16)
    lbl2 = QLabel("ЗВІТ ЗАПАСІВ"); lbl2.setProperty("class", "section"); s0l.addWidget(lbl2)
    s0l.addSpacing(6)
    drop_inv = DropZone("Перетягніть звіт запасів", "або натисніть — .xlsx / .xls")
    s0l.addWidget(drop_inv)
    s0l.addStretch()
    wiz.step_stack.addWidget(s0)

    # Step 1: Settings + Run
    s1 = QWidget()
    s1l = QVBoxLayout(s1)
    s1l.setContentsMargins(0, 0, 0, 0)
    lbl3 = QLabel("МАГАЗИН"); lbl3.setProperty("class", "section"); s1l.addWidget(lbl3)
    s1l.addSpacing(6)
    combo_store = QComboBox()
    combo_store.addItem("Завантажте файл кліренсу...")
    s1l.addWidget(combo_store)
    s1l.addSpacing(16)
    lbl4 = QLabel("ЛОКАЦІЇ (можна кілька)"); lbl4.setProperty("class", "section"); s1l.addWidget(lbl4)
    s1l.addSpacing(6)
    loc_row = QHBoxLayout()
    loc_group, style_locs = _make_loc_buttons(app)
    for b in loc_group:
        loc_row.addWidget(b)
    s1l.addLayout(loc_row)
    s1l.addStretch()
    wiz.step_stack.addWidget(s1)

    drop_clr.file_dropped.connect(lambda path: _populate_stores(combo_store, path))
    wiz._current_step = [0]

    def next_step():
        step = wiz._current_step[0]
        if step == 0:
            if not drop_clr.path() or not drop_inv.path():
                QMessageBox.warning(wiz, "Увага", "Завантажте обидва файли!")
                return
            wiz._current_step[0] = 1
            wiz.set_step(1, "Оберіть магазин та локації")
            wiz.action_btn.setText("Запустити →")
            style_locs()
        elif step == 1:
            st = combo_store.currentText()
            if not st or "Завантажте" in st:
                QMessageBox.warning(wiz, "Увага", "Оберіть магазин!")
                return
            locs = _selected_locs(loc_group)
            wiz._run_processing(
                lambda: {loc: process_clearance_add(drop_clr.path(), drop_inv.path(), st, loc) for loc in locs}
            )

    wiz.action_btn.clicked.connect(next_step)

    def on_result(module_id, results_dict):
        t = app._current_theme
        st = combo_store.currentText()
        all_empty = all(not v for v in results_dict.values())
        if all_empty:
            QMessageBox.information(wiz, "Інфо", "Нічого не знайдено.")
            return
        total = sum(len(v) for v in results_dict.values())
        metrics = []
        actions = []
        for loc, data in results_dict.items():
            if not data:
                continue
            metrics.append((len(data), loc, "mod_clearance"))
            loc_data = data
            loc_name = loc
            actions.append((f"{loc} ({len(data)})", "tint_clearance", "mod_clearance",
                            lambda _checked=False, d=loc_data, l=loc_name: _save_lines(results_page, d, f"Кліренс_{st}_{l}.txt")))
        results_page.show_results(
            f"⚡ Кліренс — {st}",
            f"Оброблено {total} позицій",
            metrics, actions, t, module_id="clearance",
        )
        parent_stack.setCurrentWidget(results_page)

    wiz.show_results.connect(on_result)

    def reset():
        wiz._current_step[0] = 0
        wiz.set_step(0, "Завантажте файли")
        wiz.action_btn.setText("Далі →")
        drop_clr.reset()
        drop_inv.reset()

    wiz._reset = reset
    return wiz


def build_missed_wizard(parent_stack, results_page, app):
    wiz = WizardPage("missed", "Пропущені товари", "🔍", "mod_missed",
                      ["Файл", "Запуск"])

    s0 = QWidget()
    s0l = QVBoxLayout(s0)
    s0l.setContentsMargins(0, 0, 0, 0)
    lbl = QLabel("ЗВІТ ЗАПАСІВ"); lbl.setProperty("class", "section"); s0l.addWidget(lbl)
    s0l.addSpacing(6)
    drop_inv = DropZone("Перетягніть звіт запасів", "або натисніть — .xlsx / .xls")
    s0l.addWidget(drop_inv)
    s0l.addStretch()
    wiz.step_stack.addWidget(s0)

    s1 = QWidget()
    s1l = QVBoxLayout(s1)
    s1l.setContentsMargins(0, 0, 0, 0)
    lbl_div = QLabel("ДИВІЗІОН"); lbl_div.setProperty("class", "section"); s1l.addWidget(lbl_div)
    s1l.addSpacing(6)
    combo_div = QComboBox()
    for v in ["Усі", "Одяг", "Взуття", "Аксесуари"]:
        combo_div.addItem(v)
    s1l.addWidget(combo_div)
    s1l.addSpacing(16)
    lbl_g = QLabel("СТАТЬ"); lbl_g.setProperty("class", "section"); s1l.addWidget(lbl_g)
    s1l.addSpacing(6)
    combo_gen = QComboBox()
    for v in ["Усі", "Men", "Women", "Unisex", "Junior", "Kids"]:
        combo_gen.addItem(v)
    s1l.addWidget(combo_gen)
    s1l.addStretch()
    wiz.step_stack.addWidget(s1)

    wiz._current_step = [0]

    def next_step():
        step = wiz._current_step[0]
        if step == 0:
            if not drop_inv.path():
                QMessageBox.warning(wiz, "Увага", "Завантажте файл!")
                return
            wiz._current_step[0] = 1
            wiz.set_step(1, "Оберіть фільтри")
            wiz.action_btn.setText("Запустити →")
        elif step == 1:
            div = combo_div.currentText()
            gen = combo_gen.currentText()
            wiz._run_processing(
                lambda: process_missed_items(drop_inv.path(), div, gen)
            )

    wiz.action_btn.clicked.connect(next_step)

    def on_result(module_id, data):
        if data.empty:
            QMessageBox.information(wiz, "Інфо", "Пропущених не знайдено.")
            return
        t = app._current_theme
        div = combo_div.currentText()
        gen = combo_gen.currentText()
        results_page.show_results(
            "🔍 Пропущені товари",
            f"Знайдено {len(data)} позицій",
            [(len(data), "Пропущено", "mod_missed")],
            [("Зберегти .xlsx", "tint_missed", "mod_missed",
              lambda: _save_excel(results_page, data, f"Пропущені_{div}_{gen}.xlsx"))],
            t, module_id="missed",
        )
        parent_stack.setCurrentWidget(results_page)

    wiz.show_results.connect(on_result)

    def reset():
        wiz._current_step[0] = 0
        wiz.set_step(0, "Завантажте звіт")
        wiz.action_btn.setText("Далі →")
        drop_inv.reset()

    wiz._reset = reset
    return wiz


def build_movement_wizard(parent_stack, results_page, app):
    wiz = WizardPage("movement", "Переведення в ТЗ", "📦", "mod_movement",
                      ["Файли", "Запуск"])

    s0 = QWidget()
    s0l = QVBoxLayout(s0)
    s0l.setContentsMargins(0, 0, 0, 0)
    drop_clr = DropZone("Перетягніть Total Clearance", "або натисніть — .xlsx / .xls")
    drop_inv = DropZone("Перетягніть звіт запасів", "або натисніть — .xlsx / .xls")
    drop_scan = DropZone("Перетягніть файл сканування", "або натисніть — .txt",
                          file_filter="Text files (*.txt);;All files (*)")
    for lbl_t, dz in [("TOTAL CLEARANCE", drop_clr), ("ЗВІТ ЗАПАСІВ", drop_inv), ("ФАЙЛ СКАНУВАННЯ", drop_scan)]:
        lbl = QLabel(lbl_t); lbl.setProperty("class", "section"); s0l.addWidget(lbl)
        s0l.addSpacing(4); s0l.addWidget(dz); s0l.addSpacing(10)
    s0l.addStretch()
    wiz.step_stack.addWidget(s0)

    s1 = QWidget()
    s1l = QVBoxLayout(s1)
    s1l.setContentsMargins(0, 0, 0, 0)
    lbl_s = QLabel("МАГАЗИН"); lbl_s.setProperty("class", "section"); s1l.addWidget(lbl_s)
    s1l.addSpacing(6)
    combo_store = QComboBox()
    combo_store.addItem("Завантажте файл кліренсу...")
    s1l.addWidget(combo_store)
    s1l.addStretch()
    wiz.step_stack.addWidget(s1)

    drop_clr.file_dropped.connect(lambda path: _populate_stores(combo_store, path))
    wiz._current_step = [0]

    def next_step():
        step = wiz._current_step[0]
        if step == 0:
            if not all([drop_clr.path(), drop_inv.path(), drop_scan.path()]):
                QMessageBox.warning(wiz, "Увага", "Завантажте всі три файли!")
                return
            wiz._current_step[0] = 1
            wiz.set_step(1, "Оберіть магазин")
            wiz.action_btn.setText("Запустити →")
        elif step == 1:
            st = combo_store.currentText()
            if "Завантажте" in st:
                QMessageBox.warning(wiz, "Увага", "Оберіть магазин!")
                return
            wiz._run_processing(
                lambda: process_movement(drop_clr.path(), drop_inv.path(), drop_scan.path(), st)
            )

    wiz.action_btn.clicked.connect(next_step)

    def on_result(module_id, data):
        promo, regular, all_combined = data
        t = app._current_theme
        st = combo_store.currentText()
        promo_qty = sum(int(x.split(';')[1]) for x in promo) if promo else 0
        reg_qty = sum(int(x.split(';')[1]) for x in regular) if regular else 0
        results_page.show_results(
            f"📦 Переведення — {st}",
            f"Оброблено {len(all_combined)} штрихкодів",
            [
                (promo_qty, "Кліренс", "mod_clearance"),
                (reg_qty, "Звичайні", "mod_missed"),
                (promo_qty + reg_qty, "Всього", "mod_shipping"),
            ],
            [
                (f"Кліренс ({promo_qty})", "tint_clearance", "mod_clearance",
                 lambda: _save_lines(results_page, promo, f"КЛІРЕНС_{st}.txt")),
                (f"Звичайні ({reg_qty})", "tint_missed", "mod_missed",
                 lambda: _save_lines(results_page, regular, f"НЕ_КЛІРЕНС_{st}.txt")),
                (f"Все ({len(all_combined)})", "tint_shipping", "mod_shipping",
                 lambda: _save_lines(results_page, all_combined, f"УСІ_ШК_{st}.txt")),
            ],
            t, module_id="movement",
        )
        parent_stack.setCurrentWidget(results_page)

    wiz.show_results.connect(on_result)

    def reset():
        wiz._current_step[0] = 0
        wiz.set_step(0, "Завантажте файли")
        wiz.action_btn.setText("Далі →")
        drop_clr.reset(); drop_inv.reset(); drop_scan.reset()

    wiz._reset = reset
    return wiz


def build_price_wizard(parent_stack, results_page, app):
    wiz = WizardPage("price", "Переоцінка", "🏷", "mod_price",
                      ["Файли", "Запуск"])

    s0 = QWidget()
    s0l = QVBoxLayout(s0)
    s0l.setContentsMargins(0, 0, 0, 0)
    drop_price = DropZone("Перетягніть файл переоцінки", "або натисніть — .xlsx / .xls")
    drop_clr = DropZone("Перетягніть Total Clearance", "або натисніть — .xlsx / .xls")
    drop_inv = DropZone("Перетягніть звіт запасів", "або натисніть — .xlsx / .xls")
    for lbl_t, dz in [("ФАЙЛ ПЕРЕОЦІНКИ", drop_price), ("TOTAL CLEARANCE", drop_clr), ("ЗВІТ ЗАПАСІВ", drop_inv)]:
        lbl = QLabel(lbl_t); lbl.setProperty("class", "section"); s0l.addWidget(lbl)
        s0l.addSpacing(4); s0l.addWidget(dz); s0l.addSpacing(10)
    s0l.addStretch()
    wiz.step_stack.addWidget(s0)

    s1 = QWidget()
    s1l = QVBoxLayout(s1)
    s1l.setContentsMargins(0, 0, 0, 0)
    lbl_s = QLabel("МАГАЗИН"); lbl_s.setProperty("class", "section"); s1l.addWidget(lbl_s)
    s1l.addSpacing(6)
    combo_store = QComboBox()
    combo_store.addItem("Завантажте файл кліренсу...")
    s1l.addWidget(combo_store)
    s1l.addStretch()
    wiz.step_stack.addWidget(s1)

    drop_clr.file_dropped.connect(lambda path: _populate_stores(combo_store, path))
    wiz._current_step = [0]

    def next_step():
        step = wiz._current_step[0]
        if step == 0:
            if not all([drop_price.path(), drop_clr.path(), drop_inv.path()]):
                QMessageBox.warning(wiz, "Увага", "Завантажте всі три файли!")
                return
            wiz._current_step[0] = 1
            wiz.set_step(1, "Оберіть магазин")
            wiz.action_btn.setText("Запустити →")
        elif step == 1:
            st = combo_store.currentText()
            if "Завантажте" in st:
                QMessageBox.warning(wiz, "Увага", "Оберіть магазин!")
                return
            wiz._run_processing(
                lambda: process_price_update(drop_price.path(), drop_clr.path(), drop_inv.path(), st)
            )

    wiz.action_btn.clicked.connect(next_step)

    def on_result(module_id, data):
        promo, reg, total_in_price, found_arts = data
        t = app._current_theme
        st = combo_store.currentText()
        not_found = total_in_price - found_arts
        metrics = [
            (len(promo), "Акційних", "mod_price"),
            (len(reg), "Звичайних", "mod_missed"),
            (not_found, "Немає в магазині", "text_tertiary"),
        ]
        actions = []
        if promo:
            actions.append((f"Акційні ({len(promo)})", "tint_price", "mod_price",
                            lambda: _save_lines(results_page, promo, f"Акційні_{st}.txt")))
        if reg:
            actions.append((f"Звичайні ({len(reg)})", "tint_missed", "mod_missed",
                            lambda: _save_lines(results_page, reg, f"Звичайні_{st}.txt")))
        if not promo and not reg:
            QMessageBox.information(wiz, "Інфо",
                                   f"Жодного артикулу з прайсу не знайдено в запасах.\n"
                                   f"Всього в прайсі: {total_in_price}")
            return
        results_page.show_results(
            f"🏷 Переоцінка — {st}",
            f"Знайдено {found_arts} з {total_in_price} артикулів",
            metrics, actions, t, module_id="price",
        )
        parent_stack.setCurrentWidget(results_page)

    wiz.show_results.connect(on_result)

    def reset():
        wiz._current_step[0] = 0
        wiz.set_step(0, "Завантажте файли")
        wiz.action_btn.setText("Далі →")
        drop_price.reset(); drop_clr.reset(); drop_inv.reset()

    wiz._reset = reset
    return wiz


def build_shipping_wizard(parent_stack, results_page, app):
    wiz = WizardPage("shipping", "Відправка товару", "🚚", "mod_shipping",
                      ["Файли", "Запуск"])

    s0 = QWidget()
    s0l = QVBoxLayout(s0)
    s0l.setContentsMargins(0, 0, 0, 0)
    drop_scan = DropZone("Перетягніть файл сканування", "або натисніть — .txt",
                          file_filter="Text files (*.txt);;All files (*)")
    drop_inv = DropZone("Перетягніть звіт запасів", "або натисніть — .xlsx / .xls")
    drop_tmpl = DropZone("Перетягніть шаблон Excel", "або натисніть — .xlsx")
    for lbl_t, dz in [("ФАЙЛ СКАНУВАННЯ", drop_scan), ("ЗВІТ ЗАПАСІВ", drop_inv), ("ШАБЛОН EXCEL", drop_tmpl)]:
        lbl = QLabel(lbl_t); lbl.setProperty("class", "section"); s0l.addWidget(lbl)
        s0l.addSpacing(4); s0l.addWidget(dz); s0l.addSpacing(10)
    s0l.addStretch()
    wiz.step_stack.addWidget(s0)

    s1 = QWidget()
    s1l = QVBoxLayout(s1)
    s1l.setContentsMargins(0, 0, 0, 0)
    lbl_d = QLabel("НОМЕР ДОКУМЕНТУ"); lbl_d.setProperty("class", "section"); s1l.addWidget(lbl_d)
    s1l.addSpacing(6)
    doc_input = QLineEdit()
    doc_input.setPlaceholderText("Наприклад: ПЕР005697")
    s1l.addWidget(doc_input)
    s1l.addStretch()
    wiz.step_stack.addWidget(s1)

    wiz._current_step = [0]
    result_wb = [None]

    def next_step():
        step = wiz._current_step[0]
        if step == 0:
            if not all([drop_scan.path(), drop_inv.path(), drop_tmpl.path()]):
                QMessageBox.warning(wiz, "Увага", "Завантажте всі три файли!")
                return
            wiz._current_step[0] = 1
            wiz.set_step(1, "Введіть номер документу")
            wiz.action_btn.setText("Запустити →")
        elif step == 1:
            doc = doc_input.text().strip()
            if not doc:
                QMessageBox.warning(wiz, "Увага", "Введіть номер документу!")
                return
            wiz._run_processing(
                lambda: process_shipping(drop_scan.path(), drop_inv.path(), drop_tmpl.path(), doc)
            )

    wiz.action_btn.clicked.connect(next_step)

    def on_result(module_id, wb):
        result_wb[0] = wb
        if wb is None:
            QMessageBox.information(wiz, "Інфо", "Файл сканування порожній.")
            return
        t = app._current_theme
        doc = doc_input.text().strip()
        results_page.show_results(
            f"🚚 Відправка — {doc}",
            "Шаблон наповнено даними",
            [(1, "Документ готовий", "mod_shipping")],
            [("Зберегти .xlsx", "tint_shipping", "mod_shipping",
              lambda: _save_workbook(results_page, result_wb[0], f"Відправка_{doc}.xlsx"))],
            t, module_id="shipping",
        )
        parent_stack.setCurrentWidget(results_page)

    wiz.show_results.connect(on_result)

    def reset():
        wiz._current_step[0] = 0
        wiz.set_step(0, "Завантажте файли")
        wiz.action_btn.setText("Далі →")
        drop_scan.reset(); drop_inv.reset(); drop_tmpl.reset()
        doc_input.clear(); result_wb[0] = None

    wiz._reset = reset
    return wiz


# ─── Main Window ────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Retail Hub")
        self.resize(1000, 720)
        self.setMinimumSize(800, 600)

        app = QApplication.instance()
        app._current_theme = DARK

        central = QWidget()
        central.setObjectName("central")
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)

        self.stack = QStackedWidget()
        layout.addWidget(self.stack)

        # Pages
        self.home = HomePage()
        self.results = ResultsPage()
        self.stack.addWidget(self.home)
        self.stack.addWidget(self.results)

        # Build wizards
        self.wizards = {}
        builders = {
            "clearance": build_clearance_wizard,
            "missed": build_missed_wizard,
            "movement": build_movement_wizard,
            "price": build_price_wizard,
            "shipping": build_shipping_wizard,
        }
        for mod_id, builder in builders.items():
            wiz = builder(self.stack, self.results, app)
            wiz.go_home.connect(self._go_home)
            self.stack.addWidget(wiz)
            self.wizards[mod_id] = wiz

        self.home.module_selected.connect(self._open_module)
        self.home.theme_btn.clicked.connect(self._toggle_theme)
        self.results.go_home.connect(self._go_home)
        self.results.go_back_to_wizard.connect(self._retry_wizard)

        self._apply_theme()

    def _go_home(self):
        self.stack.setCurrentWidget(self.home)

    def _open_module(self, module_id):
        wiz = self.wizards[module_id]
        wiz._reset()
        wiz.set_step(0, "Крок 1 — завантажте файли")
        self.stack.setCurrentWidget(wiz)
        wiz.apply_theme(QApplication.instance()._current_theme)

    def _retry_wizard(self):
        mod_id = self.results._last_module_id
        if mod_id and mod_id in self.wizards:
            wiz = self.wizards[mod_id]
            wiz._current_step[0] = 1
            wiz.set_step(1, "Змініть налаштування і запустіть знову")
            wiz.action_btn.setText("Запустити →")
            self.stack.setCurrentWidget(wiz)
            wiz.apply_theme(QApplication.instance()._current_theme)

    def _toggle_theme(self):
        app = QApplication.instance()
        app._current_theme = LIGHT if app._current_theme['name'] == 'dark' else DARK
        self._apply_theme()

    def _apply_theme(self):
        app = QApplication.instance()
        t = app._current_theme
        app.setStyleSheet(build_stylesheet(t))
        self.home.apply_theme(t)
        self.results.apply_theme(t)
        for wiz in self.wizards.values():
            wiz.apply_theme(t)


def run():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    font = QFont(".AppleSystemUIFont", 13)
    font.setStyleStrategy(QFont.PreferAntialias)
    app.setFont(font)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())
