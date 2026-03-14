import threading
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QObject
from extract import get_health_alerts

class SignalBridge(QObject):
    message_signal    = pyqtSignal(str, str, str)   # role, content, mode
    suggestion_signal = pyqtSignal(list)
    timeline_signal   = pyqtSignal(str, str, str)   # timestamp, action, status
    image_signal      = pyqtSignal(str)              # path to generated image
    stt_result_signal = pyqtSignal(str)              # transcribed text → input field
    stt_error_signal  = pyqtSignal(str)              # STT error message
    warning_signal    = pyqtSignal(str, str)         # message, severity (for Warnings page)

class HealthMonitor(QObject):
    alert_signal = pyqtSignal(str, str)             # message, severity

    def __init__(self, interval_ms: int = 30_000):
        super().__init__()
        self.interval = interval_ms
        self._timer: QTimer | None = None

    def start(self):
        self._timer = QTimer()
        self._timer.timeout.connect(self._check)
        self._timer.start(self.interval)

    def _check(self):
        def _run():
            alerts = get_health_alerts()
            for alert in alerts:
                self.alert_signal.emit(alert["message"], alert["severity"])

        threading.Thread(target=_run, daemon=True).start()