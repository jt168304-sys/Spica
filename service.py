# service.py — O coração da Spica em segundo plano (v16 Estável com WakeLock)
import os
import time
from kivy.utils import platform

print("[Spica/Service] Processo de segundo plano iniciado!")

if platform == "android":
    from jnius import autoclass
    
    Context = autoclass('android.content.Context')
    PowerManager = autoclass('android.os.PowerManager')
    PythonService = autoclass("org.kivy.android.PythonService")
    
    service_context = PythonService.mService

    try:
        from src.services.fg_service import promover_foreground_microfone
        promover_foreground_microfone(service_context)
    except Exception as e:
        print(f"[Spica/Service] Falha ao promover FGS microphone: {e}")
    
    try:
        power_manager = service_context.getSystemService(Context.POWER_SERVICE)
        wake_lock = power_manager.newWakeLock(
            PowerManager.PARTIAL_WAKE_LOCK,
            "Spica::BackgroundServiceWakeLock"
        )
        wake_lock.acquire()
        print("[Spica/Service] WakeLock adquirido com sucesso!")
    except Exception as e:
        print(f"[Spica/Service] Falha ao adquirir WakeLock (verifique permissao WAKE_LOCK no buildozer.spec): {e}")

    PythonActivity = autoclass("org.kivy.android.PythonActivity")
    PythonActivity.mActivity = service_context
    print("[Spica/Service] FGS microphone ativo. Overlay na Activity, AudioRecord neste processo.")

    from src.services.listen_ipc import ha_pedido, consumir_pedido, responder
    from src.services.mic_recorder import MicRecorder
    from src.services.voice_service import VoiceService

    voice = VoiceService.get_instance()

    while True:
        try:
            if ha_pedido() and consumir_pedido():
                print("[Spica/Service] Pedido de escuta recebido, gravando no FGS...")
                mic = MicRecorder()
                wav = mic.capturar_utterance()
                if not wav:
                    responder("Nao ouvi")
                else:
                    texto = voice._transcrever_whisper(wav)
                    responder(texto or "Nao ouvi")
        except Exception as e:
            print("[Spica/Service] Erro no ciclo de escuta: %s" % e)
            try:
                responder("Erro ao ouvir")
            except Exception:
                pass
        time.sleep(0.15)
else:
    while True:
        time.sleep(1)
