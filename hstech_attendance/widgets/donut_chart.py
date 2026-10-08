# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import QWidget
from PyQt5.QtGui import QPainter, QColor, QPen, QFont
from PyQt5.QtCore import Qt, QRectF


class DonutChart(QWidget):
    """Biểu đồ tròn (donut) vẽ bằng QPainter, segments = [(value, QColor, label)]."""

    def __init__(self, segments=None, center_title="", parent=None):
        super().__init__(parent)
        self.segments = segments or []
        self.center_title = center_title
        self.setMinimumSize(200, 200)

    def set_data(self, segments, center_title=""):
        self.segments = segments
        self.center_title = center_title
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        side = min(self.width(), self.height()) - 20
        rect = QRectF((self.width() - side) / 2, (self.height() - side) / 2, side, side)

        total = sum(v for v, _, _ in self.segments) or 1
        start_angle = 90 * 16
        thickness = max(18, int(side * 0.14))

        painter.setPen(QPen(QColor("#E2E8F0"), thickness))
        painter.drawArc(rect.adjusted(thickness / 2, thickness / 2, -thickness / 2, -thickness / 2),
                         0, 360 * 16)

        for value, color, _ in self.segments:
            span = int(360 * 16 * value / total)
            pen = QPen(color, thickness)
            pen.setCapStyle(Qt.FlatCap)
            painter.setPen(pen)
            painter.drawArc(rect.adjusted(thickness / 2, thickness / 2, -thickness / 2, -thickness / 2),
                             start_angle, -span)
            start_angle -= span

        painter.setPen(QColor("#1E293B"))
        painter.setFont(QFont("Segoe UI", int(side * 0.11), QFont.Bold))
        painter.drawText(rect, Qt.AlignCenter, self.center_title.split("\n")[0])
        if "\n" in self.center_title:
            sub_rect = QRectF(rect.x(), rect.y() + side * 0.14, rect.width(), rect.height())
            painter.setFont(QFont("Segoe UI", int(side * 0.06)))
            painter.setPen(QColor("#64748B"))
            painter.drawText(sub_rect, Qt.AlignCenter, self.center_title.split("\n")[1])
