"""Nakładka na grę w Qt: okno bez ramki, zawsze na wierzchu, czyta ten sam stan co okno główne."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget

from boxbox.gui import theme
from boxbox.ui.overlay_model import CoachView


class QtOverlay(QWidget):
    def __init__(self, scale: float = 1.0) -> None:
        super().__init__(None, Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setWindowTitle("BoxBox Academy - nakładka")
        self.setWindowOpacity(0.96)
        self.setStyleSheet(f"QWidget {{ background: #101010; color: {theme.FG}; }} QFrame#edge {{ border: 3px solid {theme.RED}; }}")
        edge = QFrame(self)
        edge.setObjectName("edge")
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(edge)
        lay = QVBoxLayout(edge)
        lay.setContentsMargins(16, 10, 16, 10)
        f = lambda size, bold=False: f"font-size: {int(size * scale)}px; font-weight: {'800' if bold else '400'};"  # noqa: E731
        self.l_lap = QLabel("")
        self.l_lap.setStyleSheet(f(26, True))
        self.l_corner = QLabel("")
        self.l_corner.setStyleSheet(f(34, True) + f"color: {theme.CYAN};")
        self.l_focus = QLabel("")
        self.l_focus.setStyleSheet(f(15, True) + f"color: {theme.YELLOW};")
        self.l_focus.setWordWrap(True)
        self.l_msg = [QLabel("") for _ in range(3)]
        for i, lab in enumerate(self.l_msg):
            lab.setWordWrap(True)
            lab.setStyleSheet(f([20, 14, 12][i], i == 0) + f"color: {[theme.RED, '#d0d0d0', '#9a9a9a'][i]};")
        self.l_progress = QLabel("")
        self.l_progress.setStyleSheet(f(12) + f"color: {theme.GREEN};")
        self.l_progress.setWordWrap(True)
        self.l_status = QLabel("")
        self.l_status.setStyleSheet(f(11) + "color: #b0b0b0;")
        self.l_status.setWordWrap(True)
        hint = QLabel("przeciągnij, aby przesunąć | zamykasz w oknie BoxBox Academy")
        hint.setStyleSheet(f(9) + "color: #808080;")
        for w in (self.l_lap, self.l_corner, self.l_focus, *self.l_msg, self.l_progress, self.l_status, hint):
            lay.addWidget(w)
        self.setFixedWidth(int(600 * scale))
        self.move(40, 40)
        self._drag = None

    def mousePressEvent(self, event) -> None:  # noqa: N802
        self._drag = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if self._drag is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag)

    def apply(self, view: CoachView, error: str | None = None) -> None:
        self.l_lap.setText(view.lap_line)
        self.l_corner.setText(view.corner_line)
        self.l_focus.setText(view.focus_line)
        for lab, text in zip(self.l_msg, list(view.messages) + ["", "", ""]):
            lab.setText(text)
        self.l_progress.setText(view.progress_line)
        self.l_status.setText(error or view.status_line)
        self.l_status.setStyleSheet(f"color: {theme.RED if error else '#b0b0b0'};")
