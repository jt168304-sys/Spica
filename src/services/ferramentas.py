# ferramentas.py — Caixa de ferramentas da Spica (Tool Calling do Groq)
# Ferramentas: buscar_web, ler_pagina, clima, calcular.
# Regra de ouro: NENHUMA ferramenta lança exceção — sempre devolve um JSON (string).
import ast
import html
import ipaddress
import json
import math
import operator
import re
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


# ----------------------------------------------- declaração (formato Groq/OpenAI)
FERRAMENTAS = [
    {"type": "function", "function": {
        "name": "buscar_web",
        "description": ("Pesquisa na internet (DuckDuckGo). Use para notícias, preços, cotações, "
                        "placares, lançamentos, versões e qualquer fato que possa ter mudado."),
        "parameters": {"type": "object", "properties": {
            "query": {"type": "string", "description": "Termos curtos e objetivos."},
            "max_resultados": {"type": "integer", "minimum": 1, "maximum": 8}},
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
        "name": "calcular",
        "description": ("Calculadora exata. Operadores + - * / // % ** ( ) e funções "
                        "sqrt, sin, cos, tan, log, log10, exp, abs, round, min, max, floor, ceil, "
                        "constantes pi e e. Use para QUALQUER conta."),
        "parameters": {"type": "object", "properties": {
            "expressao": {"type": "string", "description": "Ex.: '1250 * 1.15 / 12'."}},
            "required": ["expressao"]}}},
]

_FUNCOES = {"buscar_web": buscar_web, "ler_pagina": ler_pagina,
            "clima": clima, "calcular": calcular}


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
