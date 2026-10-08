# -*- coding: utf-8 -*-
"""Bảng màu & stylesheet dùng chung cho toàn bộ app, mô phỏng theme navy/blue
trong ảnh demo (sidebar #0B1E3F, accent xanh #2563EB, nền #F1F4F9)."""

NAVY_DARK = "#0B1E3F"
NAVY = "#0F2B54"
NAVY_LIGHT = "#15305E"
BLUE = "#2563EB"
BLUE_HOVER = "#1D4ED8"
GREEN = "#16A34A"
RED = "#DC2626"
ORANGE = "#F59E0B"
GRAY_BG = "#F1F4F9"
WHITE = "#FFFFFF"
TEXT_DARK = "#1E293B"
TEXT_MUTED = "#64748B"
BORDER = "#E2E8F0"

APP_STYLESHEET = f"""
QWidget {{
    font-family: 'Segoe UI', 'Arial';
    font-size: 13px;
    color: {TEXT_DARK};
}}
QMainWindow, #contentArea {{
    background: {GRAY_BG};
}}
#sidebar {{
    background: {NAVY_DARK};
}}
#sidebar QPushButton {{
    text-align: left;
    padding: 12px 20px;
    border: none;
    color: #C7D2E3;
    font-size: 13px;
    border-radius: 8px;
    margin: 2px 10px;
}}
#sidebar QPushButton:hover {{
    background: {NAVY_LIGHT};
    color: white;
}}
#sidebar QPushButton:checked {{
    background: {BLUE};
    color: white;
    font-weight: 600;
}}
#sidebarTitle {{
    color: white;
    font-size: 18px;
    font-weight: 700;
    padding: 22px 20px;
}}
#topBar {{
    background: {WHITE};
    border-bottom: 1px solid {BORDER};
}}
QFrame#card {{
    background: {WHITE};
    border-radius: 12px;
    border: 1px solid {BORDER};
}}
QPushButton#primaryBtn {{
    background: {BLUE};
    color: white;
    border-radius: 8px;
    padding: 10px 18px;
    font-weight: 600;
    border: none;
}}
QPushButton#primaryBtn:hover {{ background: {BLUE_HOVER}; }}
QPushButton#greenBtn {{
    background: {GREEN}; color: white; border-radius: 8px; padding: 10px 18px; font-weight: 600; border: none;
}}
QPushButton#greenBtn:hover {{ background: #128a3e; }}
QPushButton#redBtn {{
    background: {RED}; color: white; border-radius: 8px; padding: 10px 18px; font-weight: 600; border: none;
}}
QPushButton#redBtn:hover {{ background: #b91c1c; }}
QPushButton#ghostBtn {{
    background: {WHITE}; color: {TEXT_DARK}; border-radius: 8px; padding: 9px 16px; border: 1px solid {BORDER};
}}
QPushButton#ghostBtn:hover {{ background: {GRAY_BG}; }}
QLineEdit, QComboBox, QDateEdit {{
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 7px 10px;
    background: white;
}}
QLineEdit:focus, QComboBox:focus {{ border: 1px solid {BLUE}; }}
QTableWidget {{
    background: white;
    border: none;
    gridline-color: {BORDER};
}}
QHeaderView::section {{
    background: {GRAY_BG};
    color: {TEXT_MUTED};
    padding: 8px;
    border: none;
    border-bottom: 1px solid {BORDER};
    font-weight: 600;
}}
QTableWidget::item {{ padding: 6px; }}
"""
