# ferramentas.py — Caixa de ferramentas da Spica (Tool Calling do Groq)
# Ferramentas: buscar_web, ler_pagina, clima, calcular.
# Regra de ouro: NENHUMA ferramenta lança exceção — sempre devolve um JSON (string).
import ast
import base64
import html
import ipaddress
import json
import math
import operator
import os
import random
import re
import time
import urllib.parse

from src.services.web_search import buscar_web

TIMEOUT = 10
MAX_PAGINA = 3500          # caracteres de texto devolvidos por página
MAX_BYTES_PAGINA = 600_000  # não baixa páginas gigantes
UA = ("Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Mobile Safari/537.36")


def _json(obj):
    return json.dumps(obj, ensure_ascii=False)


# ------------------------------------------------------------------ ler_pagina
_RE_LIXO = re.compile(r"<(script|style|noscript|svg|nav|header|footer|aside|form|iframe)\b.*?</\1>",
                      re.S | re.I)
_RE_COMENTARIO = re.compile(r"<!--.*?-->", re.S)
_RE_BLOCO = re.compile(r"</?(p|div|br|li|ul|ol|h[1-6]|tr|table|section|article|blockquote)\b[^>]*>", re.I)
_RE_TAG = re.compile(r"<[^>]+>")
_RE_TITULO = re.compile(r"<title[^>]*>(.*?)</title>", re.S | re.I)
_RE_PRINCIPAL = re.compile(r"<(main|article)\b.*?</\1>", re.S | re.I)


def _url_permitida(url):
    p = urllib.parse.urlparse(url)
    if p.scheme not in ("http", "https") or not p.hostname:
        return False
    host = p.hostname.lower()
    if host == "localhost" or host.endswith((".local", ".internal")):
        return False
    try:
        ip = ipaddress.ip_address(host)
        return not (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved)
    except ValueError:
        return True  # nome de domínio normal


def _html_para_texto(pagina):
    titulo = ""
    m = _RE_TITULO.search(pagina)
    if m:
        titulo = re.sub(r"\s+", " ", html.unescape(_RE_TAG.sub("", m.group(1)))).strip()
    pagina = _RE_COMENTARIO.sub("", pagina)
    pagina = _RE_LIXO.sub("", pagina)
    blocos = [b.group(0) for b in _RE_PRINCIPAL.finditer(pagina)]
    if blocos:
        pagina = max(blocos, key=len)       # prefere o <main>/<article> mais longo
    pagina = _RE_BLOCO.sub("\n", pagina)
    texto = html.unescape(_RE_TAG.sub("", pagina))
    linhas = [re.sub(r"[ \t\r\f\v]+", " ", l).strip() for l in texto.split("\n")]
    linhas = [l for l in linhas if len(l) > 1]
    return titulo, "\n".join(linhas)


def ler_pagina(url):
    try:
        import requests
        url = (url or "").strip()
        if not _url_permitida(url):
            return _json({"erro": "URL inválida ou não permitida (use http/https público)"})
        with requests.get(url, headers={"User-Agent": UA, "Accept-Language": "pt-BR,pt;q=0.9"},
                          timeout=TIMEOUT, stream=True) as resp:
            resp.raise_for_status()
            tipo = (resp.headers.get("Content-Type") or "").lower()
            if tipo and "html" not in tipo and "text" not in tipo:
                return _json({"erro": f"conteúdo não é texto/HTML ({tipo.split(';')[0]})"})
            dados = b""
            for pedaco in resp.iter_content(65536):
                dados += pedaco
                if len(dados) >= MAX_BYTES_PAGINA:
                    break
            codificacao = resp.encoding or "utf-8"
            url_final = resp.url
        titulo, texto = _html_para_texto(dados.decode(codificacao, errors="replace"))
        if not texto:
            return _json({"erro": "não consegui extrair texto dessa página"})
        truncado = len(texto) > MAX_PAGINA
        return _json({"url": url_final, "titulo": titulo, "conteudo": texto[:MAX_PAGINA],
                      "truncado": truncado})
    except Exception as e:
        return _json({"erro": f"falha ao ler a página: {type(e).__name__}: {e}"})


