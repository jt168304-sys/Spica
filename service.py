import os
import sys

base_dir = os.path.dirname(os.path.abspath(__file__))
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)
# service.py — O coração da Spica em segundo plano
import os
import time
import traceback
from kivy.utils import platform
from src.utils.service_log import slog

slog("[FGS] Processo de segundo plano (service.py) iniciado!")

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
        slog(f"[FGS] Falha ao promover FGS microphone: {e}")

    try:
        power_manager = service_context.getSystemService(Context.POWER_SERVICE)
        wake_lock = power_manager.newWakeLock(
            PowerManager.PARTIAL_WAKE_LOCK,
            "Spica::BackgroundServiceWakeLock"
        )
        wake_lock.acquire()
        slog("[FGS] WakeLock adquirido com sucesso!")
    except Exception as e:
        slog(f"[FGS] Falha ao adquirir WakeLock: {e}")

    from src.services.listen_ipc import ha_pedido, consumir_pedido, responder
    from src.services.mic_recorder import MicRecorder
    from src.services.voice_service import VoiceService

    try:
        voice = VoiceService.get_instance()
    except Exception as e:
        slog(f"[FGS] Erro ao instanciar VoiceService: {e}")
        voice = None

    slog("[FGS] Loop principal de escuta aguardando comandos...")
    while True:
        try:
            if ha_pedido() and consumir_pedido():
                slog("[FGS] Pedido de escuta recebido via IPC! Gravando áudio...")
                mic = MicRecorder()
                wav = mic.capturar_utterance()
                if not wav:
                    slog("[FGS] Sem áudio capturado no FGS.")
                    responder("Nao ouvi")
                else:
                    slog("[FGS] Áudio capturado com sucesso. Transcrevendo via Whisper...")
                    if voice is not None:
                        texto = voice._transcrever_whisper(wav)
                    else:
                        v = VoiceService()
                        texto = v._transcrever_whisper(wav)
                    slog(f"[FGS] Transcrição concluída: {texto!r}")
                    responder(texto or "Nao ouvi")
        except Exception as e:
            err_tb = traceback.format_exc()
            slog(f"[FGS] Erro no ciclo de escuta: {e}\n{err_tb}")
            try:
                responder("Erro ao ouvir")
            except Exception:
                pass
        time.sleep(0.15)
else:
    while True:
        time.sleep(1)
