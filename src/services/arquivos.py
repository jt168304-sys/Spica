import re
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


# ---------------------------------------------------------------- criar arquivos (txt, md, csv, json, html, pdf)
def _normalizar_texto(conteudo):
    t = str(conteudo or "")
    t = t.replace("\r\n", "\n").replace("\\n", "\n").replace("\\t", "\t")
    
    # Separa o texto em parágrafos se não houver quebras de linha e o texto for maior que 300 caracteres
    if "\n" not in t and len(t) > 300:
        frases = t.split(". ")
        paragrafos = []
        for i in range(0, len(frases), 4):
            paragrafo = ". ".join(frases[i:i + 4])
            paragrafos.append(paragrafo)
        t = "\n\n".join(paragrafos)
    
    return t


def _nome_base(nome):
    base = os.path.splitext(os.path.basename(str(nome or "arquivo")))[0]
    base = re.sub(r"[^\w\- ]", "", base).strip()[:60]
    return base or "arquivo"


def _pdf_bytes(titulo, texto):
    import textwrap
    linhas = []
    if titulo:
        linhas += [titulo, ""]
    for par in (texto or "").split("\n"):
        linhas += textwrap.wrap(par, 95) or [""]
    if not linhas:
        linhas = [""]
    por_pagina = 54
    paginas = [linhas[i:i + por_pagina] for i in range(0, len(linhas), por_pagina)]

    def esc(s):
        b = s.encode("cp1252", "replace").decode("latin-1")
        return b.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    objetos = {}
    n_pag = len(paginas)
    kids = " ".join(f"{4 + 2 * i} 0 R" for i in range(n_pag))
    objetos[1] = "<< /Type /Catalog /Pages 2 0 R >>"
    objetos[2] = f"<< /Type /Pages /Kids [{kids}] /Count {n_pag} >>"
    objetos[3] = "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>"
    for i, pag in enumerate(paginas):
        pid, cid = 4 + 2 * i, 5 + 2 * i
        corpo = "BT /F1 11 Tf 14 TL 50 790 Td\n" + "".join(f"({esc(l)}) Tj T*\n" for l in pag) + "ET"
        objetos[pid] = (f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
                        f"/Resources << /Font << /F1 3 0 R >> >> /Contents {cid} 0 R >>")
        objetos[cid] = f"<< /Length {len(corpo.encode('latin-1'))} >>\nstream\n{corpo}\nendstream"
    saida = bytearray(b"%PDF-1.4\n")
    offsets = {}
    for num in sorted(objetos):
        offsets[num] = len(saida)
        saida += f"{num} 0 obj\n{objetos[num]}\nendobj\n".encode("latin-1")
    total = len(objetos) + 1
    xref_pos = len(saida)
    saida += f"xref\n0 {total}\n0000000000 65535 f \n".encode("latin-1")
    for num in sorted(objetos):
        saida += f"{offsets[num]:010d} 00000 n \n".encode("latin-1")
    saida += (f"trailer\n<< /Size {total} /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF\n").encode("latin-1")
    return bytes(saida)


def _caminho_livre(pasta_destino, base, ext):
    destino = os.path.join(pasta_destino, f"{base}.{ext}")
    i = 2
    while os.path.exists(destino):
        destino = os.path.join(pasta_destino, f"{base} {i}.{ext}")
        i += 1
    return destino


def criar_arquivo(nome, conteudo, formato="txt", modo="criar"):
    formato = str(formato or "txt").lower().strip().lstrip(".")
    if formato not in ("txt", "md", "csv", "json", "html", "pdf"):
        raise ValueError("formato aceito: txt, md, csv, json, html ou pdf")
    modo = str(modo or "criar").lower().strip()
    texto = _normalizar_texto(conteudo)
    base = _nome_base(nome)
    pasta_textos = pasta("textos")
    if modo == "acrescentar":
        destino = os.path.join(pasta_textos, f"{base}.{formato}")
        if formato == "pdf" or not os.path.exists(destino):
            raise ValueError(f"para acrescentar, '{base}.{formato}' precisa existir (crie primeiro com modo criar)")
        with open(destino, "a", encoding="utf-8") as arq:
            arq.write(("\n" if texto and not texto.startswith("\n") else "") + texto)
        return {"ok": True, "arquivo": os.path.basename(destino),
                "resultado": f"parte acrescentada a {os.path.basename(destino)}",
                "tamanho_bytes": os.path.getsize(destino)}
    destino = _caminho_livre(pasta_textos, base, formato)
    if formato == "pdf":
        with open(destino, "wb") as arq:
            arq.write(_pdf_bytes(base, texto))
    else:
        with open(destino, "w", encoding="utf-8") as arq:
            arq.write(texto)
    return {"ok": True, "arquivo": os.path.basename(destino),
            "resultado": f"arquivo criado: {os.path.basename(destino)}",
            "tamanho_bytes": os.path.getsize(destino)}


def converter_para_pdf(arquivo):
    base = _nome_base(arquivo)
    pasta_textos = pasta("textos")
    origem = None
    for ext in (".txt", ".md"):
        if os.path.exists(os.path.join(pasta_textos, base + ext)):
            origem = os.path.join(pasta_textos, base + ext)
            break
    if origem is None:
        raise ValueError(f"não achei {base}.txt ou {base}.md na pasta textos")
    with open(origem, encoding="utf-8", errors="replace") as arq:
        texto = arq.read()
    destino = _caminho_livre(pasta_textos, base, "pdf")
    with open(destino, "wb") as arq:
        arq.write(_pdf_bytes(base, texto))
    return {"ok": True, "arquivo": os.path.basename(destino),
            "resultado": f"PDF criado: {os.path.basename(destino)}",
            "tamanho_bytes": os.path.getsize(destino)}
