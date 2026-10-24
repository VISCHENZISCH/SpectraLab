"""Thème sombre « verre dépoli » de SpectraLab : jetons de couleur et feuille de style Qt.

Fond bleu nuit éclairé par des halos ; cartes translucides à liseré clair
(effet verre) ; un accent en dégradé azur → cyan. Tous les éléments ont des
coins arrondis : un rayon par niveau (carte, contrôle, pastille).
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QColor, QFont, QFontDatabase

_ASSETS = Path(__file__).resolve().parent / "assets"

# ── Couleurs ──
BG = "#050506"  # noir profond
RAISED = "#101012"  # fond opaque d'un graphique ou d'un aperçu, posé sur une carte
RAISED_2 = "#18181B"
DARK = "#000000"  # écran (spectrogramme, vidéo)
TEXT = "#F5F5F7"
TEXT_2 = "#A1A1A6"
TEXT_3 = "#636366"
ON_ACCENT = "#0A0A0B"  # texte sur l'accent blanc
ON_DARK = TEXT
INK = ON_ACCENT

ACCENT = "#F5F5F7"  # blanc : action principale, sélection, courbe principale
ACCENT_2 = "#8E8E93"  # gris : seconde série, dégradés
ACCENT_SOFT = "rgba(255,255,255,30)"
VIOLET = "#C7C7CC"
GOOD = "#30D158"
CORAL = "#FF453A"
AMBER = "#FFD60A"
CYAN = "#98989D"  # information (gravité faible), volontairement neutre
LCD = ACCENT  # pastille de mesure en temps normal
WHITE = RAISED  # compatibilité : « surface claire » du thème précédent

BUTTON = "#1C1C1E"  # gris anthracite des boutons
BUTTON_HOVER = "#2C2C2E"
BUTTON_ACTIVE = "#3A3A3C"

# Halos très discrets : sur du noir pur, le verre n'aurait rien à refléter.
GLOWS = (
    (0.90, -0.10, 0.65, QColor(255, 255, 255, 16)),
    (0.05, 1.05, 0.60, QColor(255, 255, 255, 9)),
)

SEVERITY_COLORS = {3: CORAL, 2: AMBER, 1: CYAN}

# ── Espacements (multiples de 4 px) ──
TIGHT = 8  # libellé ↔ valeur, pastilles voisines
ROW = 12  # éléments d'une même carte
GAP = 16  # entre deux cartes
PAD = 20  # marge intérieure d'une carte
PANEL = 18  # marge intérieure d'un panneau d'instrument
GUTTER = 28  # marge du contenu autour des pages

# ── Rayons (≤ moitié de la hauteur de l'élément, sinon Qt dessine des angles droits) ──
RADIUS_CARD = 24
RADIUS_INNER = 16  # graphique, aperçu ou champ posé dans une carte
RADIUS_CONTROL = 12  # champs, listes déroulantes
RADIUS_CHIP = 12
RADIUS_PILL = 16

_SANS = ["Inter", "Manrope", "Segoe UI Variable Text", "Segoe UI", "Cantarell", "Noto Sans"]
_DISPLAY = ["Inter Display", "Inter", "Manrope", "Segoe UI Variable Display", "Segoe UI", "Cantarell"]
_MONO = ["JetBrains Mono", "Cascadia Mono", "Consolas", "DejaVu Sans Mono"]


def mono_family() -> str:
    return _available(_MONO)[0]


def _available(families: list[str]) -> list[str]:
    installed = set(QFontDatabase.families())
    return [f for f in families if f in installed] or families


def app_font() -> QFont:
    font = QFont()
    font.setFamilies(_available(_SANS))
    font.setPointSizeF(9.5)
    font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
    return font


def _css_families(families: list[str]) -> str:
    return ", ".join(f'"{f}"' for f in _available(families))


_GLASS = "rgba(255,255,255,10)"
_GLASS_HOVER = "rgba(255,255,255,18)"
_GLASS_BORDER = "rgba(255,255,255,20)"
_GLASS_TOP = "rgba(255,255,255,38)"
_CONTROL = BUTTON
GRADIENT = _GRADIENT = "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #FFFFFF, stop:1 #D8D8DC)"


def stylesheet() -> str:
    display = _css_families(_DISPLAY)
    mono = _css_families(_MONO)
    check = (_ASSETS / "check.svg").as_posix()
    return f"""
