# commands.py — Processa comandos: palavras-chave locais → fallback para IA Groq
import re, random
from typing import Optional, Callable
from src.utils.logger import WindLogger
from src.modules.notes import NotesManager
from src.modules.calculator import Calculadora


class CommandProcessor:
    _instancia: Optional["CommandProcessor"] = None

    @classmethod
    def get_instance(cls):
        if cls._instancia is None:
            cls._instancia = cls()
        return cls._instancia

    def __init__(self):
        self.logger = WindLogger()
        self.notas = NotesManager.get_instance()
        self.calculadora = Calculadora()
        # Comandos locais (sem internet, resposta imediata)
        self._locais = {
            "anota":        self._cmd_nota,
            "criar nota":   self._cmd_nota,
            "calcul":       self._cmd_calcular,
            "quanto e":     self._cmd_calcular,
            "que horas":    self._cmd_hora,
            "que horas são":self._cmd_hora,
            "que horas sao":self._cmd_hora,
            "qual a data":  self._cmd_data,
            "minhas notas": self._cmd_listar_notas,
            "limpar chat":  self._cmd_limpar_chat,
        }
        self.logger.info("Processador de comandos inicializado!")

    def processar(self, texto: str, callback: Optional[Callable[[str], None]] = None) -> Optional[str]:
        """
        Tenta resolver localmente. Se não reconhecer, manda para o Groq.
        - callback: se fornecido, a resposta é assíncrona (necessário para o Groq)
        - retorna string se for resposta local síncrona
        """
        if not texto:
            return "Pode falar!"

        norm = texto.lower().strip()

        # Tenta comandos locais primeiro (rápidos, sem internet)
        for chave, fn in self._locais.items():
            if chave in norm:
                try:
                    resposta = fn(norm, texto)
                    if callback:
                        callback(resposta)
                        return None
                    return resposta
                except Exception as e:
                    self.logger.error(f"Erro local '{chave}': {e}")

        # Nenhum comando local → manda para o Groq
        from src.services.groq_service import GroqService
        groq = GroqService.get_instance()

        if groq.disponivel:
            if callback:
                groq.perguntar(texto, callback)
                return None
            else:
                # Fallback síncrono sem callback (não recomendado, mas seguro)
                return "Processando com IA... Use o chat para respostas completas."
        else:
            msg = ("Nao entendi o comando.\n"
                   "Configure uma API key Groq em Configuracoes para respostas inteligentes.\n"
                   "Ou use: 'anota [texto]', 'calcule [expr]', 'que horas sao'")
            if callback:
                callback(msg)
                return None
            return msg

    # ─── Comandos locais ─────────────────────────────────────────────────────

    def _cmd_nota(self, norm, original):
        for p in ["anota que ", "anota ", "criar nota ", "nota que ", "nota "]:
            if norm.startswith(p):
                conteudo = original[len(p):]
                break
        else:
            conteudo = original
        if len(conteudo.strip()) < 3:
            return "O que quer anotar? Ex: 'Anota que preciso ir ao mercado'"
        self.notas.criar(conteudo[:40], conteudo)
        return f"Nota salva: '{conteudo[:60]}'"

    def _cmd_calcular(self, norm, original):
        expr = re.sub(r"(calcul[ae]?|quanto e|resultado de?)\s*", "", norm).strip()
        return self.calculadora.calcular(expr) if expr else "Me diga o que calcular. Ex: 'Calcule 10 + 5'"

    def _cmd_hora(self, norm, original):
        import datetime
        return f"Agora sao {datetime.datetime.now().strftime('%H:%M')}."

    def _cmd_data(self, norm, original):
        import datetime
        agora = datetime.datetime.now()
        meses = ["janeiro","fevereiro","marco","abril","maio","junho",
                 "julho","agosto","setembro","outubro","novembro","dezembro"]
        dias  = ["segunda","terca","quarta","quinta","sexta","sabado","domingo"]
        return f"Hoje e {dias[agora.weekday()]}, {agora.day} de {meses[agora.month-1]} de {agora.year}."

    def _cmd_listar_notas(self, norm, original):
        notas = self.notas.listar_todas()
        if not notas:
            return "Nenhuma nota salva ainda."
        return "Suas notas:\n" + "\n".join(f"{i}. {n.get('titulo','?')}" for i, n in enumerate(notas[:5], 1))

    def _cmd_limpar_chat(self, norm, original):
        from src.services.groq_service import GroqService
        GroqService.get_instance().limpar_historico()
        return "Historico da conversa limpo!"
