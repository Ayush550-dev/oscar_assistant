"""
gui_app.py - O.S.C.A.R.'s desktop window (replaces running things in the console)

Run this instead of main.py once you're ready to use the real interface:
    python gui_app.py

Key design choices for keeping CPU usage low (unlike the old version):
- The holographic ring only animates quickly while actively listening/speaking.
  While idle, it barely redraws at all (1 frame per second).
- System telemetry (CPU/RAM) is polled once every 2 seconds, not continuously.
- The mic/voice pipeline runs on a separate background thread (voice_worker.py)
  so it never blocks or slows down the window itself.
"""

import os
import sys
import threading
import psutil

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QVBoxLayout, QHBoxLayout,
    QGroupBox, QProgressBar, QTextEdit, QLineEdit, QPushButton
)
from PyQt6.QtCore import Qt, QTimer, QPointF, QRectF, QThread, pyqtSignal
from PyQt6.QtGui import QPainter, QPen, QColor, QPixmap, QIcon

from commands import handle_command
from brain import ask_brain, speak
from voice_worker import VoiceWorker

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")
LOGO_PATH = os.path.join(ASSETS_DIR, "spider_logo.png")
ICON_PATH = os.path.join(ASSETS_DIR, "spider_logo.ico")

STYLESHEET = """
QMainWindow, QWidget {
    background-color: #04060d;
    color: #d7f3ff;
    font-family: Consolas, 'Courier New', monospace;
}
QGroupBox {
    border: 1px solid rgba(0, 200, 255, 120);
    border-radius: 6px;
    margin-top: 14px;
    padding: 10px;
    font-weight: bold;
    color: #7fdfff;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
}
QProgressBar {
    border: 1px solid rgba(0, 200, 255, 100);
    border-radius: 4px;
    text-align: center;
    background-color: #050a14;
    color: #d7f3ff;
    height: 18px;
}
QProgressBar::chunk {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #0a5c7a, stop:1 #00d9ff);
    border-radius: 4px;
}
QTextEdit {
    background-color: #050a14;
    border: 1px solid rgba(0, 200, 255, 90);
    border-radius: 4px;
}
QLineEdit {
    background-color: #050a14;
    border: 1px solid rgba(0, 200, 255, 90);
    border-radius: 4px;
    padding: 6px;
}
QPushButton {
    background-color: rgba(0, 200, 255, 40);
    border: 1px solid #00d9ff;
    border-radius: 4px;
    padding: 6px 14px;
    color: #d7f3ff;
}
QPushButton:hover {
    background-color: rgba(0, 200, 255, 90);
}
#statusBadge {
    font-size: 15px;
    font-weight: bold;
    color: #00d9ff;
    padding: 8px;
    border: 1px solid #00d9ff;
    border-radius: 4px;
    qproperty-alignment: AlignCenter;
}
"""