# ----------------------------------------------------------------------- clima
_WMO = {
    0: "céu limpo", 1: "predominantemente limpo", 2: "parcialmente nublado", 3: "nublado",
    45: "neblina", 48: "neblina com geada", 51: "garoa fraca", 53: "garoa moderada",
    55: "garoa forte", 56: "garoa congelante", 57: "garoa congelante forte",
    61: "chuva fraca", 63: "chuva moderada", 65: "chuva forte", 66: "chuva congelante",
    67: "chuva congelante forte", 71: "neve fraca", 73: "neve moderada", 75: "neve forte",
    77: "grãos de neve", 80: "pancadas de chuva fracas", 81: "pancadas de chuva moderadas",
    82: "pancadas de chuva fortes", 85: "pancadas de neve fracas", 86: "pancadas de neve fortes",
    95: "trovoada", 96: "trovoada com granizo", 99: "trovoada com granizo forte",
}


def clima(cidade):
    try:
        import requests
        cidade = (cidade or "").strip()
        if not cidade:
            return _json({"erro": "informe a cidade"})
        geo = requests.get("https://geocoding-api.open-meteo.com/v1/search",
                           params={"name": cidade, "count": 1, "language": "pt", "format": "json"},
                           timeout=TIMEOUT)
        geo.raise_for_status()
        achados = geo.json().get("results") or []
        if not achados:
            return _json({"erro": f"cidade não encontrada: {cidade}"})
        local = achados[0]
        prev = requests.get("https://api.open-meteo.com/v1/forecast", params={
            "latitude": local["latitude"], "longitude": local["longitude"],
            "current": "temperature_2m,apparent_temperature,relative_humidity_2m,precipitation,weather_code,wind_speed_10m",
            "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max",
            "timezone": "auto", "forecast_days": 3}, timeout=TIMEOUT)
        prev.raise_for_status()
        d = prev.json()
        c, dia = d.get("current", {}), d.get("daily", {})
        agora = {
            "temperatura_c": c.get("temperature_2m"),
            "sensacao_c": c.get("apparent_temperature"),
            "umidade_pct": c.get("relative_humidity_2m"),
            "chuva_mm": c.get("precipitation"),
            "vento_kmh": c.get("wind_speed_10m"),
            "condicao": _WMO.get(c.get("weather_code"), "desconhecida"),
        }
        proximos = []
        for i, data in enumerate(dia.get("time", [])):
            proximos.append({
                "data": data,
                "min_c": dia["temperature_2m_min"][i],
                "max_c": dia["temperature_2m_max"][i],
                "chance_chuva_pct": dia["precipitation_probability_max"][i],
                "condicao": _WMO.get(dia["weather_code"][i], "desconhecida"),
            })
        nome = ", ".join(x for x in (local.get("name"), local.get("admin1"), local.get("country")) if x)
        return _json({"local": nome, "agora": agora, "proximos_dias": proximos})
    except Exception as e:
        return _json({"erro": f"falha ao consultar o clima: {type(e).__name__}: {e}"})


# --------------------------------------------------------------------- calcular
_OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
        ast.Div: operator.truediv, ast.FloorDiv: operator.floordiv, ast.Mod: operator.mod,
        ast.Pow: operator.pow, ast.USub: operator.neg, ast.UAdd: operator.pos}
_FUNCS = {"sqrt": math.sqrt, "sin": math.sin, "cos": math.cos, "tan": math.tan,
          "log": math.log, "log10": math.log10, "exp": math.exp, "abs": abs,
          "round": round, "min": min, "max": max, "floor": math.floor, "ceil": math.ceil}
_CONSTS = {"pi": math.pi, "e": math.e}


