# fg_service.py — Inicializa o Foreground Service especifico (ServiceSpicaservice)
from kivy.utils import platform

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
    from src.utils.service_log import slog
    ctx = _contexto()
    pkg = ctx.getPackageName()

    candidatos = [
        f"{pkg}.ServiceSpicaservice",
        f"{pkg}.ServiceSpicaService",
        f"{pkg}.ServiceSpica",
        "org.kivy.android.PythonService"
    ]

    erros = []
    for nome in candidatos:
        try:
            cls = autoclass(nome)
            slog(f"[FGS] Classe do serviço resolvida com sucesso: {nome}")
            return cls
        except Exception as e:
            erros.append(f"{nome}: {e}")

    slog(f"[FGS] Falha ao carregar classes do serviço: {'; '.join(erros)}")
    raise RuntimeError("Classe do serviço Spica não encontrada")

def iniciar_servico(argumento=""):
    if platform != "android":
        return False
    try:
        from jnius import autoclass
        from src.utils.service_log import slog

        ctx = _contexto()
        cls = _classe_servico()

        if hasattr(cls, "start"):
            try:
                cls.start(ctx, argumento or "")
                slog("Foreground service iniciado via cls.start()")
                return True
            except Exception as e_start:
                slog(f"Falha ao chamar cls.start(): {e_start}")

        Intent = autoclass("android.content.Intent")
        BuildVersion = autoclass("android.os.Build$VERSION")
        intent = Intent(ctx, cls)

        if BuildVersion.SDK_INT >= 26:
            ctx.startForegroundService(intent)
        else:
            ctx.startService(intent)

        slog("Foreground service iniciado via Intent manual")
        return True
    except Exception as e:
        try:
            from src.utils.service_log import slog
            slog(f"Falha ao iniciar FGS: {type(e).__name__}: {e}")
        except Exception:
            print(f"[Spica/FGS] Falha ao iniciar: {e}")
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
        print(f"[Spica/FGS] Falha ao parar servico: {e}")

def promover_foreground_microfone(service):
    from jnius import autoclass
    from src.utils.service_log import slog

    BuildVersion = autoclass("android.os.Build$VERSION")
    Context = autoclass("android.content.Context")
    NotificationBuilder = autoclass("android.app.Notification$Builder")
    FGS_MICROPHONE = 128

    channel_id = "spica_mic"
    if BuildVersion.SDK_INT >= 26:
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
        if BuildVersion.SDK_INT >= 29:
            service.startForeground(9001, notificacao, FGS_MICROPHONE)
        else:
            service.startForeground(9001, notificacao)
        slog("startForeground(microphone) OK")
    except Exception as e:
        slog(f"startForeground com tipo microphone falhou: {e}")
