# permissions.py — Gerenciador de permissoes Android
from kivy.utils import platform
from src.utils.logger import WindLogger


class PermissionManager:
    def __init__(self):
        self.logger = WindLogger()

    def request_all(self):
        if platform != "android":
            return
        try:
            from android.permissions import request_permissions, Permission
            request_permissions([
                Permission.INTERNET,
                Permission.CAMERA,
                Permission.RECORD_AUDIO,
                Permission.READ_MEDIA_IMAGES,
                Permission.READ_EXTERNAL_STORAGE,
                Permission.WRITE_EXTERNAL_STORAGE,
                Permission.VIBRATE,
            ])
        except Exception as e:
            self.logger.warning(f"Erro permissoes: {e}")

    def pedir_overlay(self):
        """Solicita permissao de sobreposicao de apps (SYSTEM_ALERT_WINDOW)."""
        if platform != "android":
            return True
        try:
            from jnius import autoclass
            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            Settings = autoclass("android.provider.Settings")
            Intent = autoclass("android.content.Intent")
            Uri = autoclass("android.net.Uri")
            ctx = PythonActivity.mActivity
            if not Settings.canDrawOverlays(ctx):
                intent = Intent(
                    Settings.ACTION_MANAGE_OVERLAY_PERMISSION,
                    Uri.parse(f"package:{ctx.getPackageName()}")
                )
                ctx.startActivity(intent)
                return False
            return True
        except Exception as e:
            self.logger.warning(f"Erro overlay: {e}")
            return False

    def tem_overlay(self):
        if platform != "android":
            return True
        try:
            from jnius import autoclass
            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            Settings = autoclass("android.provider.Settings")
            ctx = PythonActivity.mActivity
            return Settings.canDrawOverlays(ctx)
        except Exception:
            return False

    def verificar(self, permissao: str) -> bool:
        return True

    def tem_microfone(self) -> bool:
        return True
