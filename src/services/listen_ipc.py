# listen_ipc.py — Pedido de escuta da Activity para o FGS (processo separado).
#
# No Moto G24 / Android 14, AudioRecord na Activity pausada pode voltar
# silenciado mesmo com o LED do mic aceso. O FGS com tipo microphone e o
# unico processo em que o sistema garante PCM de verdade.
import os
import time

CMD_NAME = "spica_listen.cmd"
OUT_NAME = "spica_listen.out"
TIMEOUT_S = 45.0


def _pasta():
    from jnius import autoclass
    PythonActivity = autoclass("org.kivy.android.PythonActivity")
    ctx = PythonActivity.mActivity
    return ctx.getCacheDir().getAbsolutePath()


def caminhos():
    pasta = _pasta()
    return os.path.join(pasta, CMD_NAME), os.path.join(pasta, OUT_NAME)


def pedir_escuta():
    cmd, out = caminhos()
    try:
        if os.path.exists(out):
            os.remove(out)
    except Exception:
        pass
    with open(cmd, "w", encoding="utf-8") as f:
        f.write("GO")
    inicio = time.time()
    while time.time() - inicio < TIMEOUT_S:
        if os.path.exists(out):
            try:
                with open(out, "r", encoding="utf-8") as f:
                    texto = f.read()
                os.remove(out)
                return texto
            except Exception:
                return None
        time.sleep(0.12)
    return None


def ha_pedido():
    cmd, _out = caminhos()
    return os.path.exists(cmd)


def consumir_pedido():
    cmd, _out = caminhos()
    try:
        if os.path.exists(cmd):
            os.remove(cmd)
            return True
    except Exception:
        pass
    return False


def responder(texto):
    _cmd, out = caminhos()
    tmp = out + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(texto or "Nao ouvi")
    os.replace(tmp, out)
