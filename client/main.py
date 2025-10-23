# client/main.py
import sys
from datetime import datetime
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QLabel, QPushButton,
    QVBoxLayout, QWidget, QTextEdit, QMessageBox
)
from PyQt6.QtCore import Qt
from .db import init_db, get_db
from .local_models import User, Device
from .worker import DatabaseWorker
from .cleanup import cleanup_old_data
from .sync import sync_to_cloud

class HealthClient(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Headset Health Monitor (FREE)")
        self.setGeometry(100, 100, 500, 600)

        self.user_id = None
        self.device_id = None
        self.worker = None

        # GUI
        central = QWidget()
        layout = QVBoxLayout()

        self.status_label = QLabel("Инициализация...")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("font-size: 16px; font-weight: bold;")

        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setStyleSheet("font-family: Consolas; font-size: 10px;")

        self.sync_btn = QPushButton("Синхронизировать (PREMIUM)")
        self.sync_btn.clicked.connect(self.start_sync)
        self.sync_btn.setEnabled(False)

        layout.addWidget(self.status_label)
        layout.addWidget(self.log_box)
        layout.addWidget(self.sync_btn)
        central.setLayout(layout)
        self.setCentralWidget(central)

        self.log("Запуск клиента...")

        # Запуск инициализации
        self.ensure_user_and_device()

    def ensure_user_and_device(self):
        try:
            init_db()
            self.log("БД инициализирована")

            db_gen = get_db()
            db = next(db_gen)

            # Пользователь
            user = db.query(User).first()
            if not user:
                user = User(username="local_user", email="local@example.com", hashed_password="***")
                db.add(user)
                db.commit()
                db.refresh(user)
                self.log("Создан локальный пользователь")

            self.user_id = user.id

            # Устройство
            device = db.query(Device).filter(Device.user_id == self.user_id).first()
            if not device:
                device = Device(
                    user_id=self.user_id,
                    device_name="Headset-Local",
                    device_type="headset",
                    device_id="LOCAL-001"
                )
                db.add(device)
                db.commit()
                self.log("Создано устройство")

            self.device_id = device.id
            db.close()

            # Запуск воркера
            self.start_worker()

            # Включаем кнопку
            self.sync_btn.setEnabled(True)
            self.status_label.setText("Сбор данных...")
            self.log("Готов к работе")

        except Exception as e:
            self.log(f"[ОШИБКА] {e}")
            QMessageBox.critical(self, "Ошибка", f"Не удалось запуститься:\n{e}")

    def start_worker(self):
        self.worker = DatabaseWorker(self.user_id, self.device_id)
        self.worker.data_collected.connect(self.update_status)
        self.worker.log_message.connect(self.log)
        self.worker.start()

        # Очистка раз в сутки
        from PyQt6.QtCore import QTimer
        cleanup_timer = QTimer(self)
        cleanup_timer.timeout.connect(cleanup_old_data)
        cleanup_timer.start(24 * 60 * 60 * 1000)

    def update_status(self, data):
        self.status_label.setText(f"HR: {data['hr']} | Stress: {data['stress']:.2f}")

    def start_sync(self):
        self.sync_btn.setEnabled(False)
        self.log("Синхронизация...")
        jwt = "YOUR_JWT_HERE"
        try:
            sync_to_cloud(jwt)
            self.log("Синхронизация завершена")
        except Exception as e:
            self.log(f"[SYNC ERROR] {e}")
        finally:
            self.sync_btn.setEnabled(True)

    def log(self, msg: str):
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_box.append(f"[{ts}] {msg}")
        self.log_box.ensureCursorVisible()

    def closeEvent(self, event):
        if self.worker:
            self.worker.stop()
            self.worker.wait()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = HealthClient()
    window.show()
    sys.exit(app.exec())