# fg_service.py — Sobe o foreground service com tipo microphone (Android 14+)
from kivy.utils import platform

_NOMES_SERVICO = (
    "ServiceSpicaservice",
    "ServiceSpicaService",
)


def estamos_no_servico():
    if platform != "android":
        return False
    try:
        from jnius import autoclass
        PythonService = autoclass("org.kivy.android.PythonService")
        return PythonService.mService is not None
    except Exception:
        return False


def _contexto():
    from jnius import autoclass
    if estamos_no_servico():
        PythonService = autoclass("org.kivy.android.PythonService")
        return PythonService.mService
    PythonActivity = autoclass("org.kivy.android.PythonActivity")
    return PythonActivity.mActivity


def _classe_servico():
    from jnius import autoclass
    ctx = _contexto()
    pkg = ctx.getPackageName()
    last = None
    for simples in _NOMES_SERVICO:
        nome = pkg + "." + simples
        try:
            return autoclass(nome)
        except Exception as e:
            last = e
    try:
        return autoclass("org.kivy.android.PythonService")
    except Exception as e:
        last = e
    raise RuntimeError("Classe do servico Spica nao encontrada: %s" % last)


def iniciar_servico(argumento=""):
    if platform != "android":
        return False
    try:
        from jnius import autoclass
        from src.utils.service_log import slog
        ctx = _contexto()
        cls = _classe_servico()
        slog("classe FGS: %s" % cls)
        if hasattr(cls, "start"):
            cls.start(ctx, argumento or "")
            slog("Foreground service iniciado via start()")
            return True
        Intent = autoclass("android.content.Intent")
        Build = autoclass("android.os.Build")
        intent = Intent(ctx, cls)
        if Build.VERSION.SDK_INT >= 26:
            ctx.startForegroundService(intent)
        else:
            ctx.startService(intent)
        slog("Foreground service iniciado via Intent")
        return True
    except Exception as e:
        try:
            from src.utils.service_log import slog
            slog("Falha ao iniciar FGS: %s: %s" % (type(e).__name__, e))
        except Exception:
            print("[Spica/FGS] Falha ao iniciar: %s" % e)
        return False


def parar_servico():
    if platform != "android":
        return
    try:
        from jnius import autoclass
        if estamos_no_servico():
            PythonService = autoclass("org.kivy.android.PythonService")
            PythonService.mService.stopSelf()
            return
        ctx = _contexto()
        cls = _classe_servico()
        if hasattr(cls, "stop"):
            cls.stop(ctx)
            return
        Intent = autoclass("android.content.Intent")
        ctx.stopService(Intent(ctx, cls))
    except Exception as e:
        print("[Spica/FGS] Falha ao parar servico: %s" % e)


def promover_foreground_microfone(service):
    """Garante startForeground() COM o tipo MICROPHONE.

    O python-for-android pode chamar startForeground(id, notification) sem o
    tipo. No Android 14 o microfone em segundo plano so e liberado se o FGS
    estiver com FOREGROUND_SERVICE_TYPE_MICROPHONE (128).
    """
    from jnius import autoclass
    from src.utils.service_log import slog

    Build = autoclass("android.os.Build")
    Context = autoclass("android.content.Context")
    NotificationBuilder = autoclass("android.app.Notification$Builder")
    FGS_MICROPHONE = 128

    channel_id = "spica_mic"
    if Build.VERSION.SDK_INT >= 26:
        NotificationChannel = autoclass("android.app.NotificationChannel")
        NotificationManager = autoclass("android.app.NotificationManager")
        nm = service.getSystemService(Context.NOTIFICATION_SERVICE)
        canal = NotificationChannel(
            channel_id,
            "Spica escuta",
            NotificationManager.IMPORTANCE_LOW,
        )
        canal.setDescription("Mantem o microfone ativo com a bolha")
        canal.setSound(None, None)
        nm.createNotificationChannel(canal)
        builder = NotificationBuilder(service, channel_id)
    else:
        builder = NotificationBuilder(service)

    info = service.getApplicationInfo()
    builder.setContentTitle("Spica")
    builder.setContentText("Escuta em segundo plano")
    builder.setSmallIcon(info.icon)
    builder.setOngoing(True)
    builder.setOnlyAlertOnce(True)
    notificacao = builder.build()

    try:
        if Build.VERSION.SDK_INT >= 29:
            service.startForeground(9001, notificacao, FGS_MICROPHONE)
        else:
            service.startForeground(9001, notificacao)
        slog("startForeground(microphone) OK")
    except Exception as e:
        slog("startForeground com tipo microphone falhou, tentando sem tipo: %s" % e)
        try:
            service.startForeground(9001, notificacao)
            slog("startForeground() sem tipo OK")
        except Exception as e2:
            slog("startForeground falhou de vez: %s" % e2)
