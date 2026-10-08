# -*- coding: utf-8 -*-
"""HSTech - Hệ thống chấm công nhân viên bằng nhận diện khuôn mặt.
Chạy: python main.py
Yêu cầu: pip install -r requirements.txt
Đăng nhập mặc định: admin / 123456
"""
import sys
import os
import traceback
from datetime import datetime
from PyQt5.QtWidgets import QApplication, QMessageBox

import db
from style import APP_STYLESHEET
from pages.login import LoginWindow
from pages.main_window import MainWindow

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_PATH = os.path.join(BASE_DIR, "error_log.txt")


def install_global_error_handler():
    """Bắt mọi lỗi không lường trước trong toàn bộ app (kể cả bên trong các
    hàm xử lý sự kiện PyQt) để tránh app tự thoát ngang không rõ lý do —
    thay vào đó hiện hộp thoại lỗi và ghi chi tiết vào error_log.txt để dễ
    tìm nguyên nhân, đồng thời cố gắng giữ app tiếp tục chạy."""
    def handle_exception(exc_type, exc_value, exc_tb):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_tb)
            return
        details = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        try:
            with open(LOG_PATH, "a", encoding="utf-8") as f:
                f.write(f"\n===== {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} =====\n")
                f.write(details)
        except Exception:
            pass
        try:
            QMessageBox.critical(
                None, "Đã xảy ra lỗi",
                "Có lỗi xảy ra và thao tác vừa rồi không thực hiện được.\n"
                f"Chi tiết lỗi đã được ghi vào file:\n{LOG_PATH}\n\n"
                f"{exc_type.__name__}: {exc_value}")
        except Exception:
            pass  # nếu QApplication chưa sẵn sàng thì bỏ qua, tránh crash kép

    sys.excepthook = handle_exception


class App:
    def __init__(self):
        install_global_error_handler()
        db.init_db(seed_demo=True)
        self.qapp = QApplication(sys.argv)
        self.qapp.setStyleSheet(APP_STYLESHEET)
        self.main_window = None
        self.login_window = None
        self.show_login()

    def show_login(self):
        if self.main_window:
            self.main_window.close()
            self.main_window = None
        self.login_window = LoginWindow(self.on_login_success)
        self.login_window.show()

    def on_login_success(self, user):
        self.login_window.close()
        self.main_window = MainWindow(user, logout_callback=self.show_login)
        self.main_window.show()

    def run(self):
        sys.exit(self.qapp.exec_())


if __name__ == "__main__":
    App().run()
