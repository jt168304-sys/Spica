"""
src/utils/permissions.py — Permissões Android
Versão compatível com Pydroid 3
"""

from kivy.utils import platform
from src.utils.logger import WindLogger


class PermissionManager:
    """
    Gerencia permissões Android.
    No Pydroid 3: pula tudo (o Pydroid já tem as permissões necessárias).
    No APK compilado com Buildozer: solicita normalmente.
    """

    def __init__(self):
        self.logger = WindLogger()

    def request_all(self):
        """Solicita permissões. Seguro para chamar em qualquer ambiente."""

        if platform != "android":
            self.logger.info("PC detectado — permissões ignoradas.")
            return

        # Detecta Pydroid 3 pelo caminho do executável Python
        import sys
        executavel = sys.executable.lower()
        e_pydroid = "ru.iiec" in executavel or "pydroid" in executavel

        if e_pydroid:
            self.logger.info("Pydroid 3 detectado — pulando permissões (já concedidas pelo Pydroid).")
            return

        # APK real (Buildozer) — solicita permissões normalmente
        try:
            from android.permissions import request_permissions, Permission
            request_permissions([
                Permission.RECORD_AUDIO,
                Permission.WRITE_EXTERNAL_STORAGE,
                Permission.READ_EXTERNAL_STORAGE,
                Permission.INTERNET,
                Permission.VIBRATE,
            ])
            self.logger.info("Permissões solicitadas.")
        except Exception as e:
            self.logger.warning(f"Erro ao solicitar permissões (não crítico): {e}")

    def verificar(self, permissao: str) -> bool:
        return True  # No Pydroid, assume concedido

    def tem_microfone(self) -> bool:
        return True
