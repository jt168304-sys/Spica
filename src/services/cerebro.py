# cerebro.py — colaboração entre o Groq (escreve) e o Cloudflare (revisa) dentro da Spica.
# Cada chamada ao Cloudflare conta num limite diário local, para proteger a cota gratuita.
import datetime
import json
import os

import requests

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODELO = "openai/gpt-oss-120b"
CF_MODELO = "@cf/meta/llama-3.3-70b-instruct-fp8-fast"
CF_LIMITE_DIA = 15


def _cfg():
    from src.config.settings import Settings
    return Settings()


def _caminho_uso():
    base = os.environ.get("ANDROID_PRIVATE") or os.path.expanduser("~")
    return os.path.join(base, "cerebro_uso.json")


def _uso_hoje():
    hoje = datetime.date.today().isoformat()
    try:
        with open(_caminho_uso(), encoding="utf-8") as arq:
            dados = json.load(arq)
    except Exception:
        dados = {}
    if dados.get("dia") != hoje:
        dados = {"dia": hoje, "n": 0}
    return dados


def cf_disponivel():
    cfg = _cfg()
    if not (cfg.get("cf_account", "") or "").strip() or not (cfg.get("cf_token", "") or "").strip():
        return False
    return _uso_hoje()["n"] < CF_LIMITE_DIA


def _contar_cf():
    dados = _uso_hoje()
    dados["n"] += 1
    with open(_caminho_uso(), "w", encoding="utf-8") as arq:
        json.dump(dados, arq)


def _groq(mensagens, max_tokens=1500):
    chave = (_cfg().get("api_key", "") or "").strip()
    if not chave:
        raise RuntimeError("sem chave do Groq")
    r = requests.post(GROQ_URL,
                      json={"model": GROQ_MODELO, "messages": mensagens,
                            "max_tokens": max_tokens, "temperature": 0.3},
                      headers={"Authorization": f"Bearer {chave}", "Content-Type": "application/json"},
                      timeout=120)
    if r.status_code != 200:
        raise RuntimeError(f"Groq HTTP {r.status_code}")
    return (r.json()["choices"][0]["message"].get("content") or "").strip()


def _cf(mensagens, max_tokens=800):
    cfg = _cfg()
    conta = (cfg.get("cf_account", "") or "").strip()
    token = (cfg.get("cf_token", "") or "").strip()
    if not conta or not token:
        raise RuntimeError("Cloudflare não configurado")
    if _uso_hoje()["n"] >= CF_LIMITE_DIA:
        raise RuntimeError("limite diário do Cloudflare atingido")
    _contar_cf()
    url = f"https://api.cloudflare.com/client/v4/accounts/{conta}/ai/v1/chat/completions"
    r = requests.post(url,
                      json={"model": CF_MODELO, "messages": mensagens, "max_tokens": max_tokens},
                      headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                      timeout=120)
    if r.status_code != 200:
        raise RuntimeError(f"Cloudflare HTTP {r.status_code}")
    return (r.json()["choices"][0]["message"].get("content") or "").strip()


def refinar_prompt_imagem(pedido, prompt_en):
    """O Cloudflare revisa o prompt de imagem (em inglês). Se algo falhar, devolve o prompt original."""
    if not cf_disponivel():
        return prompt_en
    try:
        novo = _cf([
            {"role": "system", "content": "Você revisa prompts de imagem em inglês. Responda só com o prompt final, em inglês, sem explicações."},
            {"role": "user", "content": (f"Pedido original (português): {pedido}\n"
                                         f"Prompt atual: {prompt_en}\n"
                                         "Regras: não inclua pessoas se o pedido não citou pessoas; não inclua "
                                         "estilo anime ou mangá se o pedido não citou anime ou mangá; mantenha "
                                         "todos os elementos pedidos.")},
        ], max_tokens=300)
        if 10 < len(novo) < 1800:
            return novo
    except Exception as e:
        print(f"[Spica/Cerebro] revisão de imagem: {e}")
    return prompt_en


import re as _re

REVISOR = (
    "Você é um revisor exigente. Analise o texto em relação ao pedido e responda EXATAMENTE neste formato:\n"
    "VEREDITO: APROVADO ou REPROVADO\n"
    "FALHAS:\n- itens que não atendem ao pedido, estão incompletos, resumidos ou mal organizados (vazio se nenhum)\n"
    "FATOS_A_CONFIRMAR:\n- afirmações específicas (datas, números, nomes, lançamentos, recursos) que o texto não sustenta "
    "com o próprio pedido (vazio se nenhuma)\n"
    "MELHORIAS:\n- pelo menos 2 sugestões concretas para o Groq aplicar (estrutura, profundidade, clareza, exemplos, ordem)\n"
    "Regras: REPROVADO se houver qualquer falha ou fato a confirmar. Não reescreva o texto. Não elogie."
)

