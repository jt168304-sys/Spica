# bubble.py — Controla o SpicaOverlayService
from kivy.clock import Clock
from kivy.utils import platform


class FloatingBubble:

    def __init__(self):
        self._service_iniciado = False
        self._tentativas = 0
        if platform == "android":
            Clock.schedule_once(self._verificar_e_iniciar, 1.5)

    def _verificar_e_iniciar(self, dt=None):
        self._tentativas += 1
        try:
            from jnius import autoclass
            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            Settings       = autoclass("android.provider.Settings")
            Intent         = autoclass("android.content.Intent")
            Uri            = autoclass("android.net.Uri")
            ctx = PythonActivity.mActivity

            if Settings.canDrawOverlays(ctx):
                print("[Spica] Permissao OK — iniciando service")
                Clock.schedule_once(self._iniciar_service, 0.2)
            else:
                print("[Spica] Sem permissao — abrindo configuracoes")
                ctx.startActivity(Intent(
                    Settings.ACTION_MANAGE_OVERLAY_PERMISSION,
                    Uri.parse(f"package:{ctx.getPackageName()}"),
                ))
                # Verifica a cada 3s por até 10 tentativas
                if self._tentativas < 10:
                    Clock.schedule_once(self._verificar_e_iniciar, 3.0)
        except Exception as e:
            print(f"[Spica] bubble erro: {e}")

    def _iniciar_service(self, dt=None):
        if self._service_iniciado:
            return
        try:
            from jnius import autoclass
            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            Intent         = autoclass("android.content.Intent")
            Build          = autoclass("android.os.Build")
            ctx = PythonActivity.mActivity

            intent = Intent()
            intent.setClassName(ctx, "com.spica.SpicaOverlayService")

            if Build.VERSION.SDK_INT >= 26:
                ctx.startForegroundService(intent)
            else:
                ctx.startService(intent)

            self._service_iniciado = True
            print("[Spica] SpicaOverlayService iniciado!")
        except Exception as e:
            print(f"[Spica] iniciar_service erro: {e}")

    def parar(self):
        if not self._service_iniciado:
            return
        try:
            from jnius import autoclass
            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            Intent         = autoclass("android.content.Intent")
            ctx = PythonActivity.mActivity
            intent = Intent()
            intent.setClassName(ctx, "com.spica.SpicaOverlayService")
            ctx.stopService(intent)
            self._service_iniciado = False
        except Exception as e:
            print(f"[Spica] parar erro: {e}")

    def pulsar(self): pass
    def parar_pulsar(self): pass