def _avaliar(no):
    if isinstance(no, ast.Expression):
        return _avaliar(no.body)
    if isinstance(no, ast.Constant) and isinstance(no.value, (int, float)) and not isinstance(no.value, bool):
        return no.value
    if isinstance(no, ast.Name) and no.id in _CONSTS:
        return _CONSTS[no.id]
    if isinstance(no, ast.BinOp) and type(no.op) in _OPS:
        a, b = _avaliar(no.left), _avaliar(no.right)
        if isinstance(no.op, ast.Pow) and abs(b) > 1000:
            raise ValueError("expoente grande demais")
        return _OPS[type(no.op)](a, b)
    if isinstance(no, ast.UnaryOp) and type(no.op) in _OPS:
        return _OPS[type(no.op)](_avaliar(no.operand))
    if isinstance(no, ast.Call) and isinstance(no.func, ast.Name) and no.func.id in _FUNCS and not no.keywords:
        return _FUNCS[no.func.id](*[_avaliar(a) for a in no.args])
    raise ValueError("expressão não permitida")


def calcular(expressao):
    try:
        expr = (expressao or "").strip().replace("^", "**").replace("×", "*").replace("÷", "/")
        if not expr or len(expr) > 200:
            return _json({"erro": "expressão vazia ou longa demais"})
        valor = _avaliar(ast.parse(expr, mode="eval"))
        if isinstance(valor, float):
            if math.isnan(valor) or math.isinf(valor):
                return _json({"erro": "resultado indefinido"})
            valor = round(valor, 10)
        return _json({"expressao": expr, "resultado": valor})
    except ZeroDivisionError:
        return _json({"erro": "divisão por zero"})
    except Exception as e:
        return _json({"erro": f"não consegui calcular: {e}"})


# ------------------------------------------------------------------ gerar_imagem
_IMAGENS = []          # caminhos das imagens criadas na conversa atual (o chat as mostra)


def pegar_imagens_geradas():
    """Devolve (e esvazia) a lista de imagens criadas desde a última chamada."""
    itens = list(_IMAGENS)
    del _IMAGENS[:]
    return itens


def _pasta_imagens():
    base = os.environ.get("ANDROID_PRIVATE") or os.path.expanduser("~")
    pasta = os.path.join(base, "imagens")
    os.makedirs(pasta, exist_ok=True)
    return pasta


def _imagem_cloudflare(prompt):
    """FLUX.1 schnell no Cloudflare Workers AI (cota diária grátis). Devolve (bytes, erro)."""
    try:
        from src.config.settings import Settings
        cfg = Settings()
        conta = (cfg.get("cf_account", "") or "").strip()
        token = (cfg.get("cf_token", "") or "").strip()
    except Exception as e:
        return None, f"configuração: {e}"
    if not conta or not token:
        return None, "Cloudflare não configurado"
    import requests
    url = f"https://api.cloudflare.com/client/v4/accounts/{conta}/ai/run/@cf/black-forest-labs/flux-1-schnell"
    r = requests.post(url, headers={"Authorization": f"Bearer {token}"},
                      json={"prompt": prompt, "steps": 8, "seed": random.randint(1, 2**31 - 1)}, timeout=90)
    if r.status_code != 200:
        return None, f"Cloudflare HTTP {r.status_code}: {r.text[:140]}"
    dados = (r.json().get("result") or {}).get("image")
    if not dados:
        return None, "Cloudflare respondeu sem imagem"
    return base64.b64decode(dados), ""


def _imagem_pollinations(prompt):
    """Reserva grátis e sem chave (qualidade menor, com marca d'água)."""
    import requests
    url = ("https://image.pollinations.ai/prompt/" + urllib.parse.quote(prompt) +
           f"?width=768&height=768&model=flux&nologo=true&seed={random.randint(1, 99999)}")
    r = requests.get(url, headers={"User-Agent": UA}, timeout=90)
    tipo = (r.headers.get("Content-Type") or "").lower()
    if r.status_code != 200 or "image" not in tipo or len(r.content) < 5000:
        return None, f"Pollinations HTTP {r.status_code}"
    return r.content, ""


_PADROES_ARTE = {
    "padrao": {"estilo": "anime", "enquadramento": "meio corpo", "fundo": "simple soft background, uncluttered"},
    "qualidade": "masterpiece, best quality, highly detailed, sharp focus",
    "anatomia": "anatomically correct, two arms, five fingers on each hand",
    "estilos": {"anime": {"palavras": ["anime"], "tags": "modern anime illustration, clean line art, cel shading, vibrant colors"}},
    "enquadramentos": {"meio corpo": {"palavras": ["meio corpo"], "tags": "waist-up shot, both arms visible"}},
}


