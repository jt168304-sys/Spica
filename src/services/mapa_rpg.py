# mapa_rpg.py — Gera mapas de RPG vistos de cima (masmorra e caverna) por CÓDIGO, em PNG.
# Modelos de imagem erram mapas (grade, salas, proporções); o código acerta o que foi pedido.
# Sem bibliotecas extras: escreve o PNG na mão (zlib + struct).
import random
import re
import struct
import zlib

_DIGITOS = {  # fonte 3x5 para numerar as salas
    "0": "111101101101111", "1": "010110010010111", "2": "111001111100111", "3": "111001111001111",
    "4": "101101111001001", "5": "111100111001111", "6": "111100111101111", "7": "111001001001001",
    "8": "111101111101111", "9": "111101111001111"}
_PEDRA, _PAREDE, _CHAO, _GRADE, _TEXTO = (46, 46, 56), (20, 20, 26), (176, 164, 140), (150, 138, 116), (120, 30, 30)
_AGUA = (96, 140, 176)


def eh_pedido_de_mapa(texto):
    t = (texto or "").lower()
    chaves = ("battle map", "battlemap", "dungeon map", "rpg map", "tabletop map", "masmorra", "mapa de rpg",
              "mapa rpg", "mapa de masmorra", "mapa de dungeon", "dnd map", "d&d map", "mapa de batalha")
    return any(c in t for c in chaves) or ("mapa" in t and "rpg" in t) or \
        (("map" in t) and any(k in t for k in ("top-down", "top down", "overhead", "dungeon", "rpg")))


def _retangulo(pix, w, x0, y0, x1, y1, cor):
    linha = bytes(cor) * max(0, x1 - x0)
    for y in range(y0, y1):
        o = (y * w + x0) * 3
        pix[o:o + len(linha)] = linha


def _numero(pix, w, x, y, n, cor, escala=3):
    cx = x
    for ch in str(n):
        bits = _DIGITOS[ch]
        for i, b in enumerate(bits):
            if b == "1":
                px, py = cx + (i % 3) * escala, y + (i // 3) * escala
                _retangulo(pix, w, px, py, px + escala, py + escala, cor)
        cx += 4 * escala


def _png(w, h, pix):
    bruto = b"".join(b"\x00" + bytes(pix[y * w * 3:(y + 1) * w * 3]) for y in range(h))
    def bloco(tipo, dados):
        return struct.pack(">I", len(dados)) + tipo + dados + struct.pack(">I", zlib.crc32(tipo + dados) & 0xffffffff)
    return (b"\x89PNG\r\n\x1a\n" + bloco(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
            + bloco(b"IDAT", zlib.compress(bruto, 6)) + bloco(b"IEND", b""))


def _masmorra(cw, ch, salas, rng):
    grade = [[0] * cw for _ in range(ch)]
    lista = []
    for _ in range(salas * 12):
        if len(lista) >= salas:
            break
        rw, rh = rng.randint(4, 8), rng.randint(3, 6)
        rx, ry = rng.randint(1, cw - rw - 2), rng.randint(1, ch - rh - 2)
        if any(rx < a + aw + 1 and a < rx + rw + 1 and ry < b + bh + 1 and b < ry + rh + 1 for a, b, aw, bh in lista):
            continue
        lista.append((rx, ry, rw, rh))
        for y in range(ry, ry + rh):
            for x in range(rx, rx + rw):
                grade[y][x] = 1
    centros = [(x + w // 2, y + h // 2) for x, y, w, h in lista]
    for (ax, ay), (bx, by) in zip(centros, centros[1:]):          # corredores em L
        for x in range(min(ax, bx), max(ax, bx) + 1):
            grade[ay][x] = grade[ay][x] or 2
        for y in range(min(ay, by), max(ay, by) + 1):
            grade[y][bx] = grade[y][bx] or 2
    return grade, centros


def _caverna(cw, ch, rng):
    g = [[1 if rng.random() < 0.46 and 0 < x < cw - 1 and 0 < y < ch - 1 else 0 for x in range(cw)] for y in range(ch)]
    for _ in range(4):
        nova = [[0] * cw for _ in range(ch)]
        for y in range(1, ch - 1):
            for x in range(1, cw - 1):
                viz = sum(g[y + j][x + i] for j in (-1, 0, 1) for i in (-1, 0, 1))
                nova[y][x] = 1 if viz >= 5 else 0
        g = nova
    return g, []


def gerar(descricao=""):
    """Devolve (bytes_png, resumo). Lê do texto: caverna/cave, 'N salas/rooms', 'LxA' (células)."""
    t = (descricao or "").lower()
    rng = random.Random()
    caverna = any(k in t for k in ("caverna", "cave", "cavern"))
    m = re.search(r"(\d+)\s*(?:rooms|salas|rooms?)", t)
    salas = max(3, min(int(m.group(1)), 14)) if m else rng.randint(6, 8)
    m = re.search(r"(\d{2})\s*[x×]\s*(\d{2})", t)
    cw, ch = (max(16, min(int(m.group(1)), 48)), max(12, min(int(m.group(2)), 36))) if m else (32, 24)
    tam = 24
    w, h = cw * tam, ch * tam
    grade, centros = _caverna(cw, ch, rng) if caverna else _masmorra(cw, ch, salas, rng)
    pix = bytearray(bytes(_PEDRA) * (w * h))
    for y in range(ch):
        for x in range(cw):
            if grade[y][x]:
                _retangulo(pix, w, x * tam, y * tam, (x + 1) * tam, (y + 1) * tam, _CHAO)
                _retangulo(pix, w, x * tam, y * tam, (x + 1) * tam, y * tam + 1, _GRADE)
                _retangulo(pix, w, x * tam, y * tam, x * tam + 1, (y + 1) * tam, _GRADE)
    for y in range(ch):                       # contorno escuro das paredes
        for x in range(cw):
            if grade[y][x]:
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = x + dx, y + dy
                    if not (0 <= nx < cw and 0 <= ny < ch) or not grade[ny][nx]:
                        if dx:
                            xx = (x + (1 if dx > 0 else 0)) * tam - 2
                            _retangulo(pix, w, xx, y * tam, xx + 4, (y + 1) * tam, _PAREDE)
                        else:
                            yy = (y + (1 if dy > 0 else 0)) * tam - 2
                            _retangulo(pix, w, x * tam, yy, (x + 1) * tam, yy + 4, _PAREDE)
    for i, (cx, cy) in enumerate(centros, 1):  # número de cada sala
        _numero(pix, w, cx * tam + 4, cy * tam + 4, i, _TEXTO)
    tipo = "caverna" if caverna else f"masmorra com {len(centros)} salas"
    return _png(w, h, pix), f"{tipo}, grade {cw}x{ch}"
