"""Okno główne: nawigacja po lewej, strony po prawej, samouczek w dymkach, zero osobnych okien dialogowych."""
import sys
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QApplication, QButtonGroup, QFrame, QHBoxLayout, QLabel, QMainWindow, QPushButton, QStackedWidget, QVBoxLayout,
    QWidget,
)

from boxbox.gui import texts, theme
from boxbox.gui.pages import Context, HomePage, ProfilePage, ProgressPage, SettingsPage, WizardPage
from boxbox.gui.settings import Settings
from boxbox.gui.widgets import Bubble

ROOT = Path(__file__).resolve().parent.parent.parent
LOGO = ROOT / "assets" / "logo.png"


class MainWindow(QMainWindow):
    def __init__(self, data_dir: Path = Path("data")) -> None:
        super().__init__()
        self.setWindowTitle(f"{texts.APP_NAME} {texts.VERSION}")
        self.resize(1180, 820)
        settings_path = data_dir / "settings.json"
        self.ctx = Context(Settings.load(settings_path), settings_path, data_dir / "boxbox.sqlite", data_dir)
        central = QWidget()
        self.setCentralWidget(central)
        outer = QHBoxLayout(central)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        side = QFrame()
        side.setObjectName("panel")
        side.setFixedWidth(220)
        side_lay = QVBoxLayout(side)
        side_lay.setContentsMargins(12, 16, 12, 16)
        logo = QLabel()
        if LOGO.exists():
            logo.setPixmap(QPixmap(str(LOGO)).scaledToWidth(180, Qt.TransformationMode.SmoothTransformation))
            logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        else:
            logo.setText(texts.APP_NAME)
            logo.setObjectName("h2")
        side_lay.addWidget(logo)
        side_lay.addSpacing(12)
        self.nav_group = QButtonGroup(self)
        self.nav_buttons: dict[str, QPushButton] = {}
        for key, title in texts.NAV.items():
            btn = QPushButton(title)
            btn.setObjectName("nav")
            btn.setCheckable(True)
            btn.setProperty("page", key)
            self.nav_group.addButton(btn)
            self.nav_buttons[key] = btn
            side_lay.addWidget(btn)
            btn.clicked.connect(lambda _checked=False, k=key: self.show_page(k))
        side_lay.addStretch(1)
        self.version = QLabel(texts.VERSION)
        self.version.setObjectName("muted")
        side_lay.addWidget(self.version)
        outer.addWidget(side)

        self.stack = QStackedWidget()
        outer.addWidget(self.stack, 1)
        self.pages: dict[str, QWidget] = {
            "home": HomePage(self.ctx), "profile": ProfilePage(self.ctx), "progress": ProgressPage(self.ctx),
            "settings": SettingsPage(self.ctx), "wizard": WizardPage(self.ctx),
        }
        for page in self.pages.values():
            self.stack.addWidget(page)
        self.pages["home"].session_finished.connect(self.on_session_finished)
        self.pages["settings"].tutorial_requested.connect(self.start_tutorial)
        self.pages["settings"].wizard_requested.connect(lambda: self.show_page("wizard"))
        self.pages["wizard"].finished.connect(self.on_wizard_done)

        self.bubble = Bubble(central)
        self.bubble.next_clicked.connect(self.tutorial_next)
        self.bubble.closed.connect(self.tutorial_close)
        self.tutorial_index = -1

        self.setStyleSheet(theme.QSS)
        self.ctx.start_probe()
        if not self.ctx.settings.wizard_done:
            self.show_page("wizard")
        else:
            self.show_page("home")
            if not self.ctx.settings.tutorial_done:
                QTimer.singleShot(400, self.start_tutorial)

    # nawigacja
    def show_page(self, key: str) -> None:
        self.stack.setCurrentWidget(self.pages[key])
        if key in self.nav_buttons:
            self.nav_buttons[key].setChecked(True)
        else:  # kreator nie ma przycisku w nawigacji: żaden nie świeci
            self.nav_group.setExclusive(False)
            for btn in self.nav_buttons.values():
                btn.setChecked(False)
            self.nav_group.setExclusive(True)
        if key == "profile":
            self.pages["profile"].reload()
        elif key == "progress":
            self.pages["progress"].reload()

    def current_page(self) -> str:
        for key, page in self.pages.items():
            if page is self.stack.currentWidget():
                return key
        return ""

    def on_session_finished(self) -> None:
        self.pages["profile"].reload()
        self.pages["progress"].reload()

    def on_wizard_done(self) -> None:
        self.pages["profile"].reload()
        self.show_page("home")
        if not self.ctx.settings.tutorial_done:
            QTimer.singleShot(300, self.start_tutorial)

    # samouczek
    def tutorial_target(self, name: str) -> QWidget | None:
        if name.startswith("nav_"):
            return self.nav_buttons.get(name[4:])
        home = self.pages["home"]
        return {"status": home.status, "go": home.go, "live": home.live_frame}.get(name)

    def start_tutorial(self) -> None:
        self.tutorial_index = -1
        self.tutorial_next()

    def tutorial_next(self) -> None:
        self.tutorial_index += 1
        if self.tutorial_index >= len(texts.TUTORIAL):
            self.tutorial_close()
            return
        page, target_name, text = texts.TUTORIAL[self.tutorial_index]
        self.show_page(page)
        target = self.tutorial_target(target_name) or self.nav_buttons["home"]
        QTimer.singleShot(0, lambda: self.bubble.show_at(target, text, self.tutorial_index, len(texts.TUTORIAL)))

    def tutorial_close(self) -> None:
        self.bubble.hide()
        self.tutorial_index = -1
        self.ctx.settings.tutorial_done = True
        self.ctx.save()

    def closeEvent(self, event) -> None:  # noqa: N802
        self.pages["home"].shutdown()
        self.ctx.stop_probe()
        super().closeEvent(event)


def run(argv: list[str] | None = None) -> int:
    app = QApplication.instance() or QApplication(argv or sys.argv)
    app.setApplicationName(texts.APP_NAME)
    if LOGO.exists():
        app.setWindowIcon(QIcon(str(LOGO)))
    window = MainWindow()
    window.show()
    return app.exec()
