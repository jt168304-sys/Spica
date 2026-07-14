# overlay.py — Controlador de Janela Flutuante e Máquina de Estados (v16 Estável)
import os
import time
from kivy.utils import platform
from kivy.clock import Clock

try:
    from jnius import autoclass, PythonJavaClass, java_method
    from android.runnable import run_on_ui_thread
    Context = autoclass('android.content.Context')
    WindowManager = autoclass('android.view.WindowManager')
    LayoutParams = autoclass('android.view.WindowManager$LayoutParams')
    ImageView = autoclass('android.widget.ImageView')
    BitmapFactory = autoclass('android.graphics.BitmapFactory')
    PixelFormat = autoclass('android.graphics.PixelFormat')
    PythonActivity = autoclass("org.kivy.android.PythonActivity")
    AndroidSettings = autoclass('android.provider.Settings')
    Uri = autoclass('android.net.Uri')
    Intent = autoclass('android.content.Intent')
    MotionEvent = autoclass('android.view.MotionEvent')
    LinearLayout = autoclass('android.widget.LinearLayout')
    TextView = autoclass('android.widget.TextView')
    Color = autoclass('android.graphics.Color')
    JString = autoclass('java.lang.String')
    HAS_ANDROID = True
except Exception:
    HAS_ANDROID = False
    def run_on_ui_thread(func): return func


def tem_permissao_overlay():
    """Verifica se a permissão 'Exibir sobre outros apps' foi concedida."""
    if not HAS_ANDROID:
        return False
    try:
        ctx = PythonActivity.mActivity
        return bool(AndroidSettings.canDrawOverlays(ctx))
    except Exception as e:
        print(f"[Spica/Overlay] Erro ao checar permissão de overlay: {e}")
        return False


def pedir_permissao_overlay():
    """Abre a tela do Android onde o usuário libera 'Exibir sobre outros apps'."""
    if not HAS_ANDROID:
        return
    try:
        ctx = PythonActivity.mActivity
        intent = Intent(
            AndroidSettings.ACTION_MANAGE_OVERLAY_PERMISSION,
            Uri.parse(f"package:{ctx.getPackageName()}")
        )
        ctx.startActivity(intent)
        print("[Spica/Overlay] Tela de permissão de overlay aberta. Ative e volte ao app.")
    except Exception as e:
        print(f"[Spica/Overlay] Erro ao abrir tela de permissão de overlay: {e}")

