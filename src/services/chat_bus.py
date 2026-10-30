# chat_bus.py — Fila de mensagens da escuta contínua até o chat.
# O loop de voz não tem acesso à lista de mensagens da tela; ele escreve aqui (arquivo JSON por linha,
# na pasta privada do app) e o chat lê a cada segundo. Funciona mesmo entre processos.
import json
import os
import re

_RE_IMG = re.compile(r"\n?\[IMAGEM:([^\]]+)\]")


def _arquivo():
    base = os.environ.get("ANDROID_PRIVATE") or os.path.expanduser("~")
    os.makedirs(base, exist_ok=True)
    return os.path.join(base, "chat_pendente.jsonl")


def separar(texto):
    """Tira os marcadores [IMAGEM:caminho] do texto. Devolve (texto_limpo, [caminhos existentes])."""
    imagens = [m for m in _RE_IMG.findall(texto or "") if os.path.exists(m)]
    return _RE_IMG.sub("", texto or "").strip(), imagens


def publicar(tipo, texto="", imagens=()):
    """tipo: 'usuario' ou 'spica'. Nunca levanta exceção."""
    try:
        with open(_arquivo(), "a", encoding="utf-8") as arq:
            arq.write(json.dumps({"tipo": tipo, "texto": texto or "", "imagens": list(imagens or [])},
                                 ensure_ascii=False) + "\n")
    except Exception as e:
        print(f"[Spica/ChatBus] publicar: {e}")


def ler_pendentes():
    """Devolve as mensagens pendentes e esvazia a fila."""
    try:
        caminho = _arquivo()
        if not os.path.exists(caminho) or os.path.getsize(caminho) == 0:
            return []
        with open(caminho, "r+", encoding="utf-8") as arq:
            linhas = arq.read().splitlines()
            arq.seek(0)
            arq.truncate()
        saida = []
        for linha in linhas:
            try:
                saida.append(json.loads(linha))
            except Exception:
                pass
        return saida
    except Exception as e:
        print(f"[Spica/ChatBus] ler: {e}")
        return []
