# mood_service.py — Sistema de humor/expressões da Spica
# A IA se autoclassifica no fim de cada resposta com uma tag tipo [HUMOR:surpresa],
# que é lida aqui, removida do texto (o usuário nunca vê/ouve a tag), e traduzida
# pra uma expressão do modelo Live2D via o assets/live2d/humor.json (editável).
import os
import re
import json
from src.utils.logger import WindLogger


class MoodService:
    _instancia = None
    # tolera erros do modelo: [HUDOR:neutro], [HUMOR : ??], espaços, ":" ou "="
    TAG_REGEX = re.compile(r"\s*\[\s*H[Uu][A-Za-z]{1,4}\s*[:：=]\s*([^\]\n]{0,24}?)\s*\]\s*$")
    _TAG_ABERTA = re.compile(r"\s*\[\s*H[Uu][A-Za-z]{1,4}\s*[:：=][^\]\n]*$")

    @classmethod
    def get_instance(cls):
        if cls._instancia is None:
            cls._instancia = cls()
        return cls._instancia

    def __init__(self):
        self.logger = WindLogger()
        self._humores = self._carregar_humores()

    def _caminho_humor_json(self):
        # src/services/mood_service.py -> sobe 2 níveis até a raiz do projeto
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        return os.path.join(base_dir, "assets", "expressoes", "humor.json")

    def _carregar_humores(self):
        try:
            caminho = self._caminho_humor_json()
            if os.path.exists(caminho):
                with open(caminho, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            self.logger.error(f"[Spica/Humor] Falha ao carregar humor.json: {e}")
        # Fallback mínimo caso o arquivo não exista ou esteja corrompido
        return {"neutro": {"expressao": None, "descricao": "Estado padrao"}}

    def recarregar(self):
        """Recarrega o humor.json do disco sem precisar reiniciar o app —
        útil enquanto você ainda está ajustando/testando os humores."""
        self._humores = self._carregar_humores()
        self.logger.info(f"[Spica/Humor] humor.json recarregado: {list(self._humores.keys())}")

    def humores_disponiveis(self):
        return list(self._humores.keys())

    def bloco_prompt_humor(self) -> str:
        """Instrução do humor para o system prompt. Lista cada humor com a descrição do
        humor.json, então adicionar um humor novo lá já reflete aqui sem mexer no código."""
        linhas = "\n".join(
            f"- {chave}: {dados.get('descricao', '')}" for chave, dados in self._humores.items()
        )
        return (
            "\n\n[SISTEMA DE HUMOR - OBRIGATORIO]\n"
            "No FINAL de toda resposta, numa linha separada, adicione uma tag com o seu tom emocional "
            "NAQUELA resposta. Formato exato: [HUMOR:chave]\n"
            f"Chaves e quando usar cada uma:\n{linhas}\n"
            "Escolha pelo que voce sente ao dizer aquilo, nao pelo assunto. Varie: use 'neutro' so em conversa "
            "comum e deixe as outras para quando a emocao for real (elogio ou boa noticia = feliz, "
            "algo inesperado = surpresa, nao entendeu = confusa, ma noticia ou desanimo = triste, "
            "situacao constrangedora ou absurda = chocada). A tag e interna: a pessoa nunca ve nem ouve. "
            "Nao a mencione nem explique, so adicione no final."
        )

    def extrair_humor(self, texto_resposta: str):
        """Recebe a resposta crua da IA (que deve terminar com [HUMOR:xxx]).
        Devolve (texto_limpo, nome_expressao_ou_None). Se a tag não vier, ou o
        humor não existir no humor.json, cai em silêncio (sem trocar expressão)
        em vez de quebrar a resposta."""
        if not texto_resposta:
            return texto_resposta, None

        match = self.TAG_REGEX.search(texto_resposta)
        if not match:
            return self._TAG_ABERTA.sub("", texto_resposta).strip(), None   # tag quebrada: só some

        chave_humor = match.group(1).strip().lower()
        texto_limpo = self._TAG_ABERTA.sub("", self.TAG_REGEX.sub("", texto_resposta)).strip()

        humor = self._humores.get(chave_humor)
        if humor is None:
            self.logger.info(f"[Spica/Humor] IA usou humor desconhecido '{chave_humor}' — ignorando expressao")
            return texto_limpo, None

        return texto_limpo, chave_humor
