# cofre.py — Cofre de histórias e piadas da Spica + registro completo das conversas (local, SQLite).
# Fica na mesma pasta da memória (armazenamento privado do app). Sem limite prático de texto:
# cada conversa vira uma linha, e cada coisa guardada no cofre também.
import os
import re
import sqlite3
import threading
import time

from src.services import memoria as _m

_TRAVA = threading.Lock()


def _con():
    con = sqlite3.connect(os.path.join(_m._pasta(), "cofre.db"), timeout=5)
    con.execute("CREATE TABLE IF NOT EXISTS conversas (id INTEGER PRIMARY KEY, quando REAL, usuario TEXT, spica TEXT)")
    con.execute("CREATE TABLE IF NOT EXISTS cofre (id INTEGER PRIMARY KEY, tipo TEXT, texto TEXT, criado REAL)")
    return con


def registrar_turno(usuario, spica):
    """Guarda a conversa inteira (sem cortes curtos). Conteúdo sensível do usuário é omitido."""
    try:
        u = (usuario or "")[:4000]
        if _m._SENSIVEL.search(u):
            u = "[omitido: conteudo sensivel]"
        with _TRAVA, _con() as con:
            con.execute("INSERT INTO conversas (quando, usuario, spica) VALUES (?,?,?)",
                        (time.time(), u, (spica or "")[:4000]))
    except Exception as e:
        print(f"[Spica/Cofre] registrar: {e}")


def guardar(texto, tipo="piada"):
    t = " ".join((texto or "").split())[:1500]
    if len(t) < 5:
        return False
    with _TRAVA, _con() as con:
        con.execute("INSERT INTO cofre (tipo, texto, criado) VALUES (?,?,?)", (tipo, t, time.time()))
    return True


def buscar(termo, n=3, minimo=1):
    alvo = _m._palavras(termo)
    if not alvo:
        return []
    pontos = []
    with _TRAVA, _con() as con:
        for tipo, texto in con.execute("SELECT tipo, texto FROM cofre"):
            comum = len(alvo & _m._palavras(texto))
            if comum >= minimo:
                pontos.append((comum, tipo, texto))
    pontos.sort(reverse=True)
    return pontos[:n]


def listar(n=15):
    with _TRAVA, _con() as con:
        return [r[0] for r in con.execute("SELECT texto FROM cofre ORDER BY id DESC LIMIT ?", (n,))]


def apagar(termo):
    alvo = _m._palavras(termo)
    if not alvo:
        return 0
    minimo = 2 if len(alvo) >= 2 else 1
    apagados = 0
    with _TRAVA, _con() as con:
        for cid, texto in list(con.execute("SELECT id, texto FROM cofre")):
            if len(alvo & _m._palavras(texto)) >= minimo:
                con.execute("DELETE FROM cofre WHERE id=?", (cid,))
                apagados += 1
    return apagados


_GUARDAR = re.compile(r"^\s*(spica[,:]?\s*)?(guarda|guarde|salva|salve|anota|anote|memoriza)\w*\s+(essa|esta|isso|aquela|aquele)?\s*(piada|historia|história|cena|frase)s?\s*[:,]?\s*(.{5,})$", re.I)
_TRAZER = re.compile(r"^\s*(spica[,:]?\s*)?(traz|traga|conta|conte|mostra|mostre|lembra|lembre|me conta|me mostra|me traz)\w*\s+(aquela|aquele|a|o|uma|um)?\s*(piada|historia|história|cena|frase)s?\s*(sobre|de|do|da)?\s*(.{2,})$", re.I)
_APAGAR = re.compile(r"^\s*(spica[,:]?\s*)?(esquece|esqueca|apaga|apague)\w*\s+(a|aquela|aquele|o)?\s*(piada|historia|história|cena|frase)s?\s*(sobre|de|do|da)\s+(.{2,})$", re.I)
_LISTAR = re.compile(r"(o que (tem|tenho) no cofre|meu cofre|lista (o )?cofre|mostra (o )?cofre)", re.I)


def tratar_comando(texto):
    """Comandos do cofre por texto. Devolve a resposta pronta ou None se não for comando do cofre."""
    try:
        m = _GUARDAR.match(texto or "")
        if m:
            tipo = m.group(4).lower().replace("história", "historia")
            ok = guardar(m.group(5), tipo)
            return "Guardei no meu cofre." if ok else "Isso ficou curto demais pra guardar."
        m = _APAGAR.match(texto or "")
        if m:
            n = apagar(m.group(6))
            return f"Pronto, tirei {n} coisa{'s' if n != 1 else ''} do cofre." if n else "Não achei isso no cofre."
        m = _TRAZER.match(texto or "")
        if m:
            achados = buscar(m.group(6))
            if not achados:
                return "Não achei nada no cofre sobre isso."
            return "Do meu cofre: " + " | ".join(t for _, _, t in achados)
        if _LISTAR.search(texto or ""):
            itens = listar(10)
            return ("No cofre: " + " | ".join(t[:80] for t in itens)) if itens else "O cofre ainda está vazio."
    except Exception as e:
        print(f"[Spica/Cofre] comando: {e}")
    return None


def bloco(mensagem):
    """Lembranças do cofre que combinam com a mensagem (só com pelo menos 2 palavras em comum)."""
    try:
        achados = buscar(mensagem, 2, minimo=2)
        if not achados:
            return ""
        return ("\n\n[COFRE - coisas que a pessoa pediu para guardar. Use só se combinar com a conversa, sem listar]\n"
                + "\n".join(f"- ({tipo}) {t[:300]}" for _, tipo, t in achados))
    except Exception:
        return ""
