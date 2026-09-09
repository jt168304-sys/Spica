# service.py — Foreground service tipo microphone (Android 14)
# Nao importa VoiceService/Kivy aqui: isso derrubava o processo e o mic
# nunca abria. Overlay e AudioRecord ficam na Activity.
import time
from kivy.utils import platform

print("[Spica/Service] Processo de segundo plano iniciado!")

if platform == "android":
    from jnius import autoclass

    Context = autoclass("android.content.Context")
    PowerManager = autoclass("android.os.PowerManager")
    PythonService = autoclass("org.kivy.android.PythonService")

    service_context = PythonService.mService

    try:
        from src.services.fg_service import promover_foreground_microfone
        promover_foreground_microfone(service_context)
    except Exception as e:
        print("[Spica/Service] Falha ao promover FGS microphone: %s" % e)

    try:
        power_manager = service_context.getSystemService(Context.POWER_SERVICE)
        wake_lock = power_manager.newWakeLock(
            PowerManager.PARTIAL_WAKE_LOCK,
            "Spica::BackgroundServiceWakeLock",
        )
        wake_lock.acquire()
        print("[Spica/Service] WakeLock adquirido com sucesso!")
    except Exception as e:
        print("[Spica/Service] Falha ao adquirir WakeLock: %s" % e)

    PythonActivity = autoclass("org.kivy.android.PythonActivity")
    PythonActivity.mActivity = service_context
    print("[Spica/Service] FGS microphone ativo. Mic grava na Activity.")

while True:
    time.sleep(1)
