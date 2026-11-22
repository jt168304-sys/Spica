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


def colaborar_texto(pedido):
    """O Groq escreve o texto completo; o Cloudflare revisa; se reprovar, o Groq corrige uma vez.
    Devolve (texto, relatório curto)."""
    rascunho = _groq([
        {"role": "system", "content": "Você escreve textos completos e detalhados, em parágrafos reais, sem resumir e sem deixar tudo numa linha só."},
        {"role": "user", "content": pedido},
    ], max_tokens=2500)
    if not rascunho:
        raise RuntimeError("o Groq não devolveu texto")
    if not cf_disponivel():
        return rascunho, "revisão pulada (Cloudflare sem limite hoje ou não configurado)"
    try:
        revisao = _cf([
            {"role": "system", "content": "Você revisa um texto escrito por outro modelo. Responda APROVADO se o texto estiver completo e correto para o pedido. Caso contrário, liste no máximo 5 pontos do que falta ou está errado."},
            {"role": "user", "content": f"Pedido: {pedido}\n\nTexto:\n{rascunho}"},
        ], max_tokens=400)
    except Exception as e:
        return rascunho, f"revisão indisponível ({e})"
    if revisao.upper().startswith("APROVADO"):
        return rascunho, "aprovado pela revisão do Cloudflare"
    try:
        corrigido = _groq([
            {"role": "system", "content": "Você corrige um texto seguindo a revisão. Devolva o texto completo, sem comentários."},
            {"role": "user", "content": f"Pedido: {pedido}\n\nTexto:\n{rascunho}\n\nRevisão:\n{revisao}"},
        ], max_tokens=2500)
        return (corrigido or rascunho), "corrigido após a revisão do Cloudflare"
    except Exception as e:
        return rascunho, f"correção falhou ({e}); usei o rascunho"
