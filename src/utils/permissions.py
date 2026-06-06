# permissions.py
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
            # Tenta cada permissao individualmente para nao deixar uma falha cancelar as outras
            perms = []
            for nome in [
                "INTERNET", "CAMERA", "RECORD_AUDIO", "VIBRATE",
                "READ_EXTERNAL_STORAGE", "WRITE_EXTERNAL_STORAGE",
                "READ_MEDIA_IMAGES",   # Android 13+
            ]:
                try:
                    perms.append(getattr(Permission, nome))
                except AttributeError:
                    pass   # Constante nao existe nessa versao do p4a — ok
            if perms:
                request_permissions(perms)
        except Exception as e:
            self.logger.warning(f"Erro permissoes: {e}")

    def pedir_overlay(self):
        """Abre configuracoes do Android para SYSTEM_ALERT_WINDOW."""
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
            return Settings.canDrawOverlays(PythonActivity.mActivity)
        except Exception:
            return False

    def verificar(self, permissao: str) -> bool:
        return True
