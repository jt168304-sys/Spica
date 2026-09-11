# voice_service.py — Reconhecimento de voz
#
# Dois caminhos:
# 1) SpeechRecognizer (Google) — funciona com o app EM FOCO. No Android 12+
#    (e de forma dura no 14 / Motorola), o Google grava em OUTRO processo e
#    o sistema entrega SILENCIO quando a Spica nao esta visivel. O LED do
#    microfone acende, mas nao chega voz.
# 2) AudioRecord no nosso UID + Whisper (Groq) — o PCM e capturado no
#    processo da Spica, que herda o foregroundServiceType=microphone.
#    Esse e o unico caminho confiavel pra escuta continua fora do app.
import threading
import time
from kivy.clock import Clock
from src.utils.logger import WindLogger

try:
    from jnius import autoclass, PythonJavaClass, java_method
    from android.runnable import run_on_ui_thread
    PythonActivity = autoclass("org.kivy.android.PythonActivity")
    SpeechRecognizer = autoclass("android.speech.SpeechRecognizer")
    Intent = autoclass("android.content.Intent")
    RecognizerIntent = autoclass("android.speech.RecognizerIntent")
    AudioManager = autoclass("android.media.AudioManager")
    Context = autoclass("android.content.Context")
    HAS_ANDROID = True
except Exception:
    HAS_ANDROID = False
    def run_on_ui_thread(func):
        return func

