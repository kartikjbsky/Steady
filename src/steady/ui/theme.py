from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication


# The asset is included in the Python package and in PyInstaller builds.
THREADS_ASSET = Path(__file__).resolve().parents[1] / "assets" / "ambient_threads.png"
PAPER_ASSET = Path(__file__).resolve().parents[1] / "assets" / "warm_paper.png"


def _dark_stylesheet() -> str:
    background_rule = ""
    if THREADS_ASSET.is_file():
        image_url = THREADS_ASSET.as_uri()
        background_rule = (
            f'background-image: url("{image_url}"); '
            "background-repeat: no-repeat; background-position: left center;"
        )

    return f"""
QWidget {{
    font-size: 12pt;
    color: #F2F0DF;
}}
QMainWindow, QWidget#root {{
    background-color: #05070A;
}}
QStackedWidget#pageStack, QStackedWidget {{
    background-color: #070A0E;
    background-image: none;
    border: 0;
}}
QWidget#page {{
    background-color: #070A0E;
    {background_rule}
}}
QScrollArea {{
    background-color: #070A0E;
    background-image: none;
    border: 0;
}}
QScrollArea::viewport {{
    background-color: #070A0E;
    background-image: none;
}}
QWidget#scrollContent {{
    background-color: #070A0E;
    {background_rule}
}}
QFrame#sidebar {{
    background-color: #090D12;
    border: 0;
    border-right: 1px solid #222B34;
}}
QFrame#sidebarDivider {{ border: 0; border-top: 1px solid #29343D; max-height: 1px; }}
QScrollArea {{ background: transparent; border: 0; }}
QScrollArea::viewport {{ background: transparent; }}
QLabel#brand {{
    color: #F3F0DB;
    font-size: 22pt;
    font-weight: 700;
    letter-spacing: 3px;
}}
QLabel#pageTitle {{
    color: #F5F1D9;
    font-size: 27pt;
    font-weight: 750;
    letter-spacing: 0.2px;
}}
QLabel#muted {{
    color: #B8BDB9;
    font-size: 11pt;
}}
QPushButton#navButton {{
    text-align: left;
    padding: 11px 13px;
    min-height: 20px;
    border: 1px solid transparent;
    border-left: 3px solid transparent;
    border-radius: 8px;
    color: #C7CCC9;
    background: transparent;
    font-size: 11.5pt;
    font-weight: 550;
}}
QPushButton#navButton:hover {{
    background: rgba(180, 194, 201, 0.08);
    color: #F5F1E3;
}}
QPushButton#navButton:checked {{
    background: rgba(215, 207, 160, 0.12);
    border-left: 3px solid #D9D0A4;
    color: #FFFBE7;
    font-weight: 650;
}}
QFrame#card {{
    background-color: rgba(13, 19, 26, 226);
    border: 1px solid #29343E;
    border-radius: 15px;
}}
QFrame#innerCard {{
    background-color: rgba(20, 28, 36, 225);
    border: 1px solid #303D48;
    border-radius: 11px;
}}
QPushButton {{
    background-color: #1A242D;
    color: #E7E8DF;
    border: 1px solid #3B4852;
    border-radius: 8px;
    padding: 8px 12px;
    min-height: 18px;
}}
QPushButton:hover {{
    background-color: #27343F;
    border-color: #748796;
}}
QPushButton:pressed {{
    background-color: #34434F;
}}
QPushButton:disabled {{
    color: #77838A;
    background-color: #131A20;
    border-color: #29323A;
}}
QPushButton#primaryButton {{
    background-color: #D8D0A7;
    color: #101318;
    border: 1px solid #E8DFB4;
    border-radius: 8px;
    padding: 9px 15px;
    font-weight: 650;
}}
QPushButton#primaryButton:hover {{
    background-color: #E8E0B8;
    border-color: #F5EBC3;
}}
QPushButton#subtleButton {{
    background-color: rgba(15, 22, 29, 110);
    border: 1px solid #43515C;
    border-radius: 8px;
    padding: 7px 11px;
    color: #D7DDD9;
}}
QPushButton#subtleButton:hover {{
    background-color: #202C36;
    border-color: #8293A0;
    color: #FFFFFF;
}}
QPushButton#dangerButton {{
    background-color: #4D2929;
    color: #FFEAE5;
    border: 1px solid #995C55;
    border-radius: 8px;
    padding: 7px 11px;
    font-weight: 650;
}}
QPushButton#dangerButton:hover {{
    background-color: #633531;
    border-color: #C47C70;
}}
QPushButton:focus, QComboBox:focus, QLineEdit:focus,
QSpinBox:focus, QDateEdit:focus, QTextEdit:focus, QCheckBox:focus {{
    border: 2px solid #D9D0A4;
}}
QComboBox, QLineEdit, QSpinBox, QDoubleSpinBox, QDateEdit, QDateTimeEdit, QTimeEdit, QTextEdit {{
    background-color: #111922;
    color: #F0F0E5;
    border: 1px solid #3A4854;
    border-radius: 7px;
    padding: 7px 9px;
    selection-background-color: #756F51;
    selection-color: #FFFFFF;
}}
QComboBox:hover, QLineEdit:hover, QSpinBox:hover, QDateEdit:hover,
QDateTimeEdit:hover, QTimeEdit:hover, QTextEdit:hover {{
    border-color: #6D7E89;
}}
QComboBox QAbstractItemView {{
    background-color: #111922;
    color: #F0F0E5;
    selection-background-color: #384B58;
    selection-color: #FFFFFF;
    border: 1px solid #536471;
}}
QCheckBox {{
    spacing: 8px;
    color: #E9E9DE;
}}
QCheckBox::indicator {{
    width: 22px;
    height: 22px;
    border: 1px solid #81909A;
    border-radius: 4px;
    background: #111820;
}}
QCheckBox::indicator:hover {{
    border: 2px solid #D9D0A4;
}}
QCheckBox::indicator:checked {{
    background: #D9D0A4;
    border: 1px solid #E9E0B9;
}}
QCheckBox::indicator:disabled {{
    background: #222D36;
    border-color: #4E5A64;
}}
QProgressBar {{
    border: 1px solid #303C46;
    border-radius: 6px;
    background: #17212A;
    height: 11px;
    text-align: center;
}}
QProgressBar::chunk {{
    background: #B7C8A7;
    border-radius: 5px;
}}
QLabel#timerClock {{
    color: #F8F3DC;
    font-size: 45pt;
    font-weight: 300;
    letter-spacing: 3px;
}}
QTableWidget {{
    background-color: rgba(12, 18, 25, 238);
    alternate-background-color: rgba(22, 31, 40, 238);
    color: #E9ECE5;
    gridline-color: #34414B;
    border: 1px solid #2B3842;
    border-radius: 9px;
    selection-background-color: #354653;
    selection-color: #FFFCEB;
}}
QTableWidget::item {{
    padding: 7px 5px;
    border-bottom: 1px solid rgba(65, 79, 90, 100);
}}
QHeaderView::section {{
    background-color: #17222C;
    color: #DDDCCB;
    border: 0;
    border-bottom: 1px solid #485560;
    padding: 9px 7px;
    font-weight: 750;
    font-size: 11.5pt;
}}
QFrame#habitRow {{
    background-color: rgba(18, 26, 34, 220);
    border: 1px solid #303C46;
    border-radius: 10px;
}}
QPushButton#calendarDay {{
    text-align: left;
    padding: 9px;
    min-height: 70px;
    background-color: rgba(14, 21, 28, 235);
    border: 1px solid #2B3943;
    border-radius: 9px;
    color: #EBEDE4;
    font-size: 10.5pt;
    font-weight: 500;
}}
QPushButton#calendarDay:hover {{
    background-color: #1C2933;
    border: 1px solid #8395A0;
}}
QPushButton#calendarDay[today="true"] {{
    border: 1.5px solid #D9D0A4;
}}
QPushButton#calendarDay[hasActivity="true"] {{
    border-left: 3px solid #A8C5AE;
}}
QPushButton#calendarDay[selected="true"] {{
    background-color: #263640;
    border: 2px solid #D9D0A4;
    color: #FFFBE9;
}}
QPushButton#calendarDay[outside="true"] {{
    color: #78858D;
    background-color: rgba(8, 12, 16, 220);
    border: 1px solid #202A32;
}}
QLabel#calendarLegendToday {{ color: #D9D0A4; }}
QLabel#calendarLegendSelected {{ color: #E7DFAF; }}
QLabel#calendarLegendActivity {{ color: #A8C5AE; }}
QLabel#fieldLabel {{ color: #E8E6D7; font-weight: 600; }}
QToolTip {{
    background-color: #17222C;
    color: #F5F1DF;
    border: 1px solid #7E8C94;
    padding: 6px;
}}
QScrollBar:vertical {{
    background: #0D141B;
    width: 12px;
    margin: 2px;
}}
QScrollBar::handle:vertical {{
    background: #465763;
    min-height: 28px;
    border-radius: 5px;
}}
QScrollBar::handle:vertical:hover {{ background: #758995; }}
QScrollBar:horizontal {{
    background: #0D141B;
    height: 12px;
    margin: 2px;
}}
QScrollBar::handle:horizontal {{
    background: #465763;
    min-width: 28px;
    border-radius: 5px;
}}
QScrollBar::handle:horizontal:hover {{ background: #758995; }}
QMessageBox {{
    background-color: #0E151C;
}}
QMenu {{
    background-color: #111922;
    color: #F0F0E5;
    border: 1px solid #536471;
}}
QMenu::item:selected {{ background-color: #354653; }}
"""


