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


def escrever(nome, conteudo):
    """Salva uma anotação .txt na pasta textos. Não sobrescreve: cria 'nome 2.txt' se já existir."""
    import re
    base = os.path.splitext(os.path.basename(nome or "anotacao"))[0]
    base = re.sub(r"[^\w\- ]", "", base).strip()[:60] or "anotacao"
    pasta_textos = pasta("textos")
    destino = os.path.join(pasta_textos, base + ".txt")
    i = 2
    while os.path.exists(destino):
        destino = os.path.join(pasta_textos, f"{base} {i}.txt")
        i += 1
    with open(destino, "w", encoding="utf-8") as arq:
        arq.write(conteudo or "")
    return destino
