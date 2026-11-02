# arquivos.py — Pastas "textos" e "imagens" da Spica, dentro da pasta do app que o Android deixa ver
# (Android/data/com.spica.spica/files). Você pode colocar .txt em "textos" pelo gerenciador de arquivos,
# e a Spica lê com a ferramenta ler_arquivo. A memória (banco) continua privada no app.
import os

PASTAS = ("textos", "imagens")


def raiz():
    try:
        from jnius import autoclass
        ctx = autoclass("org.kivy.android.PythonActivity").mActivity
        return ctx.getExternalFilesDir(None).getAbsolutePath()
    except Exception:
        return os.environ.get("ANDROID_PRIVATE") or os.path.expanduser("~")


def pasta(nome):
    if nome not in PASTAS:
        raise ValueError(f"pasta inválida: {nome}")
    caminho = os.path.join(raiz(), nome)
    os.makedirs(caminho, exist_ok=True)
    return caminho


def listar(nome):
    return sorted(f for f in os.listdir(pasta(nome)) if not f.startswith("."))[:300]


def ler(nome, arquivo, limite=6000):
    """Devolve (texto, erro). Só lê .txt e .md dentro da pasta indicada (sem sair dela)."""
    base = os.path.realpath(pasta(nome))
    alvo = os.path.realpath(os.path.join(base, os.path.basename(arquivo or "")))
    if not alvo.startswith(base + os.sep):
        return None, "caminho não permitido"
    if not os.path.isfile(alvo):
        return None, "arquivo não existe nessa pasta"
    if not alvo.lower().endswith((".txt", ".md")):
        return None, "só consigo ler .txt e .md"
    with open(alvo, encoding="utf-8", errors="replace") as arq:
        return arq.read(limite), ""