def _guia_arte():
    """Carrega assets/conhecimento/arte_anime.json (editável); se faltar, usa o padrão embutido."""
    try:
        caminho = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..",
                               "assets", "conhecimento", "arte_anime.json")
        with open(os.path.normpath(caminho), encoding="utf-8") as arq:
            dados = json.load(arq)
        guia = dict(_PADROES_ARTE)
        guia.update({k: v for k, v in dados.items() if not k.startswith("_")})
        return guia
    except Exception:
        return _PADROES_ARTE


def _escolher(tabela, texto, padrao):
    """Acha o item cujas palavras aparecem no texto; senão usa o padrão."""
    texto = (texto or "").lower()
    for nome, item in tabela.items():
        if any(p.lower() in texto for p in item.get("palavras", [])):
            return nome, item.get("tags", "")
    item = tabela.get(padrao) or next(iter(tabela.values()))
    return padrao, item.get("tags", "")


def montar_prompt_arte(assunto, acao="", enquadramento="", estilo="", luz="", fundo=""):
    """Monta o prompt final (em inglês) com o guia de arte: assunto primeiro, depois pose,
    enquadramento, luz, fundo, estilo, qualidade e anatomia."""
    guia = _guia_arte()
    pad = guia.get("padrao", {})
    _, tags_estilo = _escolher(guia["estilos"], estilo, pad.get("estilo", "anime"))
    _, tags_enq = _escolher(guia["enquadramentos"], enquadramento, pad.get("enquadramento", "meio corpo"))
    partes = [assunto.strip(), (acao or "").strip(), tags_enq, (luz or "").strip(),
              (fundo or "").strip() or pad.get("fundo", ""), tags_estilo,
              guia.get("qualidade", ""), guia.get("anatomia", "")]
    return ", ".join(x.strip(" ,") for x in partes if x and x.strip(" ,"))[:1800]


def gerar_imagem(assunto=None, acao=None, enquadramento=None, estilo=None, luz=None,
                 fundo=None, variacoes=1, descricao=None, **_ignorados):
    try:
        base_texto = (assunto or descricao or "").strip()
        if not base_texto:
            return _json({"erro": "faltou descrever o que desenhar"})
        prompt = montar_prompt_arte(base_texto, acao or "", enquadramento or "", estilo or "",
                                    luz or "", fundo or "")
        try:
            quantidade = max(1, min(int(variacoes), 2))
        except (TypeError, ValueError):
            quantidade = 1
        feitas, motor, falhas = 0, "", []
        for n in range(quantidade):
            dados, erro = None, ""
            for nome, funcao in (("cloudflare", _imagem_cloudflare), ("pollinations", _imagem_pollinations)):
                try:
                    dados, erro = funcao(prompt)
                except Exception as e:
                    dados, erro = None, f"{type(e).__name__}: {e}"
                if dados:
                    motor = nome
                    break
                falhas.append(f"{nome}: {erro}")
            if not dados:
                break
            caminho = os.path.join(_pasta_imagens(), time.strftime("spica_%Y%m%d_%H%M%S") + f"_{n + 1}.jpg")
            with open(caminho, "wb") as arq:
                arq.write(dados)
            _IMAGENS.append(caminho)
            feitas += 1
        if feitas == 0:
            return _json({"erro": "não consegui gerar a imagem agora", "detalhes": falhas[:4]})
        aviso = ("Imagem(ns) criada(s) e já aparece(m) no chat; comente em uma frase curta."
                 if motor == "cloudflare" else
                 "Criada pela reserva (qualidade menor, com marca d'água); já aparece no chat.")
        return _json({"ok": True, "quantidade": feitas, "motor": motor, "aviso": aviso})
    except Exception as e:
        return _json({"erro": f"falha ao gerar imagem: {type(e).__name__}: {e}"})


