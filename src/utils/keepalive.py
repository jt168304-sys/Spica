# keepalive.py — Mantém a Spica viva em segundo plano (sem Activity transparente)
# Estratégia: Foreground Service (mic) + bolha SYSTEM_ALERT_WINDOW + isenção de bateria.
# A Activity só é "minimizada" (moveTaskToBack), nunca escondida nem destruída.
from kivy.utils import platform

HAS_ANDROID = False
if platform == "android":
    try:
        from jnius import autoclass
        from android.runnable import run_on_ui_thread
        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        Context = autoclass("android.content.Context")
        Intent = autoclass("android.content.Intent")
        Uri = autoclass("android.net.Uri")
        AndroidSettings = autoclass("android.provider.Settings")
        HAS_ANDROID = True
    except Exception as e:
        print(f"[Spica/KeepAlive] jnius indisponivel: {e}")

if not HAS_ANDROID:
    def run_on_ui_thread(func):
        return func


def ignorando_otimizacao_bateria():
    """True se o Android já NÃO aplica otimização de bateria ao app."""
    if not HAS_ANDROID:
        return True
    try:
        ctx = PythonActivity.mActivity
        pm = ctx.getSystemService(Context.POWER_SERVICE)
        return bool(pm.isIgnoringBatteryOptimizations(ctx.getPackageName()))
    except Exception as e:
        print(f"[Spica/KeepAlive] Erro ao checar bateria: {e}")
        return True  # na dúvida, não trava o fluxo


def pedir_ignorar_otimizacao_bateria():
    """Abre o diálogo do sistema 'Permitir que o app rode sem restrição de bateria'.
    Exige REQUEST_IGNORE_BATTERY_OPTIMIZATIONS no buildozer.spec."""
    if not HAS_ANDROID:
        return
    try:
        ctx = PythonActivity.mActivity
        intent = Intent(
            AndroidSettings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS,
            Uri.parse(f"package:{ctx.getPackageName()}"),
        )
        ctx.startActivity(intent)
    except Exception as e:
        print(f"[Spica/KeepAlive] Erro ao pedir isenção de bateria: {e}")


@run_on_ui_thread
def minimizar_app():
    """Equivale a apertar Home: o usuário vê a tela inicial, o app continua vivo."""
    if not HAS_ANDROID:
        return
    try:
        PythonActivity.mActivity.moveTaskToBack(True)
    except Exception as e:
        print(f"[Spica/KeepAlive] Erro ao minimizar: {e}")
