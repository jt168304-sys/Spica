# service_log.py — Log em arquivo que funciona em QUALQUER processo (Activity
# ou service.py), gravando num local acessível via Termux sem precisar de
# root/adb. Criado porque o main.py só loga a Activity — o service.py nunca
# tinha nenhuma visibilidade até agora.
import os
import time

_caminho_log = None


def _resolver_caminho():
    global _caminho_log
    if _caminho_log is not None:
        return _caminho_log
    try:
        from jnius import autoclass
        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        ext_dir = PythonActivity.mActivity.getExternalFilesDir(None).getAbsolutePath()
    except Exception:
        ext_dir = "/storage/emulated/0/Android/data/com.spica.spica/files"
    try:
        os.makedirs(ext_dir, exist_ok=True)
    except Exception:
        pass
    _caminho_log = os.path.join(ext_dir, "spica_service_log.txt")
    return _caminho_log


def slog(msg):
    """Grava uma linha de log com timestamp — funciona tanto no processo da
    Activity quanto no processo do service.py. Nunca lança exceção."""
    linha = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(f"[Spica/SLOG] {linha}")
    try:
        caminho = _resolver_caminho()
        with open(caminho, "a", encoding="utf-8") as f:
            f.write(linha + "\n")
    except Exception as e:
        print(f"[Spica/SLOG] Falha ao gravar log: {e}")
