# web_search.py — Busca web (DuckDuckGo) como "Tool" para o Groq (Tool Calling)
#
# - Usa `with DDGS() as ddgs:` + `ddgs.text(query, max_results=...)` (pacote `ddgs`,
#   novo nome do `duckduckgo-search`; os dois funcionam com este código).
# - Campos do resultado: title / href / body  (NÃO existe 'url').
# - Se o pacote não existir (caso do APK: o p4a não compila as dependências
#   nativas do ddgs), cai automaticamente para uma busca só com `requests`.
# - NUNCA lança exceção: sempre devolve um JSON (string) para o modelo.
import json
import re
import html
import urllib.parse

try:
    from ddgs import DDGS                      # pacote novo
except Exception:
    try:
        from duckduckgo_search import DDGS     # pacote antigo (renomeado)
    except Exception:
        DDGS = None

REGIAO = "br-pt"
TIMEOUT = 10
MAX_CORPO = 400  # corta cada resumo p/ não estourar tokens


def _limpar(txt):
    txt = re.sub(r"<[^>]+>", "", txt or "")
    return re.sub(r"\s+", " ", html.unescape(txt)).strip()


def _busca_ddgs(query, max_resultados):
    """Caminho principal: biblioteca ddgs, com gerenciador de contexto."""
    with DDGS(timeout=TIMEOUT) as ddgs:
        brutos = ddgs.text(query, region=REGIAO, max_results=max_resultados) or []
    saida = []
    for res in brutos:
        link = res.get("href") or res.get("url") or ""   # 'href' é o correto; 'url' só por segurança
        if not link:
            continue
        saida.append({
            "titulo": _limpar(res.get("title")),
            "link": link,
            "resumo": _limpar(res.get("body"))[:MAX_CORPO],
        })
    return saida


def _atributo(attrs, nome):
    m = re.search(r"(?<![\w-])" + nome + r"=['\"]([^'\"]*)['\"]", attrs)
    return m.group(1) if m else ""


def _desembrulhar(href):
    """Os links do DDG vêm como //duckduckgo.com/l/?uddg=<url real>."""
    if href.startswith("//"):
        href = "https:" + href
    q = urllib.parse.parse_qs(urllib.parse.urlparse(href).query)
    return q["uddg"][0] if "uddg" in q else href


def _links_com_classe(pagina, classe):
    """[(href, texto)] dos <a> cuja classe contém `classe` (ordem dos atributos tanto faz)."""
    achados = []
    for m in re.finditer(r"<a\b([^>]*)>(.*?)</a>", pagina, re.S | re.I):
        attrs, interno = m.group(1), m.group(2)
        if classe in _atributo(attrs, "class"):
            achados.append((_atributo(attrs, "href"), _limpar(interno)))
    return achados


def _snippets_com_classe(pagina, classe):
    padrao = (r"<(?:a|td|div)\b[^>]*class=['\"][^'\"]*" + classe +
              r"[^'\"]*['\"][^>]*>(.*?)</(?:a|td|div)>")
    return [_limpar(x) for x in re.findall(padrao, pagina, re.S | re.I)]


def _montar(links, snippets, max_resultados):
    saida = []
    for i, (href, titulo) in enumerate(links[:max_resultados]):
        if not href:
            continue
        saida.append({
            "titulo": titulo,
            "link": _desembrulhar(href),
            "resumo": (snippets[i] if i < len(snippets) else "")[:MAX_CORPO],
        })
    return saida


def _parse_lite(pagina, max_resultados):
    return _montar(_links_com_classe(pagina, "result-link"),
                   _snippets_com_classe(pagina, "result-snippet"), max_resultados)


def _parse_html(pagina, max_resultados):
    return _montar(_links_com_classe(pagina, "result__a"),
                   _snippets_com_classe(pagina, "result__snippet"), max_resultados)


def _busca_http(query, max_resultados):
    """Fallback sem dependências nativas. Tenta a página 'lite' e depois a 'html'.
    Devolve (resultados, motor, motivo_se_vazio)."""
    import requests
    headers = {"User-Agent": "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 "
                             "(KHTML, like Gecko) Chrome/124.0 Mobile Safari/537.36"}
    motivo = "nenhum resultado encontrado"
    with requests.Session() as sessao:   # fecha a conexão ao sair
        for motor, url, parser in (("lite", "https://lite.duckduckgo.com/lite/", _parse_lite),
                                   ("html", "https://html.duckduckgo.com/html/", _parse_html)):
            try:
                resp = sessao.post(url, data={"q": query, "kl": REGIAO},
                                   headers=headers, timeout=TIMEOUT)
                resp.raise_for_status()
            except Exception as e:
                motivo = f"{motor}: {type(e).__name__}"
                continue
            resultados = parser(resp.text, max_resultados)
            if resultados:
                return resultados, motor, ""
            baixo = resp.text.lower()
            if "anomaly" in baixo or "captcha" in baixo or "challenge" in baixo:
                motivo = f"{motor}: bloqueio anti-robô do DuckDuckGo"
            else:
                motivo = f"{motor}: página sem resultados"
    return [], "http", motivo


