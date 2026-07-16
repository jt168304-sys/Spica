# voice_service.py — Servico de Reconhecimento de Voz Nativo Android (v16 Estável)
import threading
from kivy.clock import Clock
from src.utils.logger import WindLogger

try:
    from jnius import autoclass, PythonJavaClass, java_method
    from android.runnable import run_on_ui_thread
    PythonActivity = autoclass("org.kivy.android.PythonActivity")
    SpeechRecognizer = autoclass("android.speech.SpeechRecognizer")
    Intent = autoclass("android.content.Intent")
    RecognizerIntent = autoclass("android.speech.RecognizerIntent")
    context = PythonActivity.mActivity
    HAS_ANDROID = True
except Exception:
    HAS_ANDROID = False
    def run_on_ui_thread(func):
        return func

class RecognitionListenerImpl(PythonJavaClass if HAS_ANDROID else object):
    __javainterfaces__ = ['android/speech/RecognitionListener']
    __javacontext__ = 'app'

    def __init__(self, callback, usar_clock=True):
        super().__init__()
        self.callback = callback
        self.usar_clock = usar_clock
        self.logger = WindLogger()

    def _entregar(self, texto):
        if self.usar_clock:
            Clock.schedule_once(lambda dt: self.callback(texto), 0)
        else:
            self.callback(texto)

    @java_method('(Landroid/os/Bundle;)V')
    def onReadyForSpeech(self, params):
        self.logger.info("[Spica/Voice] Microfone pronto e ouvindo nativamente...")

    @java_method('()V')
    def onBeginningOfSpeech(self): pass

    @java_method('(F)V')
    def onRmsChanged(self, rmsdB): pass

    @java_method('([B)V')
    def onBufferReceived(self, buffer): pass

    @java_method('()V')
    def onEndOfSpeech(self): pass

    @java_method('(I)V')
    def onError(self, error):
        self.logger.error(f"[Spica/Voice] Erro no Reconhecedor Android cod: {error}")
        msg = "Nao ouvi" if error == 7 else f"Erro ao ouvir ({error})"
        self._entregar(msg)

    @java_method('(Landroid/os/Bundle;)V')
    def onResults(self, results):
        matches = results.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
        if matches and matches.size() > 0:
            texto = matches.get(0)
            self._entregar(texto)
        else:
            self._entregar("Nao ouvi")

    @java_method('(Landroid/os/Bundle;)V')
    def onPartialResults(self, partialResults): pass

    @java_method('(ILandroid/os/Bundle;)V')
    def onEvent(self, eventType, params): pass

class VoiceService:
    _instancia = None

    @classmethod
    def get_instance(cls):
        if cls._instancia is None:
            cls._instancia = cls()
        return cls._instancia

    def __init__(self):
        self.logger = WindLogger()
        self.recognizer = None
        self._listener_persistente = None

    def ouvir(self, callback, usar_clock=True):
        if not HAS_ANDROID:
            callback("Microfone indisponivel neste sistema.")
            return
        self._ouvir_android(callback, usar_clock)

    @run_on_ui_thread
    def _ouvir_android(self, callback, usar_clock=True):
        try:
            if self.recognizer is not None:
                try:
                    self.recognizer.stopListening()
                    self.recognizer.destroy()
                except Exception:
                    pass
                self.recognizer = None

            self.recognizer = SpeechRecognizer.createSpeechRecognizer(context)

            self._listener_persistente = RecognitionListenerImpl(callback, usar_clock)
            self.recognizer.setRecognitionListener(self._listener_persistente)

            intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH)
            intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
            intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE, "pt-BR")
            intent.putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, False)
            # Define quanto tempo de silencio o reconhecedor espera antes de
            # considerar que a pessoa terminou de falar (essas chaves nao tem
            # constante oficial na classe RecognizerIntent, mas sao aceitas
            # pelo reconhecedor padrao do Google).
            intent.putExtra("android.speech.extra.SPEECH_INPUT_COMPLETE_SILENCE_LENGTH_MILLIS", 2500)
            intent.putExtra("android.speech.extra.SPEECH_INPUT_POSSIBLY_COMPLETE_SILENCE_LENGTH_MILLIS", 1500)
            intent.putExtra("android.speech.extra.SPEECH_INPUT_MINIMUM_LENGTH_MILLIS", 1500)

            self.recognizer.startListening(intent)
            self.logger.info("[Spica/Voice] Hardware de áudio ativado com sucesso na UI Thread.")
        except Exception as e:
            self.logger.error(f"[Spica/Voice] Falha crítica ao instanciar microfone: {e}")
            if usar_clock:
                Clock.schedule_once(lambda dt: callback("Erro ao inicializar hardware de voz."), 0)
            else:
                callback("Erro ao inicializar hardware de voz.")

    def destruir(self):
        try:
            if self.recognizer:
                try:
                    self.recognizer.stopListening()
                except:
                    pass
                try:
                    self.recognizer.destroy()
                except:
                    pass
                self.recognizer = None

            self._listener_persistente = None
            self.logger.info("[Spica/Voice] Reconhecedor de voz destruído")
        except Exception as e:
            self.logger.error(f"[Spica/Voice] Erro ao destruir: {e}")

    def __del__(self):
        try:
            self.destruir()
        except:
            pass
