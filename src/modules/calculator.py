# calculator.py — Avalia expressoes matematicas e linguagem natural
import re
from src.utils.logger import WindLogger


class Calculadora:
    def __init__(self):
        self.logger = WindLogger()

    def calcular(self, expressao: str) -> str:
        try:
            expr = self._normalizar(expressao)
            especial = self._checar_especiais(expr, expressao)
            if especial:
                return especial
            resultado = self._avaliar_seguro(expr)
            fmt = str(int(resultado)) if resultado == int(resultado) else f"{resultado:.4f}".rstrip("0").rstrip(".")
            return f"{expressao} = {fmt}"
        except ZeroDivisionError:
            return "Divisao por zero nao e possivel."
        except:
            return "Nao consegui calcular. Ex: 'Calcule 10 + 5'"

    def _normalizar(self, expr: str) -> str:
        for antigo, novo in [("×","*"),("÷","/"),("²","**2"),("³","**3"),(",","."),("x","*")]:
            expr = expr.replace(antigo, novo)
        return expr.lower().strip()

    def _checar_especiais(self, norm, original):
        import math
        m = re.search(r"raiz\s+(?:quadrada\s+)?de\s+([\d.]+)", norm)
        if m:
            n = float(m.group(1))
            return f"raiz de {n} = {math.sqrt(n):.4f}".rstrip("0").rstrip(".")
        m = re.search(r"([\d.]+)\s*(?:%|por\s+cento)\s+de\s+([\d.]+)", norm)
        if m:
            return f"{m.group(1)}% de {m.group(2)} = {(float(m.group(1))/100)*float(m.group(2))}"
        return None

    def _avaliar_seguro(self, expr: str) -> float:
        if not re.match(r"^[\d\s\+\-\*\/\(\)\.\%\*]+$", expr):
            raise ValueError("Expressao invalida")
        return float(eval(expr, {"__builtins__": {}}, {}))
