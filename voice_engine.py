import threading
import numpy as np
from typing import Optional
try:
    import pyttsx3
    TTS_AVAILABLE = True
except ImportError: TTS_AVAILABLE = False
try:
    import sounddevice as sd
    import soundfile as sf
    STT_AVAILABLE = True
except ImportError: STT_AVAILABLE = False

# Try to import faster_whisper, but handle failure gracefully
try:
    from faster_whisper import WhisperModel
    WHISPER_AVAILABLE = True
except Exception as WHISPER_ERROR:
    WHISPER_AVAILABLE = False
    print(f"[Voice] Whisper not available: {WHISPER_ERROR}")

class VoiceEngine:
    def __init__(self, signals):
        self._signals    = signals
        self._tts_engine = None
        self._whisper    = None
        self._recording  = False
        self._tts_lock   = threading.Lock()
        self._silent_mode = False

        self._init_tts_async()

    def _init_tts_async(self):
        def _run():
            if not TTS_AVAILABLE: return
            try:
                engine = pyttsx3.init()
                engine.setProperty("rate", 175)
                engine.setProperty("volume", 0.9)
                voices = engine.getProperty("voices")
                for v in voices:
                    if "zira" in v.name.lower() or "female" in v.name.lower():
                        engine.setProperty("voice", v.id)
                        break
                self._tts_engine = engine
            except Exception as e:
                print(f"[TTS] Init failed: {e}")
                self._tts_engine = None
        t = threading.Thread(target=_run, daemon=True)
        t.start()

    def _ensure_whisper(self):
        if self._whisper is not None or not WHISPER_AVAILABLE: return
        try: self._whisper = WhisperModel("tiny", device="cpu", compute_type="int8")
        except Exception as e:
            print(f"[STT] Whisper load failed: {e}")
            self._whisper = None

    # TTS
    def set_silent_mode(self, enabled: bool): self._silent_mode = enabled

    def speak(self, text: str, force: bool = False):
        if not self._tts_engine: return
        if self._silent_mode and not force: return

        def _run():
            with self._tts_lock:
                try:
                    self._signals.tts_speaking.emit(True)
                    # Strip markdown
                    import re
                    clean = re.sub(r"[*_`#\[\]()]", "", text)
                    clean = re.sub(r"https?://\S+", "link", clean)
                    self._tts_engine.say(clean[:500])
                    self._tts_engine.runAndWait()
                except Exception as e: print(f"[TTS] Speak error: {e}")
                finally: self._signals.tts_speaking.emit(False)
        t = threading.Thread(target=_run, daemon=True)
        t.start()

    def stop_speaking(self):
        if self._tts_engine:
            try: self._tts_engine.stop()
            except Exception: pass
    # STT
    @property
    def stt_available(self) -> bool: return STT_AVAILABLE

    def record_and_transcribe(self, duration: int = 5, sample_rate: int = 16000):
        if not self.stt_available:
            self._signals.stt_error.emit("STT not available (faster-whisper not installed)")
            return
        self._ensure_whisper()
        if not self._whisper:
            self._signals.stt_error.emit("STT model failed to load")
            return
        def _run():
            try:
                self._signals.stt_started.emit()
                self._recording = True
                audio = sd.rec(
                    int(duration * sample_rate),
                    samplerate=sample_rate,
                    channels=1,
                    dtype="float32",
                )
                sd.wait()
                self._recording = False
                audio_np = audio.flatten()

                segments, _ = self._whisper.transcribe(audio_np, language="en")
                text = " ".join(s.text.strip() for s in segments).strip()

                if text: self._signals.stt_result.emit(text)
                else: self._signals.stt_error.emit("No speech detected.")
            except Exception as e:
                self._recording = False
                self._signals.stt_error.emit(f"STT Error: {e}")
        t = threading.Thread(target=_run, daemon=True)
        t.start()

    @property
    def is_recording(self) -> bool: return self._recording