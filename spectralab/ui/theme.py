"""Thème « dark glass » de SpectraLab : jetons de couleur et feuille de style Qt."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QColor, QFont, QFontDatabase

_ASSETS = Path(__file__).resolve().parent / "assets"

BG = "#08090E"
TEXT = "#F1F2F6"
TEXT_2 = "#A3A8BA"
TEXT_3 = "#626779"
INK = "#0B0C10"  # texte sur fond clair

LIME = "#D2F36B"
VIOLET = "#9E8CFF"
CYAN = "#5FE3D2"
CORAL = "#FF7B7B"
AMBER = "#FFC56E"

# Lueurs du fond : (x, y, rayon relatif, couleur RGBA).
GLOWS = (
    (0.08, -0.05, 0.55, QColor(210, 243, 107, 34)),
    (0.95, 0.10, 0.60, QColor(158, 140, 255, 46)),
    (0.55, 1.10, 0.65, QColor(95, 227, 210, 26)),
)

SEVERITY_COLORS = {3: CORAL, 2: AMBER, 1: CYAN}

_SANS = ["Inter", "Segoe UI Variable Text", "Segoe UI", "Cantarell", "Noto Sans"]
_DISPLAY = ["Inter Display", "Inter", "Segoe UI Variable Display", "Segoe UI", "Cantarell"]
_MONO = ["JetBrains Mono", "Cascadia Mono", "Consolas", "DejaVu Sans Mono"]


def _available(families: list[str]) -> list[str]:
    installed = set(QFontDatabase.families())
    return [f for f in families if f in installed] or families


def app_font() -> QFont:
    font = QFont()
    font.setFamilies(_available(_SANS))
    font.setPointSizeF(10)
    font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
    return font


def _css_families(families: list[str]) -> str:
    return ", ".join(f'"{f}"' for f in _available(families))


def stylesheet() -> str:
    display = _css_families(_DISPLAY)
    mono = _css_families(_MONO)
    check = (_ASSETS / "check.svg").as_posix()
    return f"""
QWidget {{ color: {TEXT}; background: transparent; }}
QToolTip {{
    color: {TEXT}; background: #15161F; border: 1px solid rgba(255,255,255,30);
    border-radius: 8px; padding: 6px 8px;
}}

/* ── Typographie ── */
QLabel#HeroTitle {{ font-family: {display}; font-size: 38px; font-weight: 300; }}
QLabel#PageTitle {{ font-family: {display}; font-size: 30px; font-weight: 400; }}
QLabel#Subtitle {{ color: {TEXT_2}; font-size: 13px; }}
QLabel#CardTitle {{ font-size: 14px; font-weight: 600; }}
QLabel#CardHint {{ color: {TEXT_2}; font-size: 12px; }}
QLabel#Caption {{
    color: {TEXT_3}; font-size: 10px; font-weight: 700; letter-spacing: 1.5px;
}}
QLabel#BigNumber {{ font-family: {display}; font-size: 52px; font-weight: 300; }}
QLabel#Unit {{ color: {TEXT_2}; font-size: 13px; }}
QLabel#Mono {{ font-family: {mono}; font-size: 12px; }}
QLabel#Badge {{
    background: rgba(255,255,255,20); border-radius: 10px; padding: 3px 9px;
    font-size: 11px; font-weight: 600;
}}

/* ── Cartes en verre ── */
QFrame[card="glass"] {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 rgba(255,255,255,17), stop:1 rgba(255,255,255,7));
    border: 1px solid rgba(255,255,255,20);
    border-top-color: rgba(255,255,255,38);
    border-radius: 24px;
}}
QFrame[card="glass"][clickable="true"]:hover {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 rgba(255,255,255,26), stop:1 rgba(255,255,255,12));
    border-color: rgba(210,243,107,90);
}}
QFrame[card="glass"][clickable="true"]:focus {{ border-color: {LIME}; }}
QFrame[card="lime"] {{ background: {LIME}; border: none; border-radius: 24px; }}
QFrame[card="lime"] QLabel {{ color: {INK}; }}
QFrame[card="lime"] QLabel#Unit, QFrame[card="lime"] QLabel#CardHint {{ color: rgba(11,12,16,150); }}
QFrame[card="lime"] QLabel#Badge {{ background: rgba(255,255,255,190); }}
QFrame[card="violet"] {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #2A2156, stop:0.55 #1A1638, stop:1 #0F1A24);
    border: 1px solid rgba(158,140,255,70);
    border-radius: 24px;
}}