GROQ_SISTEMA = (
    "Você escreve textos completos e detalhados, em parágrafos reais, sem resumir. Não invente datas, números, nomes, "
    "lançamentos nem recursos: se algo não for certo, escreva [a confirmar]. Não use markdown (sem #, sem **, sem ---)."
)


def _log(msg):
    try:
        from src.utils.service_log import slog
        slog(f"[Spica/Cerebro] {msg}")
    except Exception:
        print(f"[Spica/Cerebro] {msg}")


def _revisar(pedido, texto):
    return _cf([
        {"role": "system", "content": REVISOR},
        {"role": "user", "content": f"Pedido: {pedido}\n\nTexto:\n{texto}"},
    ], max_tokens=700)


def _secao(rev, nome):
    m = _re.search(nome + r":\s*\n((?:\s*-.*\n?)*)", rev or "", _re.I)
    return [l.strip()[1:].strip() for l in (m.group(1).splitlines() if m else []) if l.strip().startswith("-") and l.strip()[1:].strip()]


def _problemas(rev):
    """Lista de falhas e fatos a confirmar. Vazia só se o revisor não apontou nada."""
    return _secao(rev, "FALHAS") + _secao(rev, "FATOS_A_CONFIRMAR")


def _melhorias(rev):
    return _secao(rev, "MELHORIAS")


def colaborar_texto(pedido):
    """O Groq escreve; o Cloudflare revisa com rigor e sempre traz melhorias; o Groq aplica as melhorias; o Cloudflare
    revisa de novo. Só sai como aprovado se a segunda revisão não apontar falhas nem fatos a confirmar.
    Devolve (texto, relatório)."""
    rascunho = _groq([
        {"role": "system", "content": GROQ_SISTEMA},
        {"role": "user", "content": pedido},
    ], max_tokens=2500)
    if not rascunho:
        raise RuntimeError("o Groq não devolveu texto")
    if not cf_disponivel():
        _log("revisão pulada: Cloudflare sem limite hoje ou não configurado")
        return rascunho, "revisão pulada (Cloudflare sem limite hoje ou não configurado)"
    try:
        rev1 = _revisar(pedido, rascunho)
    except Exception as e:
        _log(f"revisão indisponível: {e}")
        return rascunho, f"revisão indisponível ({e})"
    _log(f"revisão 1: falhas/fatos={len(_problemas(rev1))} melhorias={len(_melhorias(rev1))}")
    plano = "\n".join(["Falhas e fatos a corrigir:"] + ["- " + p for p in _problemas(rev1)]
                      + ["Melhorias a aplicar:"] + ["- " + m for m in _melhorias(rev1)])
    try:
        corrigido = _groq([
            {"role": "system", "content": (
                "Você reescreve o texto aplicando a revisão. Obrigatório: 1) corrija todas as falhas; 2) aplique todas as "
                "melhorias; 3) para cada fato a confirmar, remova-o ou escreva [a confirmar]; 4) não invente nada; "
                "5) sem markdown; parágrafos separados por linha em branco. Devolva só o texto final.")},
            {"role": "user", "content": f"Pedido: {pedido}\n\nTexto:\n{rascunho}\n\n{plano}"},
        ], max_tokens=2500) or rascunho
    except Exception as e:
        _log(f"correção falhou: {e}")
        return rascunho, f"NÃO REVISADO: a correção falhou ({e}); usei o rascunho"
    if not cf_disponivel():
        _log("corrigido, mas sem nova revisão (limite do Cloudflare)")
        return corrigido, "corrigido, mas sem nova revisão (limite do Cloudflare)"
    try:
        rev2 = _revisar(pedido, corrigido)
    except Exception as e:
        _log(f"segunda revisão falhou: {e}")
        return corrigido, f"corrigido; a 2ª revisão falhou ({e})"
    pend = _problemas(rev2)
    if not pend:
        _log("aprovado na 2ª revisão")
        return corrigido, f"aprovado na 2ª revisão do Cloudflare ({len(_melhorias(rev1))} melhorias aplicadas)"
    _log(f"NÃO APROVADO na 2ª revisão: {len(pend)} pendência(s)")
    return corrigido, "NÃO APROVADO pela revisão do Cloudflare. Pendências: " + "; ".join(pend)[:400]
