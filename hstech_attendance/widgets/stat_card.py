# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import QFrame, QHBoxLayout, QVBoxLayout, QLabel
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont


class StatCard(QFrame):
    def __init__(self, icon_emoji, title, value, color, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        self.setMinimumHeight(90)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)

        icon_lbl = QLabel(icon_emoji)
        icon_lbl.setFixedSize(46, 46)
        icon_lbl.setAlignment(Qt.AlignCenter)
        icon_lbl.setStyleSheet(
            f"background:{color}22; color:{color}; border-radius:23px; font-size:20px;")
        layout.addWidget(icon_lbl)

        text_box = QVBoxLayout()
        text_box.setSpacing(2)
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("color:#64748B; font-size:12px;")
        self.value_lbl = QLabel(str(value))
        self.value_lbl.setFont(QFont("Segoe UI", 20, QFont.Bold))
        self.value_lbl.setStyleSheet("color:#1E293B;")
        text_box.addWidget(title_lbl)
        text_box.addWidget(self.value_lbl)
        layout.addLayout(text_box)
        layout.addStretch()

    def set_value(self, value):
        self.value_lbl.setText(str(value))
