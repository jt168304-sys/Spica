# service.py — O código que roda invisível em background dentro do Android
import os
import time
from jnius import autoclass, PythonJavaClass, java_method
from android.runnable import run_on_ui_thread

# Importações das ferramentas nativas de interface do Android
Context = autoclass('android.content.Context')
WindowManager = autoclass('android.view.WindowManager')
LayoutParams = autoclass('android.view.WindowManager$LayoutParams')
ImageView = autoclass('android.widget.ImageView')
BitmapFactory = autoclass('android.graphics.BitmapFactory')
PixelFormat = autoclass('android.graphics.PixelFormat')
Motion= autoclass('android.view.MotionEvent')

class SpicaOverlayService:
    def __init__(self, android_service_context):
        self.ctx = android_service_context
        self.window_manager = self.ctx.getSystemService(Context.WINDOW_SERVICE)
        self.image_view = None
        self.params = None
        
        # Caminhos dos seus dois arquivos PNG (coloque na pasta de assets do app)
        self.app_dir = os.environ.get('ANDROID_APP_PATH', '')
        self.png_boca_fechada = os.path.join(self.app_dir, "assets", "boca_fechada.png")
        self.png_boca_aberta = os.path.join(self.app_dir, "assets", "boca_aberta.png")

    @run_on_ui_thread
    def criar_bolha_na_tela(self):
        """Desenha a imagem PNG por cima de qualquer aplicativo do celular."""
        self.image_view = ImageView(self.ctx)
        
        # Inicia com o PNG de boca fechada (Ouvindo / Esperando)
        self.definir_estado_visual(falar=False)

        # Configura as propriedades da janela flutuante do Android
        # TYPE_APPLICATION_OVERLAY garante que roda em cima de tudo nas APIs modernas
        window_type = 2038 #WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY
        
        flags = (
            LayoutParams.FLAG_NOT_FOCUSABLE | 
            LayoutParams.FLAG_LAYOUT_IN_SCREEN |
            LayoutParams.FLAG_WATCH_OUTSIDE_TOUCH
        )

        self.params = LayoutParams(
            180, 180, # Largura e Altura da bolha na tela (em pixels)
            window_type,
            flags,
            PixelFormat.TRANSLUCENT # Mantém o fundo do PNG transparente
        )
        
        # Posiciona a bolha no canto superior direito por padrão
        self.params.gravity = 51 # Gravity.TOP | Gravity.LEFT
        self.params.x = 100
        self.params.y = 100

        # Adiciona a imagem nativa diretamente no gerenciador de janelas do celular
        self.window_manager.addView(self.image_view, self.params)
        self._configurar_toque_na_bolha()

    def definir_estado_visual(self, falar=False):
        """Troca o arquivo PNG dinamicamente com base no estado da Spica."""
        try:
            caminho_imagem = self.png_boca_aberta if falar else self.png_boca_fechada
            if os.path.exists(caminho_imagem):
                bitmap = BitmapFactory.decodeFile(caminho_imagem)
                self.image_view.setImageBitmap(bitmap)
        except Exception as e:
            print(f"[Spica/Service] Erro ao alternar PNG da bolha: {e}")

    def _configurar_toque_na_bolha(self):
        """Permite arrastar a bolha pela tela e clicar para ativar a voz."""
        class TouchListener(PythonJavaClass):
            __javainterfaces__ = ['android/view/View$OnTouchListener']
            
            def __init__(self, overlay):
                super().__init__()
                self.overlay = overlay
                self.initial_x = 0
                self.initial_y = 0
                self.initial_touch_x = 0
                self.initial_touch_y = 0
                self.start_time = 0

            @java_method('(Landroid/view/View;Landroid/view/MotionEvent;)Z')
            def onTouch(self, view, event):
                action = event.getAction()
                if action == 0: # MotionEvent.ACTION_DOWN
                    self.initial_x = self.overlay.params.x
                    self.initial_y = self.overlay.params.y
                    self.initial_touch_x = event.getRawX()
                    self.initial_touch_y = event.getRawY()
                    self.start_time = time.time()
                    return True
                elif action == 2: # MotionEvent.ACTION_MOVE
                    # Atualiza a posição da bolha conforme o usuário arrasta o dedo
                    self.overlay.params.x = int(self.initial_x + (event.getRawX() - self.initial_touch_x))
                    self.overlay.params.y = int(self.initial_y + (event.getRawY() - self.initial_touch_y))
                    self.overlay.window_manager.updateViewLayout(self.overlay.image_view, self.overlay.params)
                    return True
                elif action == 1: # MotionEvent.ACTION_UP
                    # Se foi apenas um toque rápido, dispara o comando de voz
                    if time.time() - self.start_time < 0.2:
                        self.overlay.capturar_fala_em_background()
                    return True
                return False

        self.image_view.setOnTouchListener(TouchListener(self))

    def capturar_fala_em_background(self):
        """Ativa o microfone e chaveia os PNGs conforme o fluxo da IA."""
        # 1. Muda para boca fechada (indica que está ouvindo)
        self.definir_estado_visual(falar=False)
        
        def processar_resposta_ia(texto_resposta):
            # 2. Quando a Groq responder, muda para boca aberta (falando pelo TTS)
            self.definir_estado_visual(falar=True)
            
            # Aqui entra o seu TtsManager.falar(texto_resposta)
            # Ao terminar de falar via callback do TTS, chame novamente:
            # self.definir_estado_visual(falar=False)

        # Dispara o VoiceService nativo que blindamos anteriormente
        from src.services.voice_service import VoiceService
        from src.services.groq_service import GroqService
        
        def callback_voz(texto_capturado):
            if texto_capturado and texto_capturado != "Nao ouvi":
                # Envia o áudio capturado fora do app direto para a API do Llama
                GroqService.get_instance().perguntar(texto_capturado, processar_resposta_ia)
            else:
                self.definir_estado_visual(falar=False)

        VoiceService.get_instance().ouvir(callback_voz)

    @run_on_ui_thread
    def remover_bolha_da_tela(self):
        if self.window_manager and self.image_view:
            self.window_manager.removeView(self.image_view)
