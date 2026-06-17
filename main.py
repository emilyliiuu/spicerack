import sys
import json
import time
from PyQt6.QtWidgets import (
    QApplication, QWidget, QPushButton, QLabel,
    QGridLayout, QVBoxLayout, QHBoxLayout, QLineEdit, QDialog
)
from PyQt6.QtCore import Qt

STORAGE_FILE = "storage.json"

DEFAULT_COLOR = "#444444"


# -----------------------------
# DATA MODEL
# -----------------------------
def load_spices():
    try:
        with open(STORAGE_FILE, "r") as f:
            return json.load(f)
    except:
        return [
            {
                "name": f"Spice {i+1}",
                "rfid": None,
                "color": DEFAULT_COLOR,
                "status": "OK",
                "weight": 0
            }
            for i in range(16)
        ]


def save_spices(data):
    with open(STORAGE_FILE, "w") as f:
        json.dump(data, f, indent=2)


# -----------------------------
# ON SCREEN KEYBOARD
# -----------------------------
class OnScreenKeyboard(QDialog):
    def __init__(self, target_line_edit):
        super().__init__()
        self.setWindowTitle("Keyboard")
        self.target = target_line_edit

        layout = QVBoxLayout()

        self.display = QLineEdit()
        self.display.setText(self.target.text())
        layout.addWidget(self.display)

        keys = [
            "QWERTYUIOP",
            "ASDFGHJKL",
            "ZXCVBNM"
        ]

        for row in keys:
            row_layout = QHBoxLayout()
            for ch in row:
                btn = QPushButton(ch)
                btn.setFixedSize(50, 50)
                btn.clicked.connect(lambda _, c=ch: self.add_char(c))
                row_layout.addWidget(btn)
            layout.addLayout(row_layout)

        bottom = QHBoxLayout()

        space = QPushButton("Space")
        space.clicked.connect(lambda: self.add_char(" "))
        space.setFixedHeight(50)

        back = QPushButton("Back")
        back.clicked.connect(self.backspace)
        back.setFixedHeight(50)

        ok = QPushButton("OK")
        ok.clicked.connect(self.accept)
        ok.setFixedHeight(50)

        bottom.addWidget(space)
        bottom.addWidget(back)
        bottom.addWidget(ok)

        layout.addLayout(bottom)

        self.setLayout(layout)

    def add_char(self, c):
        self.display.setText(self.display.text() + c)

    def backspace(self):
        self.display.setText(self.display.text()[:-1])

    def accept(self):
        self.target.setText(self.display.text())
        super().accept()


# -----------------------------
# EDIT DIALOG
# -----------------------------
class EditDialog(QDialog):
    def __init__(self, spice_data):
        super().__init__()
        self.setWindowTitle("Edit Spice")
        self.data = spice_data

        layout = QVBoxLayout()

        # NAME
        layout.addWidget(QLabel("Name:"))
        self.name_edit = QLineEdit(self.data["name"])
        self.name_edit.setReadOnly(True)
        self.name_edit.mousePressEvent = self.open_keyboard
        layout.addWidget(self.name_edit)

        # COLOR
        layout.addWidget(QLabel("Color:"))

        self.selected_color = self.data.get("color", DEFAULT_COLOR)

        color_options = [
            "#444444",
            "#8B0000",
            "#228B22",
            "#1E90FF",
            "#DAA520",
            "#800080",
            "#FF8C00"
        ]

        color_layout = QHBoxLayout()

        for c in color_options:
            btn = QPushButton()
            btn.setFixedSize(30, 30)
            btn.setStyleSheet(f"background-color: {c}; border-radius: 15px;")
            btn.clicked.connect(lambda _, col=c: self.select_color(col))
            color_layout.addWidget(btn)

        layout.addLayout(color_layout)

        # BUTTONS
        save_btn = QPushButton("Save")
        delete_btn = QPushButton("Delete")

        save_btn.clicked.connect(self.save)
        delete_btn.clicked.connect(self.delete)

        layout.addWidget(save_btn)
        layout.addWidget(delete_btn)

        self.setLayout(layout)

        self.deleted = False

    def open_keyboard(self, event):
        kb = OnScreenKeyboard(self.name_edit)
        kb.exec()

    def select_color(self, color):
        self.selected_color = color

    def save(self):
        self.data["name"] = self.name_edit.text()
        self.data["color"] = self.selected_color
        self.accept()

    def delete(self):
        self.deleted = True
        self.accept()


