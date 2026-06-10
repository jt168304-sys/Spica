# bubble.py — Controla o SpicaOverlayService (bolha real sobre outros apps)
from kivy.clock import Clock
from kivy.utils import platform


class FloatingBubble:
    """
    Inicia/para o SpicaOverlayService — a bolha que aparece sobre todos os apps.
    Esta classe não cria nenhum widget Kivy; apenas controla o Service Android.
    O visual da bolha é definido em SpicaOverlayService.java (criarViewBolha).
    Para trocar pelo design V-Tuber: edite criarViewBolha() no Java.
    """

    def __init__(self):
        self._service_iniciado = False
        if platform == "android":
            Clock.schedule_once(self._verificar_e_iniciar, 2.0)

    # ── Permissão ─────────────────────────────────────────────────────────────

    def _verificar_e_iniciar(self, dt=None):
        try:
            from jnius import autoclass
            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            Settings       = autoclass("android.provider.Settings")
            Intent         = autoclass("android.content.Intent")
            Uri            = autoclass("android.net.Uri")
            ctx = PythonActivity.mActivity

            if Settings.canDrawOverlays(ctx):
                print("[Spica] Permissao overlay OK — iniciando service")
                Clock.schedule_once(self._iniciar_service, 0.3)
            else:
                print("[Spica] Solicitando permissao overlay...")
                ctx.startActivity(Intent(
                    Settings.ACTION_MANAGE_OVERLAY_PERMISSION,
                    Uri.parse(f"package:{ctx.getPackageName()}"),
                ))
                # Tenta novamente em 10s (usuário precisa conceder a permissão)
                Clock.schedule_once(self._verificar_e_iniciar, 10.0)
        except Exception as e:
            print(f"[Spica] bubble verificar_e_iniciar: {e}")

    # ── Iniciar/parar service ──────────────────────────────────────────────────

    def _iniciar_service(self, dt=None):
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
            print(f"[Spica] _iniciar_service: {e}")

    def parar(self):
        """Chame ao sair do app para parar a bolha."""
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
            print("[Spica] SpicaOverlayService parado.")
        except Exception as e:
            print(f"[Spica] parar service: {e}")

    # ── Compat com código antigo que chama pulsar/parar_pulsar ───────────────

    def pulsar(self):
        pass  # Visual controlado pelo Java agora

    def parar_pulsar(self):
        pass
