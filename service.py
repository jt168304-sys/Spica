# service.py — O coração da Spica em segundo plano (v16 Estável)
import os
import time
import threading
from kivy.utils import platform

print("[Spica/Service] ✶ Processo de segundo plano iniciado!")

if platform == "android":
    from jnius import autoclass, PythonJavaClass, java_method
    
    # Captura o contexto nativo do Serviço Android que está rodando este script
    PythonService = autoclass("org.kivy.android.PythonService")
    service_context = PythonService.mService
    
    # Redireciona o ponto de atividade do Pyjnius para o contexto do Serviço
    # Isso evita colisões e quebras quando a janela principal do Kivy é minimizada
    PythonActivity = autoclass("org.kivy.android.PythonActivity")
    PythonActivity.mActivity = service_context

    # Importação dos nossos serviços globais
    from src.services.overlay import SpicaOverlay
    from src.services.tts_service import TtsService
    from src.services.voice_service import VoiceService
    from src.services.groq_service import GroqService

    # Instancia e ativa a janela flutuante da Bolha
    overlay = SpicaOverlay()
    overlay.ligar_bolha()

    # ── MÁQUINA DE TOQUE E ARRASTE NATIVA (JNI) ──────────────────────────────
    class BolhaTouchListener(PythonJavaClass):
        __javainterfaces__ = ['android/view/View$OnTouchListener']
        __javacontext__ = 'app'

        def __init__(self, overlay_manager):
            super().__init__()
            self.ov = overlay_manager
            self.x_inicial = 0
            self.y_inicial = 0
            self.toque_x_inicial = 0
            self.toque_y_inicial = 0
            self.tempo_clique = 0

        @java_method('(Landroid/view/View;Landroid/view/MotionEvent;)Z')
        def onTouch(self, view, event):
            acao = event.getAction()
            
            if acao == 0:  # MotionEvent.ACTION_DOWN (Dedo encostou)
                self.x_inicial = self.ov.params.x
                self.y_inicial = self.ov.params.y
                self.toque_x_inicial = event.getRawX()
                self.toque_y_inicial = event.getRawY()
                self.tempo_clique = time.time()
                return True
                
            elif acao == 2:  # MotionEvent.ACTION_MOVE (Arrastando o avatar)
                delta_x = int(event.getRawX() - self.toque_x_inicial)
                delta_y = int(event.getRawY() - self.toque_y_inicial)
                
                # Atualiza as coordenadas da bolha no gerenciador de janelas do Android
                self.ov.params.x = self.x_inicial + delta_x
                self.ov.params.y = self.y_inicial + delta_y
                self.ov.window_manager.updateViewLayout(self.ov.image_view, self.ov.params)
                return True
                
            elif acao == 1:  # MotionEvent.ACTION_UP (Dedo levantou)
                # Se o movimento durou menos de 0.25 segundos e quase não se moveu, foi um Clique!
                if (time.time() - self.tempo_clique) < 0.25:
                    print("[Spica/Service] Clique detectado! Ativando audição...")
                    executar_fluxo_ia_background()
                return True
                
            return False

    # ── PIPELINE DE INTELIGÊNCIA EM BACKGROUND ─────────────────────────────────
    def executar_fluxo_ia_background():
        """Gerencia o ciclo de ouvir, perguntar ao Llama e responder por voz fora do app."""
        # 1. Garante que qualquer áudio anterior seja interrompido
        TtsService.get_instance().parar()
        
        # Garante que a boca comece fechada enquanto escuta
        overlay.definir_avatar_png(falar=False)

        def callback_processamento_groq(resposta_texto):
            print(f"[Spica/Service] Resposta da Groq recebida: {resposta_texto[:50]}...")
            # 3. Faz a Spica falar a resposta (os callbacks do tts_service abrirão/fecharão a boca)
            TtsService.get_instance().falar(resposta_texto)

        def callback_transcricao_voz(texto_escutado):
            if not texto_escutado or texto_escutado in ["Nao ouvi", "Erro"]:
                print("[Spica/Service] Áudio não capturado ou nulo.")
                return
                
            print(f"[Spica/Service] Usuário disse: {texto_escutado}")
            # 2. Envia o texto obtido direto para a API da Groq
            GroqService.get_instance().perguntar(
                mensagem=texto_escutado,
                callback=callback_processamento_groq
            )

        # Dispara o microfone nativo
        VoiceService.get_instance().ouvir(callback=callback_transcricao_voz)

    # Injeta o Listener de toque diretamente na ImageView nativa da nossa bolha
    if overlay.image_view:
        listener_nativo = BolhaTouchListener(overlay)
        overlay.image_view.setOnTouchListener(listener_nativo)
        print("[Spica/Service] Controle de toque e arraste acoplado à bolha!")

# Loop infinito estável para impedir que o Android encerre o processo do script
while True:
    time.sleep(1)