def _light_stylesheet() -> str:
    paper_rule = ""
    if PAPER_ASSET.is_file():
        paper_rule = (
            f'background-image: url("{PAPER_ASSET.as_uri()}"); '
            "background-repeat: repeat;"
        )

    return f"""
QWidget {{
    font-size: 12pt;
    color: #38291F;
}}
QMainWindow, QWidget#root {{
    background-color: #CDBE9F;
}}
QStackedWidget#pageStack, QStackedWidget {{
    background-color: #D1C3A5;
    border: 0;
}}
QWidget#page {{
    background-color: #D1C3A5;
    {paper_rule}
}}
QFrame#sidebar {{
    background-color: #BDAA86;
    border: 0;
    border-right: 1px solid #A89570;
}}
QFrame#sidebarDivider {{
    border: 0;
    border-top: 1px solid #A99774;
    max-height: 1px;
}}
QScrollArea {{
    background-color: #D1C3A5;
    {paper_rule}
    border: 0;
}}
QScrollArea::viewport {{
    background-color: #D1C3A5;
    {paper_rule}
}}
QWidget#scrollContent {{
    background-color: #D1C3A5;
    {paper_rule}
}}
QLabel#brand {{
    color: #38271D;
    font-size: 22pt;
    font-weight: 750;
    letter-spacing: 3px;
}}
QLabel#pageTitle {{
    color: #35251C;
    font-family: 'Noto Serif', 'Georgia', 'Liberation Serif', serif;
    font-size: 27pt;
    font-weight: 800;
    letter-spacing: 0.1px;
}}
QLabel#muted {{
    color: #6E5B48;
    font-size: 11pt;
}}
QPushButton#navButton {{
    text-align: left;
    padding: 11px 13px;
    min-height: 20px;
    border: 1px solid transparent;
    border-left: 3px solid transparent;
    border-radius: 8px;
    color: #4D3B2D;
    background: transparent;
    font-size: 11.5pt;
    font-weight: 550;
}}
QPushButton#navButton:hover {{
    background-color: rgba(116, 73, 54, 0.10);
    color: #302117;
}}
QPushButton#navButton:checked {{
    background-color: #D0C2A4;
    border-left: 3px solid #9A4A43;
    color: #38251D;
    font-weight: 750;
}}
QFrame#card {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #E4D8BF, stop:1 #DDD0B4);
    border: 1px solid #C1B08F;
    border-radius: 15px;
}}
QFrame#innerCard {{
    background-color: #DCD0B5;
    border: 1px solid #C5B392;
    border-radius: 11px;
}}
QPushButton {{
    background-color: #D9C9A9;
    color: #493426;
    border: 1px solid #B7A27D;
    border-radius: 8px;
    padding: 8px 12px;
    min-height: 18px;
}}
QPushButton:hover {{
    background-color: #E1D2B4;
    border-color: #92785A;
}}
QPushButton:pressed {{
    background-color: #C7B48F;
}}
QPushButton:disabled {{
    color: #91816B;
    background-color: #D5C9AE;
    border-color: #C7B99A;
}}
QPushButton#primaryButton {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #A84D47, stop:1 #873A36);
    color: #FFF4E2;
    border: 1px solid #78312E;
    border-radius: 8px;
    padding: 9px 15px;
    font-weight: 750;
}}
QPushButton#primaryButton:hover {{
    background: #B65A52;
    border-color: #6F2E2A;
}}
QPushButton#primaryButton:pressed {{
    background: #77312E;
}}
QPushButton#subtleButton {{
    background-color: rgba(220, 207, 181, 0.72);
    border: 1px solid #AE9B79;
    border-radius: 8px;
    padding: 7px 11px;
    color: #594330;
}}
QPushButton#subtleButton:hover {{
    background-color: #E5D8BD;
    border-color: #8E7255;
    color: #38271D;
}}
QPushButton#dangerButton {{
    background-color: #E7C8BD;
    color: #772F2B;
    border: 1px solid #B36B5B;
    border-radius: 8px;
    padding: 7px 11px;
    font-weight: 750;
}}
QPushButton#dangerButton:hover {{
    background-color: #EBCFC4;
    border-color: #95473E;
}}
QPushButton:focus, QComboBox:focus, QLineEdit:focus,
QSpinBox:focus, QDateEdit:focus, QTextEdit:focus, QCheckBox:focus {{
    border: 2px solid #9A4A43;
}}
QComboBox, QLineEdit, QSpinBox, QDoubleSpinBox, QDateEdit, QDateTimeEdit, QTimeEdit, QTextEdit {{
    background-color: #E8DCC3;
    color: #38291F;
    border: 1px solid #B7A583;
    border-radius: 7px;
    padding: 7px 9px;
    selection-background-color: #9A4A43;
    selection-color: #FFF4E2;
}}
QComboBox:hover, QLineEdit:hover, QSpinBox:hover, QDateEdit:hover,
QDateTimeEdit:hover, QTimeEdit:hover, QTextEdit:hover {{
    border-color: #927657;
}}
QComboBox QAbstractItemView {{
    background-color: #E8DCC3;
    color: #38291F;
    selection-background-color: #D2BBA0;
    selection-color: #38291F;
    border: 1px solid #A99470;
}}
QCheckBox {{
    spacing: 8px;
    color: #493629;
}}
QCheckBox::indicator {{
    width: 22px;
    height: 22px;
    border: 1px solid #8E795D;
    border-radius: 5px;
    background-color: #E9DFC9;
}}
QCheckBox::indicator:hover {{
    border: 2px solid #9A4A43;
    background-color: #F0E5D0;
}}
QCheckBox::indicator:checked {{
    background-color: #A84D47;
    border: 1px solid #873A36;
}}
QCheckBox::indicator:disabled {{
    background-color: #D2C5AA;
    border-color: #B7A685;
}}
QProgressBar {{
    border: 1px solid #B5A17C;
    border-radius: 6px;
    background-color: #D4C7AB;
    height: 11px;
    text-align: center;
}}
QProgressBar::chunk {{
    background-color: #89936D;
    border-radius: 5px;
}}
QLabel#timerClock {{
    color: #3E2D23;
    font-size: 45pt;
    font-weight: 450;
    letter-spacing: 3px;
}}
QTableWidget {{
    background-color: #E6DBC4;
    alternate-background-color: #DED2B9;
    color: #3D2D22;
    gridline-color: #C6B693;
    border: 1px solid #C1B18F;
    border-radius: 9px;
    selection-background-color: #D0BDA0;
    selection-color: #35251C;
}}
QTableWidget::item {{
    padding: 7px 5px;
    border-bottom: 1px solid #D0C2A6;
}}
QHeaderView::section {{
    background-color: #D2C3A4;
    color: #4A3728;
    border: 0;
    border-bottom: 1px solid #B6A17D;
    padding: 9px 7px;
    font-weight: 800;
    font-size: 11.5pt;
}}
QFrame#habitRow {{
    background-color: #DED2B9;
    border: 1px solid #C3B18D;
    border-radius: 10px;
}}
QPushButton#calendarDay {{
    text-align: left;
    padding: 9px;
    min-height: 70px;
    background-color: #E4D9C2;
    border: 1px solid #C6B693;
    border-radius: 9px;
    color: #3D2D22;
    font-size: 10.5pt;
    font-weight: 600;
}}
QPushButton#calendarDay:hover {{
    background-color: #EADDc5;
    border: 1px solid #9C8464;
}}
QPushButton#calendarDay[today="true"] {{
    border: 1.5px solid #A34D46;
}}
QPushButton#calendarDay[hasActivity="true"] {{
    border-left: 3px solid #89936D;
}}
QPushButton#calendarDay[selected="true"] {{
    background-color: #D3C1A1;
    border: 2px solid #9A4A43;
    color: #35251C;
}}
QPushButton#calendarDay[outside="true"] {{
    color: #8A7A65;
    background-color: #D4C8AE;
    border: 1px solid #C7B99B;
}}
QLabel#calendarLegendToday {{ color: #9A4A43; }}
QLabel#calendarLegendSelected {{ color: #6C4A31; }}
QLabel#calendarLegendActivity {{ color: #697A50; }}
QLabel#fieldLabel {{ color: #493629; font-weight: 750; }}
QToolTip {{
    background-color: #F0E5D0;
    color: #38291F;
    border: 1px solid #9E8967;
    padding: 6px;
}}
QScrollBar:vertical {{
    background-color: #CBBE9F;
    width: 12px;
    margin: 2px;
}}
QScrollBar::handle:vertical {{
    background-color: #A89572;
    min-height: 28px;
    border-radius: 5px;
}}
QScrollBar::handle:vertical:hover {{ background-color: #8E795D; }}
QScrollBar:horizontal {{
    background-color: #CBBE9F;
    height: 12px;
    margin: 2px;
}}
QScrollBar::handle:horizontal {{
    background-color: #A89572;
    min-width: 28px;
    border-radius: 5px;
}}
QScrollBar::handle:horizontal:hover {{ background-color: #8E795D; }}
QMessageBox {{
    background-color: #DED2B9;
    color: #38291F;
}}
QMenu {{
    background-color: #E8DCC3;
    color: #38291F;
    border: 1px solid #A99470;
}}
QMenu::item:selected {{ background-color: #D2BBA0; }}
"""



