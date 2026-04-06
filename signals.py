import psutil
from PyQt5.QtCore import QObject, pyqtSignal, QTimer
from constants import HEALTH_CHECK_INTERVAL_MS, HEALTH_RAM_THRESHOLD_MB

class ARIASignals(QObject):
    # Chat
    chat_response      = pyqtSignal(str, str)   # (role, text)
    chat_stream_chunk  = pyqtSignal(str)
    chat_stream_done   = pyqtSignal()
    # Status
    status_update      = pyqtSignal(str)
    typing_indicator   = pyqtSignal(bool)
    # Terminal
    terminal_output    = pyqtSignal(str, bool)  # (text, is_error)
    # Timeline
    timeline_event     = pyqtSignal(str, str)   # (action, detail)
    # Warnings
    warning_added      = pyqtSignal(str, str)   # (severity, message)
    warning_count      = pyqtSignal(int)
    # Voice / STT
    stt_started        = pyqtSignal()
    stt_result         = pyqtSignal(str)
    stt_error          = pyqtSignal(str)
    tts_speaking       = pyqtSignal(bool)
    # Patterns
    pattern_suggested  = pyqtSignal(str, str)   # (pattern_name, original_input)
    # Self-Mod
    selfmod_proposal   = pyqtSignal(list)        # list of proposal dicts
    selfmod_applied    = pyqtSignal(str, object) # (param_key, new_value)
    selfmod_rolled_back= pyqtSignal(str)         # ledger entry id
    # Theme
    theme_changed      = pyqtSignal(str)
    # Confirmation flow
    confirm_request    = pyqtSignal(str, str)   # (cmd, display_text)
    # Session
    session_loaded     = pyqtSignal(str)        # session_id

class HealthMonitor(QObject):
    def __init__(self, signals: ARIASignals, parent=None):
        super().__init__(parent)
        self._signals = signals
        self._timer = QTimer(self)
        self._timer.setInterval(HEALTH_CHECK_INTERVAL_MS)
        self._timer.timeout.connect(self._check)

    def start(self): self._timer.start()

    def stop(self): self._timer.stop()

    def _check(self):
        try:
            alerts = []
            for proc in psutil.process_iter(["name", "memory_info"]):
                try:
                    mb = proc.info["memory_info"].rss / (1024 * 1024)
                    if mb > HEALTH_RAM_THRESHOLD_MB: alerts.append((proc.info["name"], mb))
                except (psutil.NoSuchProcess, psutil.AccessDenied): continue
            if alerts:
                alerts.sort(key=lambda x: x[1], reverse=True)
                for name, mb in alerts[:3]:
                    msg = f"{name} is consuming {mb:.0f} MB RAM"
                    self._signals.warning_added.emit("warning", msg)
            # CPU spike
            cpu = psutil.cpu_percent(interval=1)
            if cpu > 90: self._signals.warning_added.emit("error", f"CPU usage critical: {cpu:.0f}%")
            elif cpu > 75: self._signals.warning_added.emit("warning", f"CPU usage high: {cpu:.0f}%")
        except Exception as e: self._signals.warning_added.emit("info", f"Health check error: {e}")