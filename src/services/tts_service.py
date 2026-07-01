# tts_service.py — Motor de Texto para Voz Nativo (Spica v16)
import threading
from kivy.utils import platform
from kivy.clock import Clock

try:
    from jnius import autoclass, PythonJavaClass, java_method
    PythonActivity = autoclass("org.kivy.android.PythonActivity")
    TextToSpeech = autoclass("android.speech.tts.TextToSpeech")
    Locale = autoclass("java.util.Locale")
    Bundle = autoclass("android.os.Bundle")
    HAS_ANDROID = True
except Exception:
    HAS_ANDROID = False

class UtteranceProgressListenerImpl(PythonJavaClass if HAS_ANDROID else object):
    __javainterfaces__ = ['android/speech/tts/UtteranceProgressListener']
    __javacontext__ = 'app'

    def __init__(self, on_start_callback, on_done_callback):
        super().__init__()
        self.on_start = on_start_callback
        self.on_done = on_done_callback

    @java_method('(Ljava/lang/String;)V')
    def onStart(self, utteranceId):
        # Dispara o evento de abrir a boca na UI Thread
        if self.on_start:
            Clock.schedule_once(lambda dt: self.on_start(), 0)

    @java_method('(Ljava/lang/String;)V')
    def onDone(self, utteranceId):
        # Dispara o evento de fechar a boca na UI Thread
        if self.on_done:
            Clock.schedule_once(lambda dt: self.on_done(), 0)

    @java_method('(Ljava/lang/String;Z)V')
    def onError(self, utteranceId, sampleTimeOut):
        if self.on_done:
            Clock.schedule_once(lambda dt: self.on_done(), 0)

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
        self._listener = None  # ✅ NOVO: Rastrear listener para evitar GC prematuro
        self._on_start_speak = None
        self._on_done_speak = None
        if platform == "android":
            self._inicializar_tts()

    def _inicializar_tts(self):
        class InitListener(PythonJavaClass):
            __javainterfaces__ = ['android/speech/tts/TextToSpeech$OnInitListener']
            __javacontext__ = 'app'
            
            def __init__(self, outer):
                super().__init__()
                self.outer = outer

            @java_method('(I)V')
            def onInit(self, status):
                if status == 0: # TextToSpeech.SUCCESS
                    locale_br = Locale("pt", "BR")
                    result = self.outer.tts.setLanguage(locale_br)
                    if result < 0:
                        # ✅ NOVO: Fallback para português genérico
                        print("[Spica/TTS] PT-BR indisponível, tentando PT...")
                        locale_pt = Locale("pt")
                        self.outer.tts.setLanguage(locale_pt)
                    self.outer._inicializado = True
                    print("[Spica/TTS] Motor de voz ativo em pt-BR.")

        ctx = PythonActivity.mActivity
        self.tts = TextToSpeech(ctx, InitListener(self))

    def configurar_callbacks_visuais(self, on_start, on_done):
        """Vincula as funções da Bolha para alternar os avatares PNG."""
        self._on_start_speak = on_start
        self._on_done_speak = on_done
        if HAS_ANDROID and self.tts:
            # ✅ NOVO: Armazenar referência ao listener para evitar GC
            self._listener = UtteranceProgressListenerImpl(on_start, on_done)
            self.tts.setOnUtteranceProgressListener(self._listener)

    def falar(self, texto):
        if not platform == "android" or not self._inicializado:
            print(f"[Spica/TTS - Fallback Desktop]: {texto}")
            return

        # ✅ NOVO: Dividir texto longo em chunks (limite do Android TTS é ~4000 caracteres)
        MAX_CHARS = 3000
        if len(texto) > MAX_CHARS:
            chunks = [texto[i:i+MAX_CHARS] for i in range(0, len(texto), MAX_CHARS)]
            print(f"[Spica/TTS] Texto dividido em {len(chunks)} chunks")
            for i, chunk in enumerate(chunks):
                # Agendar com pequeno delay entre chunks
                Clock.schedule_once(
                    lambda dt, c=chunk: self._falar_chunk(c),
                    i * 0.1  # 100ms entre chunks
                )
        else:
            self._falar_chunk(texto)

    def _falar_chunk(self, texto):
        """Fala um chunk de texto."""
        if not platform == "android" or not self._inicializado:
            return

        # Roda a execução em uma Thread separada para não travar a bolha ou o chat
        def _falar_async():
            try:
                params = Bundle()
                # Define um ID único para a frase para ativar o monitor de progresso
                utterance_id = f"spica_msg_{id(texto)}"
                self.tts.speak(texto, 0, params, utterance_id) # 0 = TextToSpeech.QUEUE_FLUSH
            except Exception as e:
                print(f"[Spica/TTS] Erro ao sintetizar voz: {e}")
                if self._on_done_speak:
                    Clock.schedule_once(lambda dt: self._on_done_speak(), 0)

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
        """✅ NOVO: Libera recursos de TTS correctamente."""
        if HAS_ANDROID and self.tts:
            try:
                self.tts.stop()
                self.tts.shutdown()
                print("[Spica/TTS] Motor de voz destruído correctamente")
            except Exception as e:
                print(f"[Spica/TTS] Erro ao destruir TTS: {e}")
            finally:
                self.tts = None
                self._inicializado = False
                self._listener = None
                self._on_start_speak = None
                self._on_done_speak = None

    def __del__(self):
        """Destrutor para limpeza automática."""
        try:
            self.destruir()
        except:
            pass
