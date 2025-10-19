import sys
import asyncio
from datetime import datetime
import sqlite3
import requests
import onnxruntime as ort
from bleak import BleakClient
from PyQt6.QtWidgets import QApplication, QMainWindow, QLabel, QPushButton, QVBoxLayout, QWidget
from PyQt6.QtCore import QTimer
from plyer import notification


class HealthMonitorApp(QMainWindow):
    """Main application window for Health Monitor using PyQt6"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Health Monitor")
        self.setGeometry(100, 100, 400, 300)

        # Initialize components
        self.setup_local_ml()
        self.setup_local_db()
        self.api_client = APIClient("http://localhost:8000")
        self.is_premium = False
        self.user_id = None
        self.ble_client = None

        # UI setup
        self.setup_ui()

        # Timer for periodic sensor reading
        self.timer = QTimer()
        self.timer.timeout.connect(self.read_sensors)
        self.timer.start(2000)  # Every 2 seconds

    def setup_local_ml(self):
        """Initialize ONNX model for local inference"""
        try:
            self.ml_session = ort.InferenceSession("models/stress_model.onnx")
        except Exception as e:
            self.show_notification("ML Error", f"Failed to load ONNX model: {e}")
            raise

    def setup_local_db(self):
        """Initialize local SQLite database"""
        self.conn = sqlite3.connect("health_data.db")
        self.cursor = self.conn.cursor()
        self.cursor.execute("""
                            CREATE TABLE IF NOT EXISTS local_vectors
                            (
                                id
                                INTEGER
                                PRIMARY
                                KEY
                                AUTOINCREMENT,
                                timestamp
                                TEXT
                                NOT
                                NULL,
                                heart_rate
                                INTEGER,
                                stress_level
                                REAL,
                                model_version
                                TEXT
                                DEFAULT
                                'v1.0'
                            )
                            """)
        self.conn.commit()

    def setup_ui(self):
        """Set up PyQt6 UI"""
        layout = QVBoxLayout()
        self.status_label = QLabel("Status: Free User")
        self.sync_button = QPushButton("Sync Data (Premium)")
        self.sync_button.clicked.connect(self.sync_data)
        self.sync_button.setEnabled(False)  # Disabled until premium status confirmed
        self.auth_button = QPushButton("Login")
        self.auth_button.clicked.connect(self.authenticate)

        layout.addWidget(self.status_label)
        layout.addWidget(self.sync_button)
        layout.addWidget(self.auth_button)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    async def connect_ble(self):
        """Connect to BLE device (example)"""
        try:
            async with BleakClient("00:11:22:33:44:55") as client:  # Replace with actual BLE address
                self.ble_client = client
                # Example: Read heart rate characteristic (replace UUID)
                heart_rate = await client.read_gatt_char("00002a37-0000-1000-8000-00805f9b34fb")
                return int.from_bytes(heart_rate, "little")
        except Exception as e:
            self.show_notification("BLE Error", f"Failed to connect: {e}")
            return None

    def read_sensors(self):
        """Read sensor data and predict stress level"""
        # Run BLE connection in async context
        loop = asyncio.get_event_loop()
        heart_rate = loop.run_until_complete(self.connect_ble()) or 75  # Fallback value
        sensor_data = {"heart_rate": heart_rate}

        stress_level = self.predict_stress(sensor_data)
        self.cursor.execute(
            "INSERT INTO local_vectors (timestamp, heart_rate, stress_level) VALUES (?, ?, ?)",
            (datetime.utcnow().isoformat(), sensor_data["heart_rate"], stress_level)
        )
        self.conn.commit()
        self.status_label.setText(f"Stress: {stress_level:.2f}")

    def predict_stress(self, sensor_data):
        """Perform local inference with ONNX model"""
        try:
            inputs = {self.ml_session.get_inputs()[0].name: [[sensor_data["heart_rate"]]]}
            result = self.ml_session.run(None, inputs)[0][0][0]
            return result
        except Exception as e:
            self.show_notification("Inference Error", f"Prediction failed: {e}")
            return 0.0

    def authenticate(self):
        """Authenticate user with FastAPI server (placeholder)"""
        try:
            # Example: POST /auth/login with dummy credentials
            response = self.api_client.login({"username": "testuser", "password": "testpass"})
            if response.status_code == 200:
                data = response.json()
                self.user_id = data.get("user_id")
                self.is_premium = data.get("user_type") == "premium"
                self.sync_button.setEnabled(self.is_premium)
                self.status_label.setText(f"Logged in as {'Premium' if self.is_premium else 'Free'} User")
                self.show_notification("Login Success", "Authentication successful")
            else:
                self.show_notification("Login Failed", "Invalid credentials")
        except Exception as e:
            self.show_notification("Login Error", f"Authentication failed: {e}")

    def sync_data(self):
        """Sync local data with server (Premium only)"""
        if not self.is_premium:
            self.show_notification("Sync Error", "Sync requires Premium account")
            self.status_label.setText("Sync requires Premium")
            return
        try:
            vectors = self.cursor.execute("SELECT * FROM local_vectors").fetchall()
            vector_data = [
                {"timestamp": v[1], "heart_rate": v[2], "stress_level": v[3], "model_version": v[4]}
                for v in vectors
            ]
            response = self.api_client.sync_vectors(self.user_id, vector_data)
            if response.status_code == 200:
                self.cursor.execute("DELETE FROM local_vectors")
                self.conn.commit()
                self.status_label.setText("Sync successful")
                self.show_notification("Sync Success", "Data synced with server")
            else:
                self.show_notification("Sync Error", f"Sync failed: {response.text}")
        except Exception as e:
            self.show_notification("Sync Error", f"Sync failed: {e}")

    def show_notification(self, title, message):
        """Show desktop notification using plyer"""
        notification.notify(title=title, message=message, timeout=5)

    def closeEvent(self, event):
        """Clean up on window close"""
        self.conn.close()
        event.accept()


class APIClient:
    """HTTP client for FastAPI server"""

    def __init__(self, base_url):
        self.base_url = base_url
        self.session = requests.Session()

    def login(self, credentials):
        return self.session.post(f"{self.base_url}/auth/login", json=credentials)

    def sync_vectors(self, user_id, vectors):
        return self.session.post(f"{self.base_url}/sync/{user_id}/vectors", json=vectors)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = HealthMonitorApp()
    window.show()
    sys.exit(app.exec())