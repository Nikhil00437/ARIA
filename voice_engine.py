import re, threading, pyttsx3

class VoiceEngine:
    def __init__(self):
        self.engine = pyttsx3.init()
        self.engine.setProperty("rate", 180)
        self.engine.setProperty("volume", 0.9)
        voices = self.engine.getProperty("voices")
        if len(voices) > 1:
            self.engine.setProperty("voice", voices[1].id)

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
        clean = re.sub(r"<[^>]+>", "", clean)[:250]

        def _speak():
            self.engine.say(clean)
            self.engine.runAndWait()

        threading.Thread(target=_speak, daemon=True).start()
