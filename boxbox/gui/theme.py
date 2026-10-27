"""Motyw: ciemny, czerwony akcent jak w logo, cyjan dla danych na żywo."""
BG = "#0f1012"
PANEL = "#17191d"
PANEL2 = "#1f2228"
FG = "#f2f2f2"
MUTED = "#9aa0a6"
RED = "#e8232a"
CYAN = "#19e6e6"
GREEN = "#3ddc3d"
YELLOW = "#ffd34d"

QSS = f"""
QMainWindow, QWidget {{ background: {BG}; color: {FG}; font-family: 'Segoe UI', 'DejaVu Sans', sans-serif; font-size: 14px; }}
QLabel {{ background: transparent; }}
QPlainTextEdit#mono {{ font-family: 'Consolas', 'DejaVu Sans Mono', monospace; font-size: 13px; }}
QFrame#panel {{ background: {PANEL}; border: 1px solid #2a2e35; border-radius: 10px; }}
QFrame#panel2 {{ background: {PANEL2}; border-radius: 8px; }}
QLabel#h1 {{ font-size: 26px; font-weight: 700; }}
QLabel#h2 {{ font-size: 18px; font-weight: 600; color: {FG}; }}
QLabel#muted {{ color: {MUTED}; }}
QLabel#big {{ font-size: 34px; font-weight: 800; }}
QLabel#cyan {{ color: {CYAN}; font-size: 28px; font-weight: 800; }}
QLabel#red {{ color: {RED}; font-size: 18px; font-weight: 700; }}
QLabel#green {{ color: {GREEN}; }}
QLabel#yellow {{ color: {YELLOW}; font-size: 16px; font-weight: 600; }}
QLabel#stat {{ font-size: 24px; font-weight: 700; color: {CYAN}; }}
QPushButton {{ background: {PANEL2}; border: 1px solid #343941; border-radius: 8px; padding: 8px 16px; }}
QPushButton:hover {{ border-color: {RED}; }}
QPushButton:disabled {{ color: #5c6269; }}
QPushButton#go {{ background: {RED}; color: white; font-size: 22px; font-weight: 800; padding: 16px 40px; border: none; }}
QPushButton#go:hover {{ background: #ff3b42; }}
QPushButton#nav {{ background: transparent; border: none; text-align: left; padding: 12px 18px; font-size: 15px; border-radius: 8px; }}
QPushButton#nav:checked {{ background: {PANEL2}; border-left: 4px solid {RED}; }}
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QPlainTextEdit, QTextEdit {{ background: {PANEL2}; border: 1px solid #343941; border-radius: 6px; padding: 6px; }}
QSlider::groove:horizontal {{ height: 6px; background: #343941; border-radius: 3px; }}
QSlider::handle:horizontal {{ width: 16px; margin: -6px 0; background: {RED}; border-radius: 8px; }}
QTableWidget {{ background: {PANEL}; gridline-color: #2a2e35; border: none; }}
QHeaderView::section {{ background: {PANEL2}; padding: 6px; border: none; font-weight: 600; }}
QFrame#bubble {{ background: #2b1d1e; border: 2px solid {RED}; border-radius: 10px; }}
QFrame#banner {{ background: #3a1b1d; border: 1px solid {RED}; border-radius: 8px; }}
QCheckBox::indicator {{ width: 18px; height: 18px; }}
QProgressBar {{ background: {PANEL2}; border: none; border-radius: 6px; height: 12px; text-align: center; }}
QProgressBar::chunk {{ background: {GREEN}; border-radius: 6px; }}
QTreeView {{ background: {PANEL2}; border: 1px solid #343941; }}
"""