if HAS_ANDROID:
    class _AudioFocusNoOp(PythonJavaClass):
        __javainterfaces__ = ['android/media/AudioManager$OnAudioFocusChangeListener']
        __javacontext__ = 'app'

        @java_method('(I)V')
        def onAudioFocusChange(self, focusChange):
            pass


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
        from src.utils.service_log import slog
        slog(f"onError chamado, codigo={error}")
        self.logger.error(f"[Spica/Voice] Erro no Reconhecedor Android cod: {error}")
        msg = "Nao ouvi" if error == 7 else f"Erro ao ouvir ({error})"
        self._entregar(msg)

    @java_method('(Landroid/os/Bundle;)V')
    def onResults(self, results):
        from src.utils.service_log import slog
        matches = results.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
        if matches and matches.size() > 0:
            texto = matches.get(0)
            slog(f"onResults capturou: {texto!r}")
            self._entregar(texto)
        else:
            slog("onResults sem matches, entregando 'Nao ouvi'")
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
        self._audio_focus_listener = None
        self._mic = None
        self._lock = threading.Lock()

    def ouvir(self, callback, usar_clock=True, captura_local=False):
        if not HAS_ANDROID:
            callback("Microfone indisponivel neste sistema.")
            return
        if captura_local or self._precisa_captura_local():
            threading.Thread(
                target=self._ouvir_local,
                args=(callback, usar_clock),
                daemon=True,
            ).start()
            return
        self._ouvir_android(callback, usar_clock)

    def _precisa_captura_local(self):
        try:
            from src.services.fg_service import estamos_no_servico
            return estamos_no_servico()
        except Exception:
            return False

    def _ouvir_local(self, callback, usar_clock=True):
        from src.utils.service_log import slog
        from src.services.mic_recorder import MicRecorder

        def entregar(texto):
            if usar_clock:
                Clock.schedule_once(lambda dt, t=texto: callback(t), 0)
            else:
                callback(texto)

        try:
            from src.services.fg_service import estamos_no_servico, iniciar_servico
            if not estamos_no_servico():
                iniciar_servico("escuta")
                time.sleep(0.4)
                from src.services.listen_ipc import pedir_escuta
                slog("pedindo captura ao FGS")
                texto_fgs = pedir_escuta()
                if texto_fgs is not None:
                    slog("FGS devolveu: %r" % texto_fgs[:80])
                    entregar(texto_fgs)
                    return
                slog("FGS nao respondeu, caindo no AudioRecord da Activity")

            with self._lock:
                if self._mic is not None:
                    try:
                        self._mic.cancelar()
                    except Exception:
                        pass
                self._mic = MicRecorder()
                mic = self._mic
            slog("captura local AudioRecord iniciada")
            wav = mic.capturar_utterance()
            if not wav:
                slog("captura local sem fala/audio")
                entregar("Nao ouvi")
                return
            texto = self._transcrever_whisper(wav)
            if texto:
                slog(f"whisper: {texto!r}")
                entregar(texto)
            else:
                slog("whisper vazio")
                entregar("Nao ouvi")
        except Exception as e:
            slog(f"EXCECAO captura local: {type(e).__name__}: {e}")
            entregar("Erro ao ouvir")

    def _transcrever_whisper(self, wav_path):
        from src.utils.service_log import slog
        from src.config.settings import Settings
        chave = Settings().get("api_key", "").strip()
        if not chave:
            slog("whisper: sem API key")
            return None
        try:
            import requests
            with open(wav_path, "rb") as f:
                resp = requests.post(
                    "https://api.groq.com/openai/v1/audio/transcriptions",
                    headers={"Authorization": f"Bearer {chave}"},
                    files={"file": ("audio.wav", f, "audio/wav")},
                    data={
                        "model": "whisper-large-v3-turbo",
                        "language": "pt",
                        "response_format": "json",
                    },
                    timeout=30,
                )
            if resp.status_code != 200:
                slog(f"whisper turbo HTTP {resp.status_code}, tentando whisper-large-v3")
                with open(wav_path, "rb") as f2:
                    resp = requests.post(
                        "https://api.groq.com/openai/v1/audio/transcriptions",
                        headers={"Authorization": f"Bearer {chave}"},
                        files={"file": ("audio.wav", f2, "audio/wav")},
                        data={
                            "model": "whisper-large-v3",
                            "language": "pt",
                            "response_format": "json",
                        },
                        timeout=30,
                    )
            if resp.status_code != 200:
                slog(f"whisper HTTP {resp.status_code}: {resp.text[:180]}")
                return None
            texto = (resp.json().get("text") or "").strip()
            if not texto or texto in (".", "...", "Musica", "Música"):
                return None
            return texto
        except Exception as e:
            slog(f"whisper falhou: {type(e).__name__}: {e}")
            return None

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

            context_atual = PythonActivity.mActivity
            self.recognizer = SpeechRecognizer.createSpeechRecognizer(context_atual)

            self._listener_persistente = RecognitionListenerImpl(callback, usar_clock)
            self.recognizer.setRecognitionListener(self._listener_persistente)

            intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH)
            intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
            intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE, "pt-BR")
            intent.putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, False)
            intent.putExtra("android.speech.extra.SPEECH_INPUT_COMPLETE_SILENCE_LENGTH_MILLIS", 2500)
            intent.putExtra("android.speech.extra.SPEECH_INPUT_POSSIBLY_COMPLETE_SILENCE_LENGTH_MILLIS", 1500)
            intent.putExtra("android.speech.extra.SPEECH_INPUT_MINIMUM_LENGTH_MILLIS", 1500)

            try:
                from src.utils.service_log import slog
                audio_manager = context_atual.getSystemService(Context.AUDIO_SERVICE)
                if self._audio_focus_listener is None:
                    self._audio_focus_listener = _AudioFocusNoOp()
                try:
                    audio_manager.abandonAudioFocus(self._audio_focus_listener)
                except Exception:
                    pass
                resultado_foco = audio_manager.requestAudioFocus(
                    self._audio_focus_listener,
                    AudioManager.STREAM_MUSIC,
                    AudioManager.AUDIOFOCUS_GAIN_TRANSIENT
                )
                slog(f"requestAudioFocus() retornou: {resultado_foco} (1=concedido, 0=falhou, 2=adiado)")
            except Exception as e:
                slog(f"Falha ao solicitar foco de audio (seguindo sem isso): {type(e).__name__}: {e}")

            self.recognizer.startListening(intent)
            self.logger.info("[Spica/Voice] Hardware de audio ativado com sucesso na UI Thread.")
        except Exception as e:
            self.logger.error(f"[Spica/Voice] Falha critica ao instanciar microfone: {e}")
            if usar_clock:
                Clock.schedule_once(lambda dt: callback("Erro ao inicializar hardware de voz."), 0)
            else:
                callback("Erro ao inicializar hardware de voz.")

    def destruir(self):
        try:
            if self._mic is not None:
                try:
                    self._mic.cancelar()
                except Exception:
                    pass
                self._mic = None
            if self.recognizer:
                try:
                    self.recognizer.stopListening()
                except Exception:
                    pass
                try:
                    self.recognizer.destroy()
                except Exception:
                    pass
                self.recognizer = None

            self._listener_persistente = None
            self.logger.info("[Spica/Voice] Reconhecedor de voz destruido")
        except Exception as e:
            self.logger.error(f"[Spica/Voice] Erro ao destruir: {e}")

    def __del__(self):
        try:
            self.destruir()
        except Exception:
            pass