# ------------------------------------------------------------- consultar_anime (AniList)
_ANILIST = "https://graphql.anilist.co"
_Q_MIDIA = """query ($busca: String, $tipo: MediaType) {
  Media(search: $busca, type: $tipo, isAdult: false) {
    title { romaji english native } format status episodes chapters volumes
    season seasonYear startDate { year month day } endDate { year month day }
    averageScore popularity genres studios(isMain: true) { nodes { name } }
    nextAiringEpisode { episode airingAt } description(asHtml: false) siteUrl
  }
}"""
_Q_PERSONAGEM = """query ($busca: String) {
  Character(search: $busca) {
    name { full native } gender age description(asHtml: false) siteUrl
    media(perPage: 3, sort: POPULARITY_DESC) { nodes { title { romaji english } type } }
  }
}"""
_Q_TEMPORADA = """query ($season: MediaSeason, $ano: Int) {
  Page(perPage: 10) {
    media(season: $season, seasonYear: $ano, type: ANIME, sort: POPULARITY_DESC, isAdult: false) {
      title { romaji english } format episodes status averageScore
      nextAiringEpisode { episode airingAt }
    }
  }
}"""


def _anilist(consulta, variaveis):
    import requests
    r = requests.post(_ANILIST, json={"query": consulta, "variables": variaveis},
                      headers={"Content-Type": "application/json", "Accept": "application/json"}, timeout=15)
    if r.status_code == 404:
        return None                      # AniList usa 404 quando não acha nada
    r.raise_for_status()
    return r.json().get("data")


def _limpar_descricao(txt, limite=420):
    txt = re.sub(r"~!.*?!~", "", txt or "", flags=re.S)       # tira spoilers
    txt = re.sub(r"<br\s*/?>", " ", txt)
    txt = html.unescape(re.sub(r"<[^>]+>", "", txt))
    return re.sub(r"\s+", " ", txt).strip()[:limite]


def _data(d):
    if not d or not d.get("year"):
        return ""
    return "-".join(f"{int(v):02d}" if k != "year" else str(v) for k, v in
                    (("year", d.get("year")), ("month", d.get("month")), ("day", d.get("day"))) if v)


def _proximo(ep):
    if not ep or not ep.get("airingAt"):
        return None
    dias = (ep["airingAt"] - time.time()) / 86400
    return {"episodio": ep.get("episode"), "quando": time.strftime("%d/%m %H:%M", time.localtime(ep["airingAt"])),
            "em_dias": round(dias, 1)}


def _titulo(t):
    t = t or {}
    return t.get("english") or t.get("romaji") or t.get("native") or "?"


_TEMPORADAS = (("inverno", "WINTER"), ("winter", "WINTER"), ("primavera", "SPRING"), ("spring", "SPRING"),
               ("verao", "SUMMER"), ("verão", "SUMMER"), ("summer", "SUMMER"), ("outono", "FALL"), ("fall", "FALL"))