# -----------------------------
# MAIN UI
# -----------------------------
class SpiceMachineUI(QWidget):
    def __init__(self):
        super().__init__()

        self.selected_idx = None
        self.last_tap_time = {}
        self.double_tap_window = 0.35  # seconds
        self.tap_hint_label = {}

        self.setWindowTitle("Spice Machine")
        self.showFullScreen()

        self.spices = load_spices()
        self.edit_mode = False

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        # TITLE
        self.title = QLabel("Select a Spice")
        self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(self.title)

        # GRID
        self.grid = QGridLayout()
        self.buttons = []

        for i in range(16):
            btn = QPushButton(self.spices[i]["name"])
            btn.setFixedSize(160, 160)
            btn.clicked.connect(lambda _, idx=i: self.on_spice_click(idx))
            self.buttons.append(btn)
            self.grid.addWidget(btn, i // 4, i % 4)

        self.grid.setHorizontalSpacing(15)
        self.grid.setVerticalSpacing(15)

        self.layout.addLayout(self.grid)

        # BOTTOM BAR
        bottom = QHBoxLayout()

        self.edit_btn = QPushButton("Edit Mode")
        self.edit_btn.clicked.connect(self.toggle_edit)

        self.return_btn = QPushButton("Return Bottle")
        self.return_btn.clicked.connect(self.return_bottle)

        bottom.addWidget(self.edit_btn)
        bottom.addWidget(self.return_btn)

        self.layout.addLayout(bottom)

        self.refresh()

    # -----------------------------
    # SPICE CLICK
    # -----------------------------

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.showNormal()

    def on_spice_click(self, idx):
        now = time.time()
        last_time = self.last_tap_time.get(idx, 0)

        spice = self.spices[idx]

        if self.edit_mode:
            self.open_edit(idx)
            return

        # first tap → select + hint
        if now - last_time >= self.double_tap_window:
            self.last_tap_time[idx] = now
            self.selected_idx = idx
            self.title.setText(f"Tap again to dispense {spice['name']}")
            self.refresh()
            return

        # second tap → dispense
        self.last_tap_time[idx] = 0
        self.selected_idx = None
        self.dispense(idx)
        self.refresh()
    def dispense(self, idx):
        spice = self.spices[idx]
        self.title.setText(f"Dispensing {spice['name']}...")

        # highlight button briefly
        btn = self.buttons[idx]
        btn.setStyleSheet(btn.styleSheet() + "border: 4px solid white;")

        print("DISPENSE:", spice["name"])

        # reset highlight after short delay
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(400, self.refresh)

    # -----------------------------
    # EDIT MODE
    # -----------------------------
    def toggle_edit(self):
        self.edit_mode = not self.edit_mode
        self.edit_btn.setText("Exit Edit Mode" if self.edit_mode else "Edit Mode")

    def open_edit(self, idx):
        dialog = EditDialog(self.spices[idx])

        if dialog.exec():
            if dialog.deleted:
                self.spices[idx] = {
                    "name": "EMPTY",
                    "rfid": None,
                    "color": DEFAULT_COLOR,
                    "status": "EMPTY",
                    "weight": 0
                }

            save_spices(self.spices)
            self.refresh()

    # -----------------------------
    # UI REFRESH
    # -----------------------------
    def refresh(self):
        for i, btn in enumerate(self.buttons):
            spice = self.spices[i]

            btn.setText(spice["name"])

            status = spice.get("status", "OK")

            if status == "EMPTY":
                color = "#222222"
                btn.setEnabled(False)
            elif status == "LOW":
                color = "#FF8C00"
                btn.setEnabled(True)
            else:
                color = spice.get("color", DEFAULT_COLOR)
                btn.setEnabled(True)

            # highlight selected
            if i == self.selected_idx:
                border = "4px solid white"
            else:
                border = "none"

            btn.setStyleSheet(f"""
                QPushButton {{
                    border-radius: 80px;
                    background-color: {color};
                    color: white;
                    font-size: 12px;
                    font-weight: bold;
                    border: {border};
                }}
                QPushButton:pressed {{
                    background-color: #111;
                }}
            """)

    # -----------------------------
    # RETURN (RFID HOOK)
    # -----------------------------
    def return_bottle(self):
        self.title.setText("Scanning RFID...")

        fake_rfid = "ABC123"
        print("RFID:", fake_rfid)

        for i, spice in enumerate(self.spices):
            if spice["rfid"] == fake_rfid:
                self.title.setText(f"Return: {spice['name']}")
                return

        self.title.setText("Unknown Bottle")


# -----------------------------
# RUN
# -----------------------------
app = QApplication(sys.argv)
window = SpiceMachineUI()
window.show()
sys.exit(app.exec())