QWidget {{ color: {TEXT}; background: transparent; }}
QMainWindow {{ background: {BG}; }}
QToolTip {{
    color: {TEXT}; background: {RAISED_2}; border: 1px solid {_GLASS_BORDER};
    border-radius: 10px; padding: 6px 10px;
}}

/* ── Typographie ── */
QLabel#HeroTitle {{ font-family: {display}; font-size: 42px; font-weight: 300; letter-spacing: -1px; }}
QLabel#PageTitle {{ font-family: {display}; font-size: 32px; font-weight: 300; letter-spacing: -0.6px; }}
QLabel#Subtitle {{ color: {TEXT_2}; font-size: 12px; }}
QLabel#CardTitle {{ font-size: 13px; font-weight: 600; }}
QLabel#CardHint {{ color: {TEXT_2}; font-size: 11px; }}
QLabel#Caption {{ color: {TEXT_3}; font-size: 10px; font-weight: 600; letter-spacing: 0.8px; }}
QLabel#BigNumber {{ font-family: {display}; font-size: 46px; font-weight: 200; letter-spacing: -1.5px; }}
QLabel#Unit {{ color: {TEXT_3}; font-size: 12px; }}
QLabel#Mono {{ font-family: {mono}; font-size: 11px; color: {TEXT_2}; }}
QLabel#Badge {{
    background: {_CONTROL}; border: 1px solid {_GLASS_BORDER}; border-radius: 10px;
    padding: 2px 9px; font-size: 11px; font-weight: 500;
}}
QLabel#AccentBadge {{
    background: {_GRADIENT}; color: {ON_ACCENT}; border-radius: 10px; padding: 3px 9px; font-size: 11px; font-weight: 600;
}}
QLabel#Up {{ color: {GOOD}; font-size: 11px; font-weight: 600; }}
QLabel#Down {{ color: {CORAL}; font-size: 11px; font-weight: 600; }}

/* ── Cartes en verre ── */
QFrame[card="glass"], QFrame[card="panel"] {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(255,255,255,14), stop:1 rgba(255,255,255,6));
    border: 1px solid {_GLASS_BORDER}; border-top-color: {_GLASS_TOP}; border-radius: {RADIUS_CARD}px;
}}
QFrame[card="glass"][clickable="true"]:hover {{ background: {_GLASS_HOVER}; border-color: rgba(255,255,255,48); }}
QFrame[card="glass"][clickable="true"]:focus {{ border-color: rgba(255,255,255,90); }}
QFrame[card="accent"] {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 rgba(255,255,255,30), stop:1 rgba(255,255,255,10));
    border: 1px solid rgba(255,255,255,40); border-top-color: rgba(255,255,255,70); border-radius: {RADIUS_CARD}px;
}}
QFrame[card="dark"] {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #17171A, stop:1 #08080A);
    border: 1px solid {_GLASS_BORDER}; border-top-color: {_GLASS_TOP}; border-radius: {RADIUS_CARD}px;
}}
QFrame[card="dark"] QLabel#CardHint {{ color: {TEXT_2}; }}
QFrame[card="white"], QFrame#Inset {{
    background: {_CONTROL}; border: 1px solid {_GLASS_BORDER}; border-radius: {RADIUS_INNER}px;
}}

/* ── Pastilles d'icônes ── */
QLabel[chip="glass"], QLabel[chip="light"], QLabel[chip="violet"], QLabel[chip="pill"] {{
    background: {_CONTROL}; border: 1px solid {_GLASS_BORDER}; border-radius: {RADIUS_CHIP}px;
}}
QLabel[chip="accent"], QLabel[chip="pill-accent"] {{ background: {_GRADIENT}; border-radius: {RADIUS_CHIP}px; }}
QLabel[chip="pill"], QLabel[chip="pill-accent"] {{ border-radius: 20px; }}
QLabel[chip="dark"] {{ background: {DARK}; border-radius: {RADIUS_CHIP}px; }}

/* ── Rail de navigation ── */
QFrame#Sidebar {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(255,255,255,12), stop:1 rgba(255,255,255,5));
    border: 1px solid {_GLASS_BORDER}; border-top-color: {_GLASS_TOP}; border-radius: {RADIUS_CARD}px;
}}
QToolButton#NavButton {{ border: none; border-radius: 16px; padding: 0; background: transparent; }}
QToolButton#NavButton:hover {{ background: {_GLASS_HOVER}; }}
QToolButton#NavButton:checked {{ background: {BUTTON_ACTIVE}; border: 1px solid rgba(255,255,255,40); }}
QToolButton#NavButton:focus {{ outline: none; }}

/* ── Boutons ── */
QPushButton {{
    background: {_CONTROL}; color: {TEXT}; border: 1px solid {_GLASS_BORDER}; border-radius: {RADIUS_PILL}px;
    padding: 9px 16px; font-weight: 500;
}}
QPushButton:hover {{ background: {BUTTON_HOVER}; border-color: rgba(255,255,255,34); }}
QPushButton:pressed {{ background: {BUTTON_ACTIVE}; }}
QPushButton:focus {{ outline: none; }}
QPushButton:disabled {{ color: {TEXT_3}; background: rgba(255,255,255,6); border-color: rgba(255,255,255,12); }}
QPushButton[variant="primary"] {{
    background: {_GRADIENT}; color: {ON_ACCENT}; border: none; padding: 10px 20px; border-radius: 18px; font-weight: 600;
}}
QPushButton[variant="primary"]:hover {{ background: #FFFFFF; }}
QPushButton[variant="primary"]:disabled {{ background: {BUTTON}; color: {TEXT_3}; }}
QPushButton[variant="danger"] {{ color: {CORAL}; border-color: rgba(255,69,58,80); }}
QPushButton[variant="danger"]:hover {{ background: rgba(255,69,58,28); }}
QPushButton[variant="pill"] {{ border-radius: {RADIUS_PILL}px; padding: 8px 14px; color: {TEXT_2}; }}
QPushButton[variant="pill"]:hover {{ color: {TEXT}; }}
QPushButton[variant="pill"]:checked {{ background: {ACCENT}; color: {ON_ACCENT}; border: none; }}
QPushButton[variant="round"] {{
    min-width: 44px; max-width: 44px; min-height: 44px; max-height: 44px;
    padding: 0; border-radius: 22px; background: {BUTTON_ACTIVE}; border: 1px solid rgba(255,255,255,40);
}}
QPushButton[variant="round"]:hover {{ background: #48484A; }}
QPushButton[variant="round"]:disabled {{ background: {BUTTON}; }}
QPushButton[variant="icon"] {{
    min-width: 42px; max-width: 42px; min-height: 42px; max-height: 42px; padding: 0; border-radius: 21px;
}}
QPushButton[variant="ghost"] {{ background: transparent; border: none; padding: 6px 8px; border-radius: 10px; }}
QPushButton[variant="ghost"]:hover {{ background: {BUTTON_HOVER}; }}
QPushButton[variant="glass"], QPushButton[variant="light"] {{ padding: 10px 18px; border-radius: 18px; }}

/* ── Champs ── */
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
    background: {_CONTROL}; border: 1px solid {_GLASS_BORDER}; border-radius: {RADIUS_CONTROL}px;
    padding: 7px 12px; selection-background-color: {ACCENT}; selection-color: {ON_ACCENT};
}}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {{ border-color: {ACCENT}; }}
QComboBox QLineEdit {{ background: transparent; border: none; padding: 0; }}
QAbstractSpinBox QLineEdit {{ background: transparent; border: none; padding: 0; }}
QSpinBox::up-button, QSpinBox::down-button {{ width: 0; border: none; }}
QComboBox::drop-down {{ border: none; width: 22px; }}
QComboBox QAbstractItemView {{
    background: {RAISED_2}; border: 1px solid {_GLASS_BORDER}; border-radius: {RADIUS_CONTROL}px; padding: 6px;
    selection-background-color: {ACCENT_SOFT}; selection-color: {TEXT}; outline: none;
}}
QCheckBox {{ spacing: 8px; color: {TEXT_2}; }}
QCheckBox::indicator {{
    width: 18px; height: 18px; border-radius: 6px; border: 1px solid rgba(255,255,255,60); background: {_CONTROL};
}}
QCheckBox::indicator:checked {{ background: {ACCENT}; border: none; image: url("{check}"); }}
QSlider::groove:horizontal {{ height: 6px; border-radius: 3px; background: rgba(255,255,255,20); }}
QSlider::sub-page:horizontal {{ border-radius: 3px; background: {TEXT_2}; }}
QSlider::handle:horizontal {{ width: 16px; margin: -5px 0; border-radius: 8px; background: {TEXT}; }}

/* ── Listes, arbres, tableaux ── */
QListWidget, QTreeWidget, QTableWidget {{ background: transparent; border: none; outline: none; }}
QListWidget::item {{ padding: 9px 12px; border-radius: 12px; margin: 2px 0; }}
QListWidget::item:hover {{ background: {_GLASS_HOVER}; }}
QListWidget::item:selected {{ background: {ACCENT_SOFT}; color: {TEXT}; }}
/* Le fond des lignes (sélection, survol) est dessiné par RowDelegate : une pilule par ligne. */
QTreeWidget::item, QTableWidget::item {{ padding: 6px 8px; background: transparent; }}
QTreeWidget::item:selected, QTableWidget::item:selected, QTreeView::branch:selected {{
    background: transparent; color: {TEXT};
}}
QTableWidget {{ gridline-color: transparent; selection-background-color: transparent; }}
QTableCornerButton::section {{ background: transparent; border: none; }}
QHeaderView {{ background: transparent; }}
QHeaderView::section {{
    background: transparent; color: {TEXT_3}; border: none; padding: 6px 8px; font-size: 10px; font-weight: 600;
}}
QPlainTextEdit, QTextEdit {{
    background: rgba(0,0,0,70); border: 1px solid {_GLASS_BORDER}; border-radius: {RADIUS_INNER}px; padding: 10px;
    font-family: {mono}; font-size: 11px; selection-background-color: {ACCENT}; selection-color: {ON_ACCENT};
}}

/* ── Onglets en pilules ── */
QTabWidget::pane {{ border: none; }}
QTabBar {{ qproperty-drawBase: 0; }}
QTabBar::tab {{
    background: {_CONTROL}; color: {TEXT_2}; border: 1px solid {_GLASS_BORDER}; border-radius: 15px;
    padding: 7px 14px; margin-right: 6px; font-weight: 500;
}}
QTabBar::tab:hover {{ color: {TEXT}; background: {_GLASS_HOVER}; }}
QTabBar::tab:selected {{ background: {ACCENT}; color: {ON_ACCENT}; border: none; }}
QTabBar QToolButton {{ background: {RAISED_2}; border-radius: 10px; border: 1px solid {_GLASS_BORDER}; }}

/* ── Instruments ── */
QLabel#Readout {{
    font-family: {mono}; font-size: 10px; color: {TEXT_2}; background: {_CONTROL};
    border: 1px solid {_GLASS_BORDER}; border-radius: 10px; padding: 4px 9px;
}}
QLabel#Timecode {{ font-family: {display}; font-size: 22px; font-weight: 300; }}
QLabel#Preview {{
    background: rgba(0,0,0,80); border: 1px solid {_GLASS_BORDER}; border-radius: {RADIUS_INNER}px; color: {TEXT_3};
}}

/* ── Zone de dépôt ── */
QFrame#DropZone {{
    border: 2px dashed rgba(255,255,255,44); border-radius: {RADIUS_CARD}px; background: rgba(255,255,255,5);
}}
QFrame#DropZone[dragging="true"] {{ border-color: {ACCENT}; background: rgba(255,255,255,16); }}

/* ── Défilement ── */
QScrollArea {{ border: none; background: transparent; }}
/* Barres masquées : le défilement se fait à la molette ou au pavé tactile. */
QScrollBar:vertical {{ width: 0px; background: transparent; }}
QScrollBar:horizontal {{ height: 0px; background: transparent; }}
QScrollBar::handle {{ background: transparent; }}
QScrollBar::add-line, QScrollBar::sub-line, QScrollBar::add-page, QScrollBar::sub-page {{
    width: 0; height: 0; background: none;
}}

/* ── Menus et boîtes de dialogue ── */
QMenu {{ background: {RAISED_2}; border: 1px solid {_GLASS_BORDER}; border-radius: 12px; padding: 6px; }}
QMenu::item {{ padding: 7px 26px 7px 14px; border-radius: 8px; }}
QMenu::item:selected {{ background: {ACCENT_SOFT}; }}
QDialog, QMessageBox {{ background: {RAISED}; }}
QSplitter::handle {{ background: transparent; }}
"""
