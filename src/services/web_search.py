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


def _busca_lite(query, max_resultados):
    """Fallback sem dependências nativas: página HTML 'lite' do DuckDuckGo."""
    import requests
    headers = {"User-Agent": "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 "
                             "(KHTML, like Gecko) Chrome/124.0 Mobile Safari/537.36"}
    with requests.Session() as sessao:   # fecha a conexão ao sair
        resp = sessao.post("https://lite.duckduckgo.com/lite/",
                           data={"q": query, "kl": REGIAO},
                           headers=headers, timeout=TIMEOUT)
    resp.raise_for_status()
    return _parse_lite(resp.text, max_resultados)


def _parse_lite(pagina, max_resultados):
    links = re.findall(
        r"<a[^>]*class=['\"]result-link['\"][^>]*>(.*?)</a>", pagina, re.S)
    hrefs = re.findall(
        r"<a[^>]*href=['\"]([^'\"]+)['\"][^>]*class=['\"]result-link['\"]", pagina)
    snippets = re.findall(
        r"<td[^>]*class=['\"]result-snippet['\"][^>]*>(.*?)</td>", pagina, re.S)
    saida = []
    for i, href in enumerate(hrefs[:max_resultados]):
        if href.startswith("//"):
            href = "https:" + href
        q = urllib.parse.parse_qs(urllib.parse.urlparse(href).query)
        if "uddg" in q:                       # desembrulha o redirecionamento do DDG
            href = q["uddg"][0]
        saida.append({
            "titulo": _limpar(links[i]) if i < len(links) else "",
            "link": href,
            "resumo": (_limpar(snippets[i]) if i < len(snippets) else "")[:MAX_CORPO],
        })
    return saida


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

        resultados, motor = [], "ddgs"
        if DDGS is not None:
            try:
                resultados = _busca_ddgs(query, max_resultados)
            except Exception as e:
                print(f"[Spica/Web] ddgs falhou ({type(e).__name__}: {e}) — tentando fallback")
        if not resultados:
            motor = "lite"
            resultados = _busca_lite(query, max_resultados)

        if not resultados:
            return json.dumps({"consulta": query, "resultados": [],
                               "aviso": "nenhum resultado encontrado"}, ensure_ascii=False)
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