def apply_theme(app: QApplication, mode: str) -> None:
    """Apply Steady's warm-paper light theme or luminous dark theme."""
    dark = mode.lower() == "dark"
    palette = QPalette()
    if dark:
        palette.setColor(QPalette.ColorRole.Window, QColor("#070A0E"))
        palette.setColor(QPalette.ColorRole.WindowText, QColor("#F2F0DF"))
        palette.setColor(QPalette.ColorRole.Base, QColor("#0D141B"))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#17212A"))
        palette.setColor(QPalette.ColorRole.Text, QColor("#F2F0DF"))
        palette.setColor(QPalette.ColorRole.Button, QColor("#1A242D"))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor("#E7E8DF"))
        palette.setColor(QPalette.ColorRole.Highlight, QColor("#59664E"))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#FFFBE7"))
        app.setStyleSheet(_dark_stylesheet())
    else:
        palette.setColor(QPalette.ColorRole.Window, QColor("#D1C3A5"))
        palette.setColor(QPalette.ColorRole.WindowText, QColor("#38291F"))
        palette.setColor(QPalette.ColorRole.Base, QColor("#E6DBC4"))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#D1C3A5"))
        palette.setColor(QPalette.ColorRole.Text, QColor("#38291F"))
        palette.setColor(QPalette.ColorRole.Button, QColor("#D9C9A9"))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor("#38291F"))
        palette.setColor(QPalette.ColorRole.Highlight, QColor("#9A4A43"))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#FFF4E2"))
        app.setStyleSheet(_light_stylesheet())
    app.setPalette(palette)