/* ── Pastilles d'icônes ── */
QLabel[chip="glass"] {{ background: rgba(255,255,255,18); border-radius: 14px; }}
QLabel[chip="light"] {{ background: rgba(255,255,255,235); border-radius: 14px; }}
QLabel[chip="lime"] {{ background: {LIME}; border-radius: 14px; }}
QLabel[chip="violet"] {{ background: rgba(158,140,255,60); border-radius: 14px; }}

/* ── Barre latérale ── */
QFrame#Sidebar {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 rgba(18,19,28,240), stop:1 rgba(10,11,16,240));
    border: 1px solid rgba(255,255,255,18);
    border-radius: 28px;
}}
QLabel#Brand {{ font-family: {display}; font-size: 17px; font-weight: 600; letter-spacing: 0.5px; }}
QLabel#BrandSub {{ color: {TEXT_3}; font-size: 10px; letter-spacing: 1px; }}
QLabel#NavSection {{
    color: {TEXT_3}; font-size: 9px; font-weight: 700; letter-spacing: 1.8px; padding: 10px 14px 4px;
}}
QToolButton#NavButton {{
    border: none; border-radius: 14px; padding: 10px 14px; text-align: left;
    color: {TEXT_2}; font-size: 13px; font-weight: 500;
}}
QToolButton#NavButton:hover {{ background: rgba(255,255,255,14); color: {TEXT}; }}
QToolButton#NavButton:checked {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 rgba(210,243,107,48), stop:1 rgba(210,243,107,8));
    color: {TEXT}; font-weight: 600;
}}
QToolButton#NavButton:focus {{ outline: none; border: 1px solid rgba(210,243,107,120); }}

