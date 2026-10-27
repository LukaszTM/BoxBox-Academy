"""Drobne widżety: panel, kafelek z liczbą, pasek błędu, dymek samouczka (w oknie, nie osobne okno)."""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from boxbox.gui import texts


def panel(parent: QWidget | None = None, name: str = "panel") -> tuple[QFrame, QVBoxLayout]:
    frame = QFrame(parent)
    frame.setObjectName(name)
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(16, 14, 16, 14)
    layout.setSpacing(8)
    return frame, layout


class StatCard(QFrame):
    def __init__(self, title: str, value: str = "–", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("panel2")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 10, 14, 10)
        self.value = QLabel(value)
        self.value.setObjectName("stat")
        title_label = QLabel(title)
        title_label.setObjectName("muted")
        lay.addWidget(self.value)
        lay.addWidget(title_label)

    def set(self, value: str) -> None:
        self.value.setText(value)


class Banner(QFrame):
    """Czerwony pasek z błędem wewnątrz okna, zamiast wyskakującego komunikatu."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("banner")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 8, 12, 8)
        self.label = QLabel("")
        self.label.setWordWrap(True)
        close = QPushButton("×")
        close.setFixedWidth(32)
        close.clicked.connect(self.hide)
        lay.addWidget(self.label, 1)
        lay.addWidget(close)
        self.hide()

    def show_text(self, text: str) -> None:
        self.label.setText(text)
        self.show()


class Bubble(QFrame):
    """Dymek samouczka: dziecko okna głównego, pozycjonowany obok wskazanego widżetu."""

    next_clicked = Signal()
    closed = Signal()

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setObjectName("bubble")
        self.setFixedWidth(360)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 12, 14, 12)
        self.step = QLabel("")
        self.step.setObjectName("muted")
        self.text = QLabel("")
        self.text.setWordWrap(True)
        buttons = QHBoxLayout()
        self.btn_close = QPushButton(texts.TUTORIAL_DONE)
        self.btn_next = QPushButton(texts.TUTORIAL_NEXT)
        self.btn_close.clicked.connect(self.closed.emit)
        self.btn_next.clicked.connect(self.next_clicked.emit)
        buttons.addWidget(self.btn_close)
        buttons.addStretch(1)
        buttons.addWidget(self.btn_next)
        lay.addWidget(self.step)
        lay.addWidget(self.text)
        lay.addLayout(buttons)
        self.hide()

    def show_at(self, target: QWidget, text: str, index: int, total: int) -> None:
        self.step.setText(texts.TUTORIAL_STEP.format(i=index + 1, n=total))
        self.text.setText(text)
        self.btn_next.setText(texts.TUTORIAL_NEXT if index + 1 < total else texts.TUTORIAL_DONE)
        self.adjustSize()
        parent = self.parentWidget()
        pos = target.mapTo(parent, target.rect().bottomLeft())
        x = min(max(8, pos.x()), max(8, parent.width() - self.width() - 8))
        y = pos.y() + 8
        if y + self.height() > parent.height() - 8:
            y = max(8, target.mapTo(parent, target.rect().topLeft()).y() - self.height() - 8)
        self.move(x, y)
        self.raise_()
        self.show()


def row(*widgets: QWidget, stretch_last: bool = False) -> QHBoxLayout:
    lay = QHBoxLayout()
    for w in widgets:
        lay.addWidget(w)
    if stretch_last:
        lay.addStretch(1)
    return lay


def label(text: str, name: str = "", align_center: bool = False) -> QLabel:
    lab = QLabel(text)
    if name:
        lab.setObjectName(name)
    lab.setWordWrap(True)
    if align_center:
        lab.setAlignment(Qt.AlignmentFlag.AlignCenter)
    return lab