def _temporada(busca):
    agora = time.localtime()
    padrao = ("WINTER", "SPRING", "SUMMER", "FALL")[(agora.tm_mon - 1) // 3]
    texto = (busca or "").lower()
    estacao = next((cod for nome, cod in _TEMPORADAS if nome in texto), padrao)
    achou = re.search(r"(20\d\d)", texto)
    return estacao, int(achou.group(1)) if achou else agora.tm_year


def consultar_anime(tipo=None, busca=None, **_ignorados):
    try:
        tipo = (tipo or "anime").strip().lower()
        busca = (busca or "").strip()
        if tipo.startswith(("temp", "season", "lanc", "estr")):
            estacao, ano = _temporada(busca)
            dados = _anilist(_Q_TEMPORADA, {"season": estacao, "ano": ano}) or {}
            itens = (dados.get("Page") or {}).get("media") or []
            if not itens:
                return _json({"erro": f"não achei animes da temporada {estacao} {ano}"})
            lista = [{"titulo": _titulo(m["title"]), "formato": m.get("format"), "episodios": m.get("episodes"),
                      "status": m.get("status"), "nota": m.get("averageScore"),
                      "proximo_episodio": _proximo(m.get("nextAiringEpisode"))} for m in itens]
            return _json({"temporada": f"{estacao} {ano}", "animes_mais_populares": lista})
        if not busca:
            return _json({"erro": "faltou o nome da obra ou personagem"})
        if tipo.startswith(("pers", "char")):
            c = (_anilist(_Q_PERSONAGEM, {"busca": busca}) or {}).get("Character")
            if not c:
                return _json({"erro": f"não achei o personagem '{busca}' no AniList"})
            return _json({"nome": c["name"].get("full"), "nome_original": c["name"].get("native"),
                          "genero": c.get("gender"), "idade": c.get("age"),
                          "aparece_em": [f"{_titulo(n['title'])} ({n.get('type')})" for n in (c.get("media") or {}).get("nodes", [])],
                          "descricao": _limpar_descricao(c.get("description")), "fonte": c.get("siteUrl")})
        tipo_api = "MANGA" if tipo.startswith(("man", "livro", "novel")) else "ANIME"
        m = (_anilist(_Q_MIDIA, {"busca": busca, "tipo": tipo_api}) or {}).get("Media")
        if not m:
            return _json({"erro": f"não achei '{busca}' no AniList"})
        saida = {"titulo": _titulo(m["title"]), "titulo_romaji": (m["title"] or {}).get("romaji"),
                 "tipo": tipo_api.lower(), "formato": m.get("format"), "status": m.get("status"),
                 "nota_media": m.get("averageScore"), "generos": m.get("genres"),
                 "estreia": _data(m.get("startDate")), "fim": _data(m.get("endDate")),
                 "descricao": _limpar_descricao(m.get("description")), "fonte": m.get("siteUrl")}
        if tipo_api == "ANIME":
            saida.update({"episodios": m.get("episodes"), "temporada": f"{m.get('season')} {m.get('seasonYear')}",
                          "estudio": ", ".join(n["name"] for n in (m.get("studios") or {}).get("nodes", [])),
                          "proximo_episodio": _proximo(m.get("nextAiringEpisode"))})
        else:
            saida.update({"capitulos": m.get("chapters"), "volumes": m.get("volumes")})
        return _json({k: v for k, v in saida.items() if v not in (None, "", [], "None None")})
    except Exception as e:
        return _json({"erro": f"falha ao consultar o AniList: {type(e).__name__}: {e}"})


# ------------------------------------------------------- identificar cena (trace.moe)
def identificar_cena_anime(caminho):
    """Descobre de qual anime/episódio é um print. Devolve um texto curto (ou "" se falhar)."""
    try:
        import requests
        ext = os.path.splitext(caminho)[1].lower()
        tipo = {"png": "image/png", "webp": "image/webp", "gif": "image/gif"}.get(ext.lstrip("."), "image/jpeg")
        with open(caminho, "rb") as arq:
            dados = arq.read()
        r = requests.post("https://api.trace.moe/search?anilistInfo&cutBorders", data=dados,
                          headers={"Content-Type": tipo}, timeout=40)
        if r.status_code != 200:
            return ""
        linhas = []
        for item in (r.json().get("result") or [])[:2]:
            info = item.get("anilist") or {}
            nome = _titulo(info.get("title")) if isinstance(info, dict) else str(info)
            seg = int(item.get("from") or 0)
            linhas.append(f"{nome} | episódio {item.get('episode')} | por volta de {seg // 60}:{seg % 60:02d} "
                          f"| similaridade {round((item.get('similarity') or 0) * 100)}%")
        return "\n".join(linhas)
    except Exception as e:
        print(f"[Spica/Cena] trace.moe: {type(e).__name__}: {e}")
        return ""


# ----------------------------------------------- declaração (formato Groq/OpenAI)
FERRAMENTAS = [
    {"type": "function", "function": {
        "name": "buscar_web",
        "description": ("Pesquisa na internet (DuckDuckGo). Use para notícias, preços, cotações, "
                        "placares, lançamentos, versões e qualquer fato que possa ter mudado."),
        "parameters": {"type": "object", "properties": {
            "query": {"type": "string", "description": "Termos curtos e objetivos."}},
            "required": ["query"]}}},
    {"type": "function", "function": {
        "name": "ler_pagina",
        "description": ("Abre um link (de um resultado de buscar_web) e devolve o texto da página. "
                        "Use quando os resumos da busca não bastarem."),
        "parameters": {"type": "object", "properties": {
            "url": {"type": "string", "description": "Link http/https completo."}},
            "required": ["url"]}}},
    {"type": "function", "function": {
        "name": "clima",
        "description": "Clima atual e previsão de 3 dias de uma cidade.",
        "parameters": {"type": "object", "properties": {
            "cidade": {"type": "string", "description": "Ex.: 'São Paulo' ou 'Recife, PE'."}},
            "required": ["cidade"]}}},
    {"type": "function", "function": {
        "name": "gerar_imagem",
        "description": ("Cria imagens de arte anime/mangá e outras ilustrações. Use quando a pessoa pedir para "
                        "criar, desenhar ou gerar uma imagem. A imagem aparece sozinha no chat. Não edita imagens "
                        "que a pessoa enviou. Dicas: descreva cabelo, olhos e roupa com cores; uma personagem por "
                        "imagem; poses simples; sem texto escrito na imagem."),
        "parameters": {"type": "object", "properties": {
            "assunto": {"type": "string", "description": (
                "EM INGLÊS: quem ou o que aparece, com aparência concreta. Ex.: 'a girl with long black hair "
                "and amber eyes, green jacket, orange ribbon'.")},
            "acao": {"type": "string", "description": "EM INGLÊS: pose ou ação simples. Ex.: 'standing, smiling softly'."},
            "enquadramento": {"type": "string", "description": "corpo inteiro, meio corpo, busto, rosto ou cena."},
            "estilo": {"type": "string", "description": "anime, manga (preto e branco), chibi, retro, fantasia, realista ou pixel."},
            "luz": {"type": "string", "description": "EM INGLÊS: iluminação e clima. Ex.: 'warm sunset light'."},
            "fundo": {"type": "string", "description": "EM INGLÊS: fundo. Prefira simples."},
            "variacoes": {"type": "integer", "description": "1 (padrão) ou 2, só se a pessoa pedir opções."}},
            "required": ["assunto"]}}},
    {"type": "function", "function": {
        "name": "consultar_anime",
        "description": ("Dados oficiais do AniList sobre animes, mangás e personagens: episódios, status, nota, "
                        "estreia, próximo episódio e a temporada atual. Use ANTES da pesquisa na web para perguntas "
                        "sobre obras e personagens de anime/mangá."),
        "parameters": {"type": "object", "properties": {
            "tipo": {"type": "string", "description": "anime, manga, personagem ou temporada."},
            "busca": {"type": "string", "description": (
                "Nome da obra ou do personagem (em romaji ou inglês funciona melhor). Para temporada: "
                "'atual' ou algo como 'outono 2026'.")}},
            "required": ["tipo"]}}},
    {"type": "function", "function": {
        "name": "calcular",
        "description": ("Calculadora exata. Operadores + - * / // % ** ( ) e funções "
                        "sqrt, sin, cos, tan, log, log10, exp, abs, round, min, max, floor, ceil, "
                        "constantes pi e e. Use para QUALQUER conta."),
        "parameters": {"type": "object", "properties": {
            "expressao": {"type": "string", "description": "Ex.: '1250 * 1.15 / 12'."}},
            "required": ["expressao"]}}},
]

_FUNCOES = {"buscar_web": buscar_web, "ler_pagina": ler_pagina,
            "clima": clima, "calcular": calcular, "gerar_imagem": gerar_imagem,
            "consultar_anime": consultar_anime}


def executar_ferramenta(nome, argumentos_json):
    """Executa a ferramenta pedida pelo modelo. Sempre devolve string JSON."""
    funcao = _FUNCOES.get(nome)
    if funcao is None:
        return _json({"erro": f"ferramenta desconhecida: {nome}"})
    try:
        args = json.loads(argumentos_json or "{}")
        if not isinstance(args, dict):
            raise ValueError("argumentos não são um objeto JSON")
    except Exception as e:
        return _json({"erro": f"argumentos inválidos: {e}"})
    try:
        return funcao(**args)
    except TypeError as e:
        return _json({"erro": f"parâmetros incorretos: {e}"})
    except Exception as e:
        return _json({"erro": f"falha na ferramenta: {type(e).__name__}: {e}"})