def buscar_web(query, max_resultados=5):
    """Função-ferramenta. Devolve SEMPRE uma string JSON (exigência do role 'tool')."""
    try:
        query = (query or "").strip()
        if not query:
            return json.dumps({"erro": "consulta vazia"}, ensure_ascii=False)
        try:
            max_resultados = max(1, min(int(max_resultados), 8))
        except (TypeError, ValueError):
            max_resultados = 5

        resultados, motor, motivo = [], "ddgs", "nenhum resultado encontrado"
        if DDGS is not None:
            try:
                resultados = _busca_ddgs(query, max_resultados)
            except Exception as e:
                print(f"[Spica/Web] ddgs falhou ({type(e).__name__}: {e}) — tentando fallback")
        if not resultados:
            resultados, motor, motivo = _busca_http(query, max_resultados)

        if not resultados:
            return json.dumps({"consulta": query, "resultados": [], "aviso": motivo},
                              ensure_ascii=False)
        return json.dumps({"consulta": query, "motor": motor, "resultados": resultados},
                          ensure_ascii=False)
    except Exception as e:  # rede, timeout, rate limit, parsing... nada derruba o assistente
        print(f"[Spica/Web] erro na busca: {type(e).__name__}: {e}")
        return json.dumps({"erro": f"falha na busca web: {type(e).__name__}: {e}"},
                          ensure_ascii=False)


# ---------- Declaração da ferramenta (formato Chat Completions do Groq/OpenAI) ----------
FERRAMENTAS_GROQ = [
    {
        "type": "function",
        "function": {
            "name": "buscar_web",
            "description": ("Pesquisa na internet (DuckDuckGo). Use para notícias, fatos "
                            "recentes, preços, placares, clima e qualquer coisa que possa "
                            "ter mudado. NÃO use para data/hora nem para conversa casual."),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string",
                              "description": "Termos da busca, curtos e objetivos."},
                    "max_resultados": {"type": "integer", "minimum": 1, "maximum": 8,
                                       "description": "Quantidade de resultados (padrão 5)."},
                },
                "required": ["query"],
            },
        },
    }
]

_FUNCOES = {"buscar_web": buscar_web}


def executar_ferramenta(nome, argumentos_json):
    funcao = _FUNCOES.get(nome)
    if funcao is None:
        return json.dumps({"erro": f"ferramenta desconhecida: {nome}"}, ensure_ascii=False)
    try:
        args = json.loads(argumentos_json or "{}")
        if not isinstance(args, dict):
            raise ValueError("argumentos não são um objeto JSON")
    except Exception as e:
        return json.dumps({"erro": f"argumentos inválidos: {e}"}, ensure_ascii=False)
    try:
        return funcao(**args)
    except TypeError as e:
        return json.dumps({"erro": f"parâmetros incorretos: {e}"}, ensure_ascii=False)


# ---------- Loop de Tool Calling com o Groq (via requests) ----------
def perguntar_com_busca(mensagens, api_key, modelo="openai/gpt-oss-120b",
                        max_rodadas=3, timeout=40):
    """`mensagens` = lista [{'role':..., 'content':...}]. Devolve o texto final."""
    import requests
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    msgs = list(mensagens)

    for rodada in range(max_rodadas + 1):
        corpo = {"model": modelo, "messages": msgs}
        if rodada < max_rodadas:                  # na última rodada força a resposta final
            corpo["tools"] = FERRAMENTAS_GROQ
            corpo["tool_choice"] = "auto"
        resp = requests.post(url, headers=headers, json=corpo, timeout=timeout)
        resp.raise_for_status()
        msg = resp.json()["choices"][0]["message"]
        chamadas = msg.get("tool_calls")
        if not chamadas:
            return (msg.get("content") or "").strip()

        # 1) devolve a mensagem do assistente com os tool_calls; 2) uma msg 'tool' por chamada
        msgs.append({"role": "assistant", "content": msg.get("content") or "",
                     "tool_calls": chamadas})
        for c in chamadas:
            resultado = executar_ferramenta(c["function"]["name"],
                                            c["function"].get("arguments"))
            msgs.append({"role": "tool", "tool_call_id": c["id"],
                         "name": c["function"]["name"], "content": resultado})
    return ""
