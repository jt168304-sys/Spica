# tts_service.py — Motor de Texto para Voz Nativo (Spica v16)
import threading
from kivy.utils import platform
from kivy.clock import Clock

try:
    from jnius import autoclass, PythonJavaClass, java_method
    from android.runnable import run_on_ui_thread
    PythonActivity = autoclass("org.kivy.android.PythonActivity")
    TextToSpeech = autoclass("android.speech.tts.TextToSpeech")
    Locale = autoclass("java.util.Locale")
    Bundle = autoclass("android.os.Bundle")
    HashMap = autoclass("java.util.HashMap")
    HAS_ANDROID = True
except Exception:
    HAS_ANDROID = False
    def run_on_ui_thread(func): return func

class TtsService:
    _instancia = None

    @classmethod
    def get_instance(cls):
        if cls._instancia is None:
            cls._instancia = cls()
        return cls._instancia

    def __init__(self):
        self.tts = None
        self._inicializado = False
        self._listener = None
        self._init_listener = None
        self._on_start_speak = None
        self._on_done_speak = None
        if platform == "android":
            self._inicializar_tts()

    @run_on_ui_thread
    def _inicializar_tts(self):
        from src.utils.service_log import slog
        slog("_inicializar_tts iniciado")

        class InitListener(PythonJavaClass):
            __javainterfaces__ = ['android/speech/tts/TextToSpeech$OnInitListener']
            __javacontext__ = 'app'

            def __init__(self, outer):
                super().__init__()
                self.outer = outer

            @java_method('(I)V')
            def onInit(self, status):
                slog(f"TTS onInit chamado, status={status}")
                if status == 0:
                    locale_br = Locale("pt", "BR")
                    result = self.outer.tts.setLanguage(locale_br)
                    if result < 0:
                        print("[Spica/TTS] PT-BR indisponível, tentando PT...")
                        locale_pt = Locale("pt")
                        self.outer.tts.setLanguage(locale_pt)
                    self.outer._inicializado = True
                    print("[Spica/TTS] Motor de voz ativo em pt-BR.")

        ctx = PythonActivity.mActivity
        self._init_listener = InitListener(self)
        self.tts = TextToSpeech(ctx, self._init_listener)

    def configurar_callbacks_visuais(self, on_start, on_done):
        """Vincula as funções da Bolha para alternar os avatares PNG."""
        self._on_start_speak = on_start
        self._on_done_speak = on_done

    def falar(self, texto, ao_terminar=None):
        from src.utils.service_log import slog
        slog(f"falar() chamado, _inicializado={self._inicializado}, platform={platform}")
        if not platform == "android" or not self._inicializado:
            print(f"[Spica/TTS - Fallback Desktop]: {texto}")
            slog("falar() abortou: platform != android OU _inicializado=False")
            if ao_terminar:
                try:
                    ao_terminar()
                except Exception:
                    pass
            return

        MAX_CHARS = 3000
        if len(texto) > MAX_CHARS:
            chunks = [texto[i:i+MAX_CHARS] for i in range(0, len(texto), MAX_CHARS)]
            print(f"[Spica/TTS] Texto dividido em {len(chunks)} chunks")
            for i, chunk in enumerate(chunks):
                eh_ultimo = (i == len(chunks) - 1)
                Clock.schedule_once(
                    lambda dt, c=chunk, ult=eh_ultimo: self._falar_chunk(c, ao_terminar if ult else None),
                    i * 0.1
                )
        else:
            self._falar_chunk(texto, ao_terminar)

    def _falar_chunk(self, texto, ao_terminar=None):
        """Fala um chunk de texto."""
        if not platform == "android" or not self._inicializado:
            if ao_terminar:
                try:
                    ao_terminar()
                except Exception:
                    pass
            return

        def _falar_async():
            from src.utils.service_log import slog
            try:
                utterance_id = f"spica_msg_{id(texto)}"
                params = HashMap()
                params.put("utteranceId", utterance_id)
                slog("Chamando tts.speak()...")
                self.tts.speak(texto, 0, params)
                slog("tts.speak() retornou sem lançar exceção")

                if self._on_start_speak:
                    try:
                        self._on_start_speak()
                    except Exception as e:
                        slog(f"EXCEÇÃO em _on_start_speak (ignorada, não impede a fala): {type(e).__name__}: {e}")

                import time
                tentativas = 0
                while not self.tts.isSpeaking() and tentativas < 20:
                    time.sleep(0.05)
                    tentativas += 1
                slog(f"isSpeaking() após espera inicial: {self.tts.isSpeaking()} (tentativas={tentativas})")

                while self.tts.isSpeaking():
                    time.sleep(0.1)
                slog("tts.isSpeaking() virou False — fala REALMENTE terminou agora")

                if self._on_done_speak:
                    try:
                        self._on_done_speak()
                    except Exception as e:
                        slog(f"EXCEÇÃO em _on_done_speak (ignorada): {type(e).__name__}: {e}")

                if ao_terminar:
                    try:
                        ao_terminar()
                    except Exception as e:
                        slog(f"EXCEÇÃO em ao_terminar (ignorada): {type(e).__name__}: {e}")
            except Exception as e:
                slog(f"EXCEÇÃO em _falar_async: {type(e).__name__}: {e}")
                print(f"[Spica/TTS] Erro ao sintetizar voz: {e}")
                if self._on_done_speak:
                    try:
                        self._on_done_speak()
                    except Exception:
                        pass
                if ao_terminar:
                    try:
                        ao_terminar()
                    except Exception:
                        pass

        threading.Thread(target=_falar_async, daemon=True).start()

    def parar(self):
        """Para a fala em andamento."""
        if HAS_ANDROID and self.tts:
            try:
                self.tts.stop()
                print("[Spica/TTS] Fala pausada")
            except Exception as e:
                print(f"[Spica/TTS] Erro ao parar: {e}")

    def destruir(self):
        """Libera recursos de TTS corretamente."""
        if HAS_ANDROID and self.tts:
            try:
                self.tts.stop()
                self.tts.shutdown()
                print("[Spica/TTS] Motor de voz destruído corretamente")
            except Exception as e:
                print(f"[Spica/TTS] Erro ao destruir TTS: {e}")
            finally:
                self.tts = None
                self._inicializado = False
                self._listener = None
                self._init_listener = None
                self._on_start_speak = None
                self._on_done_speak = None

    def __del__(self):
        try:
            self.destruir()
        except:
            pass
