# memoria.py — Memória de longo prazo da Spica (local, em arquivo SQLite).
# Fica em <dados do app>/memoria/memoria.db. Sem bibliotecas extras: a busca é por palavras
# (sem acento) com peso por uso e recência. Tudo é protegido: se algo falhar, a Spica segue sem memória.
import json
import os
import re
import sqlite3
import threading
import time
import unicodedata

_TRAVA = threading.Lock()
_PARAR = {"a", "o", "e", "de", "do", "da", "que", "um", "uma", "para", "pra", "com", "em", "no", "na", "os", "as",
          "eu", "meu", "minha", "voce", "vc", "me", "se", "por", "mais", "ele", "ela", "isso", "esse", "essa"}
_SENSIVEL = re.compile(r"\b(senha|password|cpf|rg|cart[aã]o|cvv|token|chave)\b|\d{6,}", re.I)


def _norm(t):
    t = unicodedata.normalize("NFD", (t or "").lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def _palavras(t):
    return {p for p in re.findall(r"[a-z0-9]{3,}", _norm(t)) if p not in _PARAR}


def _pasta():
    base = os.environ.get("ANDROID_PRIVATE") or os.path.expanduser("~")
    pasta = os.path.join(base, "memoria")
    os.makedirs(pasta, exist_ok=True)
    return pasta


def _con():
    con = sqlite3.connect(os.path.join(_pasta(), "memoria.db"), timeout=5)
    con.execute("CREATE TABLE IF NOT EXISTS fatos (id INTEGER PRIMARY KEY, texto TEXT, criado REAL, "
                "atualizado REAL, usos INTEGER DEFAULT 0)")
    con.execute("CREATE TABLE IF NOT EXISTS imagens (id INTEGER PRIMARY KEY, caminho TEXT, assunto TEXT, "
                "prompt TEXT, criado REAL)")
    return con


# ------------------------------------------------------------------ fatos
def adicionar_fato(texto):
    """Guarda um fato (ou reforça um parecido). Devolve True se algo foi salvo."""
    texto = re.sub(r"\s+", " ", (texto or "").strip(" .\n"))[:160]
    if len(texto) < 6 or _SENSIVEL.search(texto):
        return False
    novas = _palavras(texto)
    with _TRAVA, _con() as con:
        for fid, ftxt in con.execute("SELECT id, texto FROM fatos"):
            velhas = _palavras(ftxt)
            if novas and velhas and len(novas & velhas) / max(len(novas | velhas), 1) >= 0.6:
                con.execute("UPDATE fatos SET texto=?, atualizado=?, usos=usos+1 WHERE id=?", (texto, time.time(), fid))
                return True
        con.execute("INSERT INTO fatos (texto, criado, atualizado) VALUES (?,?,?)", (texto, time.time(), time.time()))
    return True


def listar_fatos(limite=40):
    with _TRAVA, _con() as con:
        return [r[0] for r in con.execute("SELECT texto FROM fatos ORDER BY atualizado DESC LIMIT ?", (limite,))]


def esquecer(termo):
    """Apaga fatos que combinam com o termo. Devolve quantos foram apagados."""
    alvo = _palavras(termo)
    if not alvo:
        return 0
    apagados = 0
    with _TRAVA, _con() as con:
        for fid, ftxt in list(con.execute("SELECT id, texto FROM fatos")):
            if len(alvo & _palavras(ftxt)) >= max(1, min(len(alvo), 2)):
                con.execute("DELETE FROM fatos WHERE id=?", (fid,))
                apagados += 1
    return apagados


def apagar_tudo():
    with _TRAVA, _con() as con:
        con.execute("DELETE FROM fatos")
        con.execute("DELETE FROM imagens")


def relevantes(mensagem, limite=5):
    """Fatos mais úteis para esta mensagem: palavras em comum, uso e recência."""
    alvo = _palavras(mensagem)
    agora = time.time()
    pontos = []
    with _TRAVA, _con() as con:
        for fid, ftxt, atual, usos in con.execute("SELECT id, texto, atualizado, usos FROM fatos"):
            comum = len(alvo & _palavras(ftxt))
            recente = max(0.0, 1.0 - (agora - atual) / (60 * 86400))
            pontos.append((comum * 3 + recente + min(usos, 5) * 0.2, fid, ftxt))
    pontos.sort(reverse=True)
    escolhidos = [p for p in pontos[:limite] if p[0] > 0.9 or len(pontos) <= limite]
    if escolhidos:
        with _TRAVA, _con() as con:
            for _, fid, _t in escolhidos:
                con.execute("UPDATE fatos SET usos=usos+1 WHERE id=?", (fid,))
    return [p[2] for p in escolhidos]


def bloco_prompt(mensagem):
    """Texto curto para o system prompt, ou '' se não há nada relevante."""
    try:
        fatos = relevantes(mensagem)
        if not fatos:
            return ""
        return ("\n\n[O QUE VOCE SABE SOBRE QUEM ESTA FALANDO - use com naturalidade, so se ajudar, sem listar nem avisar que lembrou]\n"
                + "\n".join(f"- {f}" for f in fatos))
    except Exception as e:
        print(f"[Spica/Memoria] bloco: {e}")
        return ""


# ------------------------------------------------------------------ imagens
def registrar_imagem(caminho, assunto, prompt):
    try:
        with _TRAVA, _con() as con:
            con.execute("INSERT INTO imagens (caminho, assunto, prompt, criado) VALUES (?,?,?,?)",
                        (caminho, assunto[:300], prompt[:600], time.time()))
    except Exception as e:
        print(f"[Spica/Memoria] imagem: {e}")


def ultima_imagem():
    try:
        with _TRAVA, _con() as con:
            r = con.execute("SELECT caminho, assunto, prompt FROM imagens ORDER BY id DESC LIMIT 1").fetchone()
        return {"caminho": r[0], "assunto": r[1], "prompt": r[2]} if r else None
    except Exception:
        return None


# ------------------------------------------------------------------ comandos diretos (sem gastar IA)
_pendente_apagar_tudo = {"ate": 0.0}


def tratar_comando(texto):
    """Comandos de memória por texto. Devolve a resposta pronta, ou None se não for um comando."""
    t = _norm(texto).strip()
    t = re.sub(r"^(spica[,:]?\s*)", "", t)
    try:
        if _pendente_apagar_tudo["ate"] > time.time() and re.match(r"^(sim|pode|confirmo)[,. ]*(apague|apaga)", t):
            apagar_tudo()
            _pendente_apagar_tudo["ate"] = 0
            return "Pronto, apaguei tudo que eu guardava sobre você."
        if re.match(r"^(esquece|esqueca|apaga|apague) (tudo|toda a memoria|a memoria toda)", t):
            _pendente_apagar_tudo["ate"] = time.time() + 120
            return "Quer mesmo que eu apague tudo? Se sim, diga: sim, apague tudo."
        m = re.match(r"^(lembra|lembre|guarda|guarde|anota|anote|memoriza)( disso| isso| que)?[:, ]+(.{6,})$", t)
        if m:
            fato = re.sub(r"^\s*(spica[,:]?\s*)?(lembra|lembre|guarda|guarde|anota|anote|memoriza)(\s+(disso|isso|que))?[:,]?\s*",
                          "", texto, flags=re.I).strip()
            if re.match(r"(?i)(eu|meu|minha|meus|minhas|me|estou|sou)\b", fato):
                fato = "O usuário disse: " + fato      # deixa claro de quem é o fato
            if adicionar_fato(fato):
                return "Anotado, vou lembrar disso."
            return "Hmm, isso eu prefiro não guardar."
        m = re.match(r"^(esquece|esqueca|apaga|apague)( que| isso| sobre| a respeito de)?[:, ]+(.{3,})$", t)
        if m:
            n = esquecer(m.group(3))
            return f"Pronto, esqueci {n} coisa{'s' if n != 1 else ''} sobre isso." if n else "Não achei nada parecido na minha memória."
        if re.search(r"o que (voce|vc) (sabe|lembra|guardou).{0,20}(sobre mim|de mim)|minha memoria|o que (voce|vc) lembra", t):
            fatos = listar_fatos(12)
            if not fatos:
                return "Ainda não guardei nada sobre você. Se quiser, diga: lembra que..."
            return "Eu lembro disso sobre você: " + "; ".join(fatos) + "."
    except Exception as e:
        print(f"[Spica/Memoria] comando: {e}")
    return None


# ------------------------------------------------------------------ extração automática (em segundo plano)
_SINAIS = re.compile(r"\b(eu|meu|minha|meus|minhas|gosto|amo|odeio|prefiro|estou|sou|trabalho|estudo|moro|quero|vou|fiz|criei|favorit)\w*", re.I)
_ultima_extracao = {"t": 0.0}

_PROMPT_EXTRACAO = (
    "Voce extrai fatos DURAVEIS e uteis sobre o USUARIO a partir da conversa: nome, gostos, projetos, rotina, "
    "preferencias e correcoes que ele fez. IGNORE perguntas, assuntos passageiros e dados sensiveis (senhas, documentos, "
    "saude, dinheiro, endereco). Responda SOMENTE JSON: {\"fatos\":[\"...\"]} com no maximo 3 itens, cada um curto "
    "(ate 100 caracteres), em terceira pessoa (ex.: \"Gosta de Oshi no Ko\"). Se nao houver nada, {\"fatos\":[]}.")


def extrair_em_segundo_plano(servico, mensagem_usuario, resposta):
    """Pede a um modelo pequeno os fatos novos, sem atrasar a resposta. Limita a frequência."""
    try:
        if len(mensagem_usuario or "") < 25 or not _SINAIS.search(mensagem_usuario):
            return
        if time.time() - _ultima_extracao["t"] < 90:
            return
        _ultima_extracao["t"] = time.time()
        threading.Thread(target=_extrair, args=(servico, mensagem_usuario, resposta), daemon=True).start()
    except Exception:
        pass


def _extrair(servico, mensagem_usuario, resposta):
    try:
        import requests
        conhecidos = "; ".join(relevantes(mensagem_usuario, 3))
        corpo = {"model": servico.MODELOS_RESERVA[0], "max_tokens": 180, "temperature": 0.1,
                 "messages": [{"role": "system", "content": _PROMPT_EXTRACAO},
                              {"role": "user", "content": f"Ja sabido: {conhecidos or 'nada'}\nUsuario: {mensagem_usuario[:300]}\n"
                                                          f"Spica: {(resposta or '')[:200]}"}]}
        r = requests.post(servico.URL, json=corpo, timeout=30,
                          headers={"Authorization": f"Bearer {servico.api_key}", "Content-Type": "application/json"})
        if r.status_code != 200:
            return
        txt = r.json()["choices"][0]["message"].get("content") or ""
        m = re.search(r"\{.*\}", txt, re.S)
        for fato in (json.loads(m.group(0)).get("fatos") or [])[:3] if m else []:
            adicionar_fato(str(fato))
    except Exception as e:
        print(f"[Spica/Memoria] extração: {e}")
