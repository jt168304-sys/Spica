# src/utils/permissions.py
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
                Permission.RECORD_AUDIO,
                Permission.WRITE_EXTERNAL_STORAGE,
                Permission.READ_EXTERNAL_STORAGE,
                Permission.INTERNET,
                Permission.VIBRATE,
                Permission.CAMERA,
                Permission.READ_MEDIA_IMAGES,
            ])
        except Exception as e:
            self.logger.warning(f"Erro permissoes: {e}")

    def verificar(self, permissao: str) -> bool:
        return True

    def tem_microfone(self) -> bool:
        return True
