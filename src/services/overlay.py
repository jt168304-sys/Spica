# overlay.py — Controlador de Janela Flutuante e Máquina de Estados (v16 Estável)
import os
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
    HAS_ANDROID = True
except Exception:
    HAS_ANDROID = False
    def run_on_ui_thread(func): return func

class SpicaOverlay:
    def __init__(self):
        self.window_manager = None
        self.image_view = None
        self.params = None
        self.iniciado = False
        self._bitmap_atual = None  # ✅ NOVO: Rastrear bitmap atual para limpeza
        
        # Mapeamento do caminho seguro dos assets empacotados pelo Buildozer
        self.app_dir = os.environ.get('ANDROID_APP_PATH', os.path.dirname(os.path.abspath(__file__)))
        # Sobe o nível correto para buscar os PNGs na pasta assets da raiz
        base_dir = os.path.dirname(os.path.dirname(self.app_dir)) if "src" in self.app_dir else self.app_dir
        
        self.path_boca_fechada = os.path.join(base_dir, "assets", "boca_fechada.png")
        self.path_boca_aberta = os.path.join(base_dir, "assets", "boca_aberta.png")

    @run_on_ui_thread
    def ligar_bolha(self):
        if not HAS_ANDROID or self.iniciado: return
        
        ctx = PythonActivity.mActivity
        self.window_manager = ctx.getSystemService(Context.WINDOW_SERVICE)
        self.image_view = ImageView(ctx)
        
        # Inicia em estado de repouso com boca fechada
        self.definir_avatar_png(falar=False)
        
        # Configura as amarras da janela nativa do Android
        window_type = 2038 # TYPE_APPLICATION_OVERLAY
        flags = LayoutParams.FLAG_NOT_FOCUSABLE | LayoutParams.FLAG_LAYOUT_IN_SCREEN
        
        self.params = LayoutParams(
            220, 220, # Tamanho escalado para o avatar ficar visível e nítido na tela
            window_type, flags, PixelFormat.TRANSLUCENT
        )
        self.params.gravity = 51 # Canto superior esquerdo
        self.params.x = 150
        self.params.y = 150
        
        self.window_manager.addView(self.image_view, self.params)
        self.iniciado = True
        
        # Conecta o ciclo visual das bocas com o novo TtsService
        from src.services.tts_service import TtsService
        TtsService.get_instance().configurar_callbacks_visuais(
            on_start=lambda: self.definir_avatar_png(falar=True),
            on_done=lambda: self.definir_avatar_png(falar=False)
        )
        print("[Spica/Overlay] Bolha injetada no sistema e sincronizada ao TTS!")

    def definir_avatar_png(self, falar=False):
        """Muda o Bitmap do ImageView do Android com limpeza correta de memória."""
        if not HAS_ANDROID or not self.image_view:
            return
        
        # ✅ NOVO: Liberar bitmap anterior para evitar memory leak
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
        if HAS_ANDROID and self.window_manager and self.image_view and self.iniciado:
            try:
                # ✅ NOVO: Liberar bitmap ANTES de remover view
                if self._bitmap_atual:
                    try:
                        self._bitmap_atual.recycle()
                    except:
                        pass
                    self._bitmap_atual = None
                
                self.window_manager.removeView(self.image_view)
                self.image_view = None
                self.iniciado = False
                print("[Spica/Overlay] Overlay removido e memória liberada correctamente")
            except Exception as e:
                print(f"[Spica/Overlay] Erro ao remover overlay: {e}")

    def destruir(self):
        """✅ NOVO: Destruir completamente o overlay."""
        self.desligar_bolha()