/* ── Panneaux d'analyse (spectre, graphiques) ── */
QFrame[card="panel"] {{
    background: rgba(6,7,12,215);
    border: 1px solid rgba(255,255,255,22);
    border-radius: 18px;
}}
QLabel#Readout {{
    font-family: {mono}; font-size: 11px; color: {TEXT_2};
    background: rgba(0,0,0,120); border-radius: 8px; padding: 4px 8px;
}}
QLabel#Timecode {{ font-family: {mono}; font-size: 20px; font-weight: 500; }}
QPlainTextEdit, QTextEdit {{
    background: rgba(0,0,0,110); border: 1px solid rgba(255,255,255,22); border-radius: 12px;
    padding: 8px; font-family: {mono}; font-size: 12px; selection-background-color: {VIOLET};
}}
QPushButton[variant="round"] {{
    min-width: 44px; max-width: 44px; min-height: 44px; max-height: 44px;
    padding: 0; border-radius: 22px; background: {LIME}; border: none;
}}
QPushButton[variant="round"]:hover {{ background: #DDF88A; }}
QPushButton[variant="round"]:disabled {{ background: rgba(210,243,107,60); }}
QPushButton[variant="ghost"] {{ background: transparent; border: none; padding: 6px 10px; }}
QPushButton[variant="ghost"]:hover {{ background: rgba(255,255,255,16); }}

/* ── Onglets ── */
QTabWidget::pane {{ border: none; }}
QTabBar {{ qproperty-drawBase: 0; }}
QTabBar::tab {{
    background: rgba(255,255,255,10); color: {TEXT_2}; border: 1px solid rgba(255,255,255,16);
    border-radius: 14px; padding: 7px 16px; margin-right: 6px; font-weight: 500;
}}
QTabBar::tab:hover {{ color: {TEXT}; background: rgba(255,255,255,18); }}
QTabBar::tab:selected {{ background: {TEXT}; color: {INK}; border-color: {TEXT}; font-weight: 600; }}

/* ── Tableaux ── */
QTableWidget {{
    background: transparent; border: none; gridline-color: rgba(255,255,255,12);
    selection-background-color: rgba(158,140,255,60); selection-color: {TEXT}; outline: none;
}}
QTableWidget::item {{ padding: 4px 6px; }}
QTableCornerButton::section {{ background: transparent; border: none; }}

/* ── Boutons ── */
QPushButton {{
    background: rgba(255,255,255,16); border: 1px solid rgba(255,255,255,26);
    border-radius: 18px; padding: 9px 18px; font-weight: 600;
}}
QPushButton:hover {{ background: rgba(255,255,255,28); }}
QPushButton:focus {{ border-color: {LIME}; outline: none; }}
QPushButton:disabled {{ color: {TEXT_3}; background: rgba(255,255,255,8); }}
QPushButton[variant="primary"] {{ background: {LIME}; color: {INK}; border: none; }}
QPushButton[variant="primary"]:hover {{ background: #DDF88A; }}
QPushButton[variant="primary"]:disabled {{ background: rgba(210,243,107,60); color: rgba(11,12,16,140); }}
QPushButton[variant="danger"] {{ color: {CORAL}; border-color: rgba(255,123,123,80); }}
QPushButton[variant="danger"]:hover {{ background: rgba(255,123,123,30); }}
QPushButton[variant="pill"] {{
    background: rgba(255,255,255,12); border: 1px solid rgba(255,255,255,18);
    border-radius: 17px; padding: 8px 18px; font-weight: 500;
}}
QPushButton[variant="pill"]:checked {{ background: {TEXT}; color: {INK}; border-color: {TEXT}; }}

/* ── Champs ── */
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
    background: rgba(255,255,255,12); border: 1px solid rgba(255,255,255,26);
    border-radius: 12px; padding: 8px 12px; selection-background-color: {VIOLET};
}}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {{ border-color: {LIME}; }}
/* Champ texte interne des listes éditables et compteurs : pas de second cadre. */
QComboBox QLineEdit {{ background: transparent; border: none; padding: 0; }}
QAbstractSpinBox QLineEdit {{ background: transparent; border: none; padding: 0; }}
QSpinBox::up-button, QSpinBox::down-button {{ width: 0; border: none; }}
QComboBox::drop-down {{ border: none; width: 26px; }}
QComboBox QAbstractItemView {{
    background: #14151D; border: 1px solid rgba(255,255,255,30); border-radius: 10px;
    selection-background-color: rgba(210,243,107,50); padding: 4px; outline: none;
}}
QCheckBox {{ spacing: 8px; }}
QCheckBox::indicator {{
    width: 18px; height: 18px; border-radius: 6px;
    border: 1px solid rgba(255,255,255,60); background: rgba(255,255,255,10);
}}
QCheckBox::indicator:checked {{ background: {LIME}; border-color: {LIME}; image: url("{check}"); }}
QSlider::groove:horizontal {{ height: 6px; border-radius: 3px; background: rgba(255,255,255,25); }}
QSlider::sub-page:horizontal {{ border-radius: 3px; background: {LIME}; }}
QSlider::handle:horizontal {{
    width: 18px; margin: -7px 0; border-radius: 9px; background: {TEXT};
}}

/* ── Listes et arbres ── */
QListWidget, QTreeWidget, QTableWidget {{
    background: transparent; border: none; outline: none;
}}
QListWidget::item {{ padding: 10px 12px; border-radius: 12px; margin: 2px 0; }}
QListWidget::item:hover {{ background: rgba(255,255,255,12); }}
QListWidget::item:selected {{ background: rgba(210,243,107,40); color: {TEXT}; }}
QTreeWidget::item {{ padding: 6px 4px; }}
QTreeWidget::item:selected {{ background: rgba(158,140,255,50); color: {TEXT}; }}
QHeaderView::section {{
    background: transparent; color: {TEXT_3}; border: none;
    border-bottom: 1px solid rgba(255,255,255,20);
    padding: 6px 4px; font-size: 11px; font-weight: 700;
}}

/* ── Zone de dépôt ── */
QFrame#DropZone {{
    border: 2px dashed rgba(255,255,255,40); border-radius: 24px;
    background: rgba(255,255,255,6);
}}
QFrame#DropZone[dragging="true"] {{ border-color: {LIME}; background: rgba(210,243,107,18); }}

/* ── Défilement ── */
QScrollArea {{ border: none; }}
QScrollBar:vertical {{ width: 10px; background: transparent; margin: 4px; }}
QScrollBar:horizontal {{ height: 10px; background: transparent; margin: 4px; }}
QScrollBar::handle {{ background: rgba(255,255,255,40); border-radius: 3px; min-height: 30px; min-width: 30px; }}
QScrollBar::handle:hover {{ background: rgba(255,255,255,70); }}
QScrollBar::add-line, QScrollBar::sub-line, QScrollBar::add-page, QScrollBar::sub-page {{
    width: 0; height: 0; background: none;
}}

/* ── Boîtes de dialogue ── */
QDialog, QMessageBox {{ background: #11121A; }}
QSplitter::handle {{ background: transparent; }}
"""