class HoloRing(QWidget):
    """The circular holographic display in the center of the window."""

    STATE_COLORS = {
        "loading":  QColor(150, 150, 150, 160),
        "idle":     QColor(40, 140, 200, 150),
        "listening": QColor(0, 200, 255, 230),
        "thinking": QColor(140, 100, 255, 230),
        "speaking": QColor(0, 255, 210, 230),
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.angle = 0
        self.state = "loading"
        self.logo_pixmap = QPixmap(LOGO_PATH) if os.path.exists(LOGO_PATH) else None

        # Idle = redraw once a second only (near-zero CPU).
        # Active states speed this up for a smooth animation.
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(1000)

    def set_state(self, state):
        self.state = state
        self.timer.setInterval(40 if state in ("listening", "speaking") else 1000)
        self.update()

    def _tick(self):
        if self.state in ("listening", "speaking"):
            self.angle = (self.angle + 6) % 360
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        cx, cy = w / 2, h / 2
        radius = min(w, h) / 2 - 24
        glow = self.STATE_COLORS.get(self.state, self.STATE_COLORS["idle"])

        # Concentric rings
        for r in (radius, radius * 0.82, radius * 0.64):
            painter.setPen(QPen(glow, 1.5))
            painter.drawEllipse(QPointF(cx, cy), r, r)

        # Rotating tick marks around the outer ring
        painter.save()
        painter.translate(cx, cy)
        painter.rotate(self.angle)
        painter.setPen(QPen(glow, 2))
        for i in range(24):
            painter.save()
            painter.rotate(i * 15)
            painter.drawLine(QPointF(0, -radius - 6), QPointF(0, -radius + 6))
            painter.restore()
        painter.restore()

        # Center: your logo file, or a placeholder reminder if not found yet
        if self.logo_pixmap and not self.logo_pixmap.isNull():
            size = int(radius * 0.85)
            target = QRectF(cx - size / 2, cy - size / 2, size, size)
            painter.drawPixmap(target.toRect(), self.logo_pixmap)
        else:
            painter.setPen(QColor(255, 255, 255, 130))
            painter.drawText(
                QRectF(cx - 110, cy - 20, 220, 40),
                Qt.AlignmentFlag.AlignCenter,
                "Place spider_logo.png\nin the assets folder"
            )


class TypedCommandWorker(QThread):
    """Handles commands typed into the console box without freezing the GUI."""
    result_ready = pyqtSignal(str)

    def __init__(self, text):
        super().__init__()
        self.text = text

    def run(self):
        response = handle_command(self.text)
        if response is None:
            response = ask_brain(self.text)
        self.result_ready.emit(response)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("O.S.C.A.R.")
        self.resize(1000, 640)
        self.setStyleSheet(STYLESHEET)

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        # ---- Left side: the holographic ring ----
        left_layout = QVBoxLayout()
        title = QLabel("O.S.C.A.R.")
        title.setStyleSheet("font-size: 26px; font-weight: bold; color: #00d9ff;")
        subtitle = QLabel("Operational System // Cognitive Assistance Runtime")
        subtitle.setStyleSheet("color: #5fa8c9;")
        left_layout.addWidget(title)
        left_layout.addWidget(subtitle)

        self.holo = HoloRing()
        left_layout.addWidget(self.holo, stretch=1)
        main_layout.addLayout(left_layout, stretch=2)

        # ---- Right side: status, telemetry, console ----
        right_layout = QVBoxLayout()
        main_layout.addLayout(right_layout, stretch=1)

        self.status_label = QLabel("LOADING")
        self.status_label.setObjectName("statusBadge")
        right_layout.addWidget(self.status_label)

        telemetry_box = QGroupBox("System Telemetry")
        t_layout = QVBoxLayout()
        self.cpu_bar = QProgressBar()
        self.cpu_bar.setFormat("CPU: %p%")
        self.ram_bar = QProgressBar()
        self.ram_bar.setFormat("RAM: %p%")
        t_layout.addWidget(self.cpu_bar)
        t_layout.addWidget(self.ram_bar)
        telemetry_box.setLayout(t_layout)
        right_layout.addWidget(telemetry_box)

        console_box = QGroupBox("Command Console")
        c_layout = QVBoxLayout()
        self.console = QTextEdit()
        self.console.setReadOnly(True)
        c_layout.addWidget(self.console)

        input_row = QHBoxLayout()
        self.input_line = QLineEdit()
        self.input_line.setPlaceholderText("Command O.S.C.A.R.")
        self.run_btn = QPushButton("Run")
        input_row.addWidget(self.input_line)
        input_row.addWidget(self.run_btn)
        c_layout.addLayout(input_row)
        console_box.setLayout(c_layout)
        right_layout.addWidget(console_box, stretch=1)

        self.run_btn.clicked.connect(self.on_run_clicked)
        self.input_line.returnPressed.connect(self.on_run_clicked)

        # ---- Telemetry polling: every 2 seconds, NOT continuously ----
        self.telemetry_timer = QTimer(self)
        self.telemetry_timer.timeout.connect(self.update_telemetry)
        self.telemetry_timer.start(2000)
        self.update_telemetry()

        # ---- Background voice loop ----
        self.worker = VoiceWorker()
        self.worker.state_changed.connect(self.on_state_changed)
        self.worker.heard_text.connect(self.on_heard_text)
        self.worker.oscar_reply.connect(self.on_oscar_reply)
        self.worker.start()

    def update_telemetry(self):
        self.cpu_bar.setValue(int(psutil.cpu_percent(interval=None)))
        self.ram_bar.setValue(int(psutil.virtual_memory().percent))

    def on_state_changed(self, state):
        self.holo.set_state(state)
        self.status_label.setText(state.upper())

    def on_heard_text(self, text):
        self.console.append(f"You: {text}")

    def on_oscar_reply(self, text):
        self.console.append(f"OSCAR: {text}")

    def on_run_clicked(self):
        text = self.input_line.text().strip()
        if not text:
            return
        self.input_line.clear()
        self.console.append(f"You: {text}")

        self.typed_worker = TypedCommandWorker(text)
        self.typed_worker.result_ready.connect(self.on_typed_result)
        self.typed_worker.start()

    def on_typed_result(self, response):
        self.console.append(f"OSCAR: {response}")
        threading.Thread(target=speak, args=(response,), daemon=True).start()

    def closeEvent(self, event):
        self.worker.stop()
        self.worker.wait(1000)
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    if os.path.exists(ICON_PATH):
        app.setWindowIcon(QIcon(ICON_PATH))
    window = MainWindow()
    if os.path.exists(ICON_PATH):
        window.setWindowIcon(QIcon(ICON_PATH))
    window.show()
    sys.exit(app.exec())