class SpicaOverlay:
    def __init__(self):
        self.window_manager = None
        self.image_view = None
        self.params = None
        self.iniciado = False
        self._bitmap_atual = None
        self._touch_listener = None
        self.mutado = False
        self.escuta_continua = False

        self._menu_view = None
        self._click_listeners = []

        self.app_dir = os.environ.get('ANDROID_APP_PATH', os.path.dirname(os.path.abspath(__file__)))
        base_dir = os.path.dirname(os.path.dirname(self.app_dir)) if "src" in self.app_dir else self.app_dir

        self.path_boca_fechada = os.path.join(base_dir, "assets", "boca_fechada.png")
        self.path_boca_aberta = os.path.join(base_dir, "assets", "boca_aberta.png")

    @run_on_ui_thread
    def ligar_bolha(self):
        if not HAS_ANDROID or self.iniciado: return

        ctx = PythonActivity.mActivity
        self.window_manager = ctx.getSystemService(Context.WINDOW_SERVICE)
        self.image_view = ImageView(ctx)

        self.definir_avatar_png(falar=False)

        window_type = 2038
        flags = LayoutParams.FLAG_NOT_FOCUSABLE | LayoutParams.FLAG_LAYOUT_IN_SCREEN

        self.params = LayoutParams(
            220, 220,
            window_type, flags, PixelFormat.TRANSLUCENT
        )
        self.params.gravity = 51
        self.params.x = 150
        self.params.y = 150

        self.window_manager.addView(self.image_view, self.params)
        self.iniciado = True

        from src.services.tts_service import TtsService
        TtsService.get_instance().configurar_callbacks_visuais(
            on_start=lambda: self.definir_avatar_png(falar=True),
            on_done=lambda: self.definir_avatar_png(falar=False)
        )

        self._configurar_toque_na_bolha()

        print("[Spica/Overlay] Bolha injetada no sistema e sincronizada ao TTS!")

    def _configurar_toque_na_bolha(self):
        """Permite arrastar a bolha pela tela e tocar rápido para abrir o menu."""
        if not HAS_ANDROID or not self.image_view:
            return

        overlay_ref = self

        class TouchListener(PythonJavaClass):
            __javainterfaces__ = ['android/view/View$OnTouchListener']
            __javacontext__ = 'app'

            def __init__(self):
                super().__init__()
                self.initial_x = 0
                self.initial_y = 0
                self.initial_touch_x = 0
                self.initial_touch_y = 0
                self.start_time = 0
                self.moveu = False

            @java_method('(Landroid/view/View;Landroid/view/MotionEvent;)Z')
            def onTouch(self, view, event):
                action = event.getAction()
                if action == MotionEvent.ACTION_DOWN:
                    self.initial_x = overlay_ref.params.x
                    self.initial_y = overlay_ref.params.y
                    self.initial_touch_x = event.getRawX()
                    self.initial_touch_y = event.getRawY()
                    self.start_time = time.time()
                    self.moveu = False
                    return True
                elif action == MotionEvent.ACTION_MOVE:
                    dx = event.getRawX() - self.initial_touch_x
                    dy = event.getRawY() - self.initial_touch_y
                    if abs(dx) > 25 or abs(dy) > 25:
                        self.moveu = True
                    overlay_ref.params.x = int(self.initial_x + dx)
                    overlay_ref.params.y = int(self.initial_y + dy)
                    try:
                        overlay_ref.window_manager.updateViewLayout(overlay_ref.image_view, overlay_ref.params)
                    except Exception as e:
                        print(f"[Spica/Overlay] Erro ao mover bolha: {e}")
                    return True
                elif action == MotionEvent.ACTION_UP:
                    duracao = time.time() - self.start_time
                    if not self.moveu and duracao < 0.6:
                        overlay_ref._alternar_menu_bolha()
                    return True
                return False

        self._touch_listener = TouchListener()
        self.image_view.setOnTouchListener(self._touch_listener)

    def _alternar_menu_bolha(self):
        """Abre o menu se estiver fechado, ou fecha se já estiver aberto."""
        if self._menu_view is not None:
            self._fechar_menu_bolha()
        else:
            self._mostrar_menu_bolha()

    @run_on_ui_thread
    def _mostrar_menu_bolha(self):
        """Mostra um mini-menu (janela de overlay própria) com opções: falar, mutar, fechar."""
        if not HAS_ANDROID or not self.image_view or self._menu_view is not None:
            return

        overlay_ref = self

        try:
            ctx = PythonActivity.mActivity
            container = LinearLayout(ctx)
            container.setOrientation(LinearLayout.VERTICAL)
            container.setBackgroundColor(Color.parseColor("#EE222222"))
            container.setPadding(12, 12, 12, 12)

            texto_escuta = "🔇 Desativar escuta" if self.escuta_continua else "🎤 Ativar escuta"
            opcoes = [
                (texto_escuta, "escuta"),
                ("✖ Fechar bolha", "fechar"),
            ]

            self._click_listeners = []
            for texto, acao in opcoes:
                tv = TextView(ctx)
                tv.setText(JString(texto))
                tv.setTextColor(Color.WHITE)
                tv.setTextSize(15)
                tv.setPadding(28, 18, 28, 18)

                class ClickListener(PythonJavaClass):
                    __javainterfaces__ = ['android/view/View$OnClickListener']
                    __javacontext__ = 'app'

                    def __init__(self, acao):
                        super().__init__()
                        self.acao = acao

                    @java_method('(Landroid/view/View;)V')
                    def onClick(self, view):
                        overlay_ref._fechar_menu_bolha()
                        if self.acao == "escuta":
                            overlay_ref._alternar_escuta_continua()
                        elif self.acao == "fechar":
                            overlay_ref.desligar_bolha()

                listener = ClickListener(acao)
                self._click_listeners.append(listener)
                tv.setOnClickListener(listener)
                container.addView(tv)

            menu_params = LayoutParams(
                LayoutParams.WRAP_CONTENT, LayoutParams.WRAP_CONTENT,
                2038, LayoutParams.FLAG_NOT_FOCUSABLE, PixelFormat.TRANSLUCENT
            )
            menu_params.gravity = 51
            menu_params.x = self.params.x
            menu_params.y = self.params.y + 230

            self.window_manager.addView(container, menu_params)
            self._menu_view = container
            print("[Spica/Overlay] Menu da bolha aberto.")
        except Exception as e:
            print(f"[Spica/Overlay] Erro ao abrir menu da bolha: {e}")

    @run_on_ui_thread
    def _fechar_menu_bolha(self):
        if self._menu_view is not None and self.window_manager is not None:
            try:
                self.window_manager.removeView(self._menu_view)
            except Exception as e:
                print(f"[Spica/Overlay] Erro ao fechar menu da bolha: {e}")
            finally:
                self._menu_view = None
                self._click_listeners = []

    def _alternar_escuta_continua(self):
        """Liga/desliga o modo de escuta continua (toggle unico de mutar/desmutar)."""
        self.escuta_continua = not self.escuta_continua
        self.mutado = not self.escuta_continua
        estado = "ativada" if self.escuta_continua else "desativada"
        print(f"[Spica/Overlay] Escuta continua {estado}.")
        if self.escuta_continua:
            self._ciclo_escuta_continua()

    def _ciclo_escuta_continua(self):
        """Escuta uma fala. Ao terminar de processar e responder, chama a si mesmo de novo."""
        if not self.escuta_continua:
            return
        try:
            from src.services.voice_service import VoiceService
            VoiceService.get_instance().ouvir(self._processar_escuta_continua, usar_clock=False)
        except Exception as e:
            print(f"[Spica/Overlay] Erro no ciclo de escuta continua: {e}")

    def _processar_escuta_continua(self, texto_capturado):
        """Recebe o texto reconhecido, manda pra IA (com o tom de conversa continua) e fala a resposta."""
        if not self.escuta_continua:
            return
        try:
            from src.services.groq_service import GroqService
            from src.services.tts_service import TtsService

            invalido = (not texto_capturado) or texto_capturado.startswith("Nao ouvi") or texto_capturado.startswith("Erro ao ouvir")
            if invalido:
                self._ciclo_escuta_continua()
                return

            def processar_resposta_ia(texto_resposta):
                TtsService.get_instance().falar(texto_resposta, on_finish=self._ciclo_escuta_continua)

            GroqService.get_instance().perguntar(
                texto_capturado, processar_resposta_ia,
                usar_clock=False, modo_continuo=True
            )
        except Exception as e:
            print(f"[Spica/Overlay] Erro ao processar escuta continua: {e}")
            self._ciclo_escuta_continua()

    @run_on_ui_thread
    def definir_avatar_png(self, falar=False):
        """Muda o Bitmap do ImageView do Android com limpeza correta de memória."""
        if not HAS_ANDROID or not self.image_view:
            return

        if self._bitmap_atual:
            try:
                self._bitmap_atual.recycle()
                self._bitmap_atual = None
            except:
                pass

        caminho = self.path_boca_aberta if falar else self.path_boca_fechada
        if os.path.exists(caminho):
            try:
                self._bitmap_atual = BitmapFactory.decodeFile(caminho)
                self.image_view.setImageBitmap(self._bitmap_atual)
            except Exception as e:
                print(f"[Spica/Overlay] Falha ao renderizar PNG: {e}")
                self._bitmap_atual = None

    @run_on_ui_thread
    def desligar_bolha(self):
        self.escuta_continua = False
        if HAS_ANDROID and self.window_manager and self.image_view and self.iniciado:
            try:
                self._fechar_menu_bolha()

                if self._bitmap_atual:
                    try:
                        self._bitmap_atual.recycle()
                    except:
                        pass
                    self._bitmap_atual = None

                self.window_manager.removeView(self.image_view)
                self.image_view = None
                self.iniciado = False
                print("[Spica/Overlay] Overlay removido e memória liberada corretamente")
            except Exception as e:
                print(f"[Spica/Overlay] Erro ao remover overlay: {e}")

    def destruir(self):
        """Destrói completamente o overlay."""
        self.desligar_bolha()
# Teste forcado pelo terminal
