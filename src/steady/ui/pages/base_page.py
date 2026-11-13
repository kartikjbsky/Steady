from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget


class BasePage(QWidget):
    def __init__(self, title: str, subtitle: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("page")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(32, 28, 32, 30)
        self.layout.setSpacing(17)

        self.title_label = QLabel(title)
        self.title_label.setObjectName("pageTitle")
        self.title_label.setAccessibleName(f"{title} page heading")
        self.subtitle_label = QLabel(subtitle)
        self.subtitle_label.setObjectName("muted")
        self.subtitle_label.setWordWrap(True)

        self.layout.addWidget(self.title_label)
        self.layout.addWidget(self.subtitle_label)
        self.layout.addSpacing(6)

    def add_card(self, title: str, body: str) -> QFrame:
        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(21, 19, 21, 19)
        card_layout.setSpacing(9)

        heading = QLabel(title)
        heading.setStyleSheet("font-size: 14pt; font-weight: 800;")
        text = QLabel(body)
        text.setObjectName("muted")
        text.setWordWrap(True)
        text.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        card_layout.addWidget(heading)
        card_layout.addWidget(text)
        self.layout.addWidget(card)
        return card
