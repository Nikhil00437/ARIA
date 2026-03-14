import re, threading, queue, tempfile, os
import pyttsx3
# faster-whisper for STT
try:
    from faster_whisper import WhisperModel
    HAS_WHISPER = True
except ImportError:
    HAS_WHISPER = False
# sounddevice + soundfile for mic recording
try:
    import sounddevice as sd
    import soundfile as sf
    import numpy as np
    HAS_AUDIO = True
except ImportError:
    HAS_AUDIO = False


class VoiceEngine:
    # TTS
    def __init__(self):
        # TTS engine
        self._tts = pyttsx3.init()
        self._tts.setProperty("rate", 180)
        self._tts.setProperty("volume", 0.9)
        voices = self._tts.getProperty("voices")
        if len(voices) > 1:
            self._tts.setProperty("voice", voices[1].id)
        self._tts_lock = threading.Lock()

        # STT model (lazy-loaded on first use to keep startup fast)
        self._whisper = None
        self._whisper_lock = threading.Lock()

        # Recording state
        self._recording   = False
        self._rec_thread  = None
        self._audio_queue = queue.Queue()

    def speak(
        self,
        text: str,
        force: bool = False,
        mode: str = "chat",
        silent_mode: bool = False,
    ):
        if silent_mode and not force:
            speak_modes = {"error", "warning", "confirmation"}
            should_speak = mode in speak_modes or text.startswith(("❌", "⚠️", "✅"))
            if not should_speak:
                return

        clean = re.sub(r"[*`#_~]", "", text)
        clean = re.sub(r"<[^>]+>", "", clean)[:300]

        def _speak():
            with self._tts_lock:
                self._tts.say(clean)
                self._tts.runAndWait()

        threading.Thread(target=_speak, daemon=True).start()

    # STT
    def _load_whisper(self) -> bool:
        if not HAS_WHISPER:
            return False
        with self._whisper_lock:
            if self._whisper is None:
                try:
                    # "tiny" is fast on CPU; switch to "base" for better accuracy
                    self._whisper = WhisperModel("tiny", device="cpu", compute_type="int8")
                except Exception:
                    return False
        return True

    @property
    def stt_available(self) -> bool:
        return HAS_WHISPER and HAS_AUDIO

    def start_recording(self) -> bool:
        if not HAS_AUDIO:
            return False
        if self._recording:
            return True
        self._recording   = True
        self._audio_queue = queue.Queue()

        def _record():
            RATE   = 16_000
            CHUNK  = 1024
            frames = []

            def callback(indata, _frames, _time, _status):
                if self._recording:
                    frames.append(indata.copy())

            with sd.InputStream(samplerate=RATE, channels=1, dtype="float32",
                                blocksize=CHUNK, callback=callback):
                while self._recording:
                    sd.sleep(100)

            if frames:
                audio = np.concatenate(frames, axis=0)
                self._audio_queue.put((audio, RATE))

        self._rec_thread = threading.Thread(target=_record, daemon=True)
        self._rec_thread.start()
        return True

    def stop_recording_and_transcribe(self, on_result, on_error=None):
        self._recording = False
        if self._rec_thread:
            self._rec_thread.join(timeout=3)
            self._rec_thread = None

        def _transcribe():
            try:
                audio, rate = self._audio_queue.get(timeout=5)
            except queue.Empty:
                if on_error:
                    on_error("No audio captured.")
                return

            if not self._load_whisper():
                if on_error:
                    on_error("Whisper unavailable — run: pip install faster-whisper sounddevice soundfile numpy")
                return

            try:
                tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
                sf.write(tmp.name, audio, rate)
                tmp.close()

                segments, _info = self._whisper.transcribe(tmp.name, language="en")
                text = " ".join(s.text.strip() for s in segments).strip()
                os.unlink(tmp.name)

                if text:
                    on_result(text)
                else:
                    if on_error:
                        on_error("Nothing detected — try speaking louder.")
            except Exception as e:
                if on_error:
                    on_error(f"Transcription failed: {e}")

        threading.Thread(target=_transcribe, daemon=True).start()