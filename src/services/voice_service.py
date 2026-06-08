# voice_service.py — Reconhecimento de voz (STT) via SpeechRecognition
import threading
from typing import Optional, Callable
from src.utils.logger import WindLogger


class VoiceService:
    _instancia: Optional["VoiceService"] = None

    @classmethod
    def get_instance(cls):
        if cls._instancia is None:
            cls._instancia = cls()
        return cls._instancia

    def __init__(self):
        self.logger = WindLogger()
        self._ouvindo = False
        self._sr = None
        try:
            import speech_recognition as sr
            self._sr = sr
            self._rec = sr.Recognizer()
            self._rec.pause_threshold = 0.8
        except ImportError:
            self.logger.warning("SpeechRecognition nao instalado.")

    def ouvir(self, callback: Optional[Callable[[str], None]] = None):
        """Inicia reconhecimento de voz em thread separada."""
        if not self._sr:
            if callback:
                from kivy.clock import Clock
                Clock.schedule_once(lambda dt: callback("Modulo de voz nao instalado."), 0)
            return
        if self._ouvindo:
            return
        threading.Thread(target=self._ouvir_sync, args=(callback,), daemon=True).start()

    def _ouvir_sync(self, callback):
        self._ouvindo = True
        try:
            sr = self._sr
            with sr.Microphone() as mic:
                self._rec.adjust_for_ambient_noise(mic, duration=0.5)
                audio = self._rec.listen(mic, timeout=5, phrase_time_limit=10)
            texto = self._rec.recognize_google(audio, language="pt-BR")
            self._retornar(callback, texto)
        except sr.WaitTimeoutError:
            self._retornar(callback, "Nao ouvi nada. Tente novamente.")
        except sr.UnknownValueError:
            self._retornar(callback, "Nao entendi. Pode repetir?")
        except sr.RequestError:
            self._retornar(callback, "Sem conexao para reconhecimento de voz.")
        except Exception as e:
            self.logger.error(f"Erro no reconhecimento: {e}")
            self._retornar(callback, "Erro no reconhecimento de voz.")
        finally:
            self._ouvindo = False
            self._parar_pulso()

    def _retornar(self, callback, texto):
        if callback:
            from kivy.clock import Clock
            Clock.schedule_once(lambda dt: callback(texto), 0)

    def _parar_pulso(self):
        try:
            from kivymd.app import MDApp
            from kivy.clock import Clock
            app = MDApp.get_running_app()
            if hasattr(app, "bubble") and app.bubble is not None:
                Clock.schedule_once(lambda dt: app.bubble.parar_pulsar(), 0)
        except Exception:
            pass
