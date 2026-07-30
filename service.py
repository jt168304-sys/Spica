# service.py — O coração da Spica em segundo plano (v16 Estável com WakeLock)
import os
import time
import threading
from kivy.utils import platform

print("[Spica/Service] ✶ Processo de segundo plano iniciado!")

if platform == "android":
    from jnius import autoclass
    
    # Classes Java para gerenciar o WakeLock e contexto
    Context = autoclass('android.content.Context')
    PowerManager = autoclass('android.os.PowerManager')
    PythonService = autoclass("org.kivy.android.PythonService")
    
    # Captura o contexto nativo do Serviço Android que está rodando este script
    service_context = PythonService.mService
    
    # Adquire o WakeLock para evitar que a CPU durma em segundo plano no Android 14.
    # Envolvido em try/except: se a permissão WAKE_LOCK não estiver no manifest (como
    # estava faltando antes), isso lançava SecurityException e derrubava o service.py
    # INTEIRO antes mesmo da bolha/escuta serem religadas — silenciosamente, sem log.
    try:
        power_manager = service_context.getSystemService(Context.POWER_SERVICE)
        wake_lock = power_manager.newWakeLock(
            PowerManager.PARTIAL_WAKE_LOCK,
            "Spica::BackgroundServiceWakeLock"
        )
        wake_lock.acquire()
        print("[Spica/Service] 🔒 WakeLock adquirido com sucesso!")
    except Exception as e:
        print(f"[Spica/Service] ⚠️ Falha ao adquirir WakeLock (verifique permissão WAKE_LOCK no buildozer.spec): {e}")

    # Redireciona o ponto de atividade do Pyjnius para o contexto do Serviço
    PythonActivity = autoclass("org.kivy.android.PythonActivity")
    PythonActivity.mActivity = service_context

    # Importação do nosso serviço de overlay (a bolha em si)
    from src.services.overlay import SpicaOverlay

    # Instancia e ativa a janela flutuante da Bolha
    overlay = SpicaOverlay()
    overlay.ligar_bolha()
    # NOTA: ligar_bolha() já configura seu próprio listener de toque/arraste
    # (_configurar_toque_na_bolha, dentro de overlay.py) com o menu de escuta
    # contínua — o mesmo sistema que já funciona dentro do app. Antes havia
    # aqui um segundo listener (BolhaTouchListener) que SOBRESCREVIA esse,
    # usando um fluxo próprio (executar_fluxo_ia_background) com
    # usar_clock=True — que nunca entrega a resposta porque o service.py não
    # roda nenhum App() do Kivy, então o Clock nunca dispara nesse processo.
    # Removido para usar só o caminho único e já testado do overlay.py.
    print("[Spica/Service] Bolha religada usando o sistema de escuta do overlay.py (unificado).")

# Loop infinito estável para impedir que o Android encerre o processo do script
while True:
    time.sleep(1)
