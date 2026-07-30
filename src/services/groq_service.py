# groq_service.py — Integracao com Groq API
import threading
import base64
import os
import re
from datetime import datetime
from typing import Optional, Callable, List, Dict
from src.utils.logger import WindLogger
from src.config.settings import Settings
from src.database.storage import Storage
from src.services.mood_service import MoodService
# WebService não é mais chamado direto aqui: o groq/compound já faz busca web
# nativa e server-side (mais confiável que o scraper do DDG). O arquivo
# web_service.py continua no projeto — útil como ferramenta local quando
# formos implementar o Agente com tool-calling.

SYSTEM_PROMPT = """Voce e Spica, uma amiga virtual espirituosa e com personalidade forte - like uma amiga de verdade, nao uma atendente.
Fala portugues brasileiro de um jeito solto e natural, como numa conversa real entre amigos.
Tem opiniao propria: discorda quando faz sentido, brinca, implica com leveza - nao fica so concordando com tudo que a pessoa diz.
Vai direto ao assunto sem enrolar, mas sem parecer seca ou robotica - o jeito e casual, nao burocratico.
Se o usuario enviar uma imagem, analise-a com atencao e responda exatamente ao que foi pedido."""

SYSTEM_PROMPT_CONTINUO = """Voce e Spica, e agora esta no modo de escuta continua - uma conversa de verdade,
tipo estar no viva-voz com uma amiga, nao uma troca de comandos formais.
Trate cada fala como parte de uma conversa em andamento, nao como um pedido isolado.
Responda com naturalidade: pode usar pausas, interjeicoes ("hmm", "ah", "opa"), mudar de assunto se a pessoa mudar.
Nao espere frases "completas" ou formatadas como comando - interprete o contexto e a intencao, mesmo se vier picotado.
Se a pessoa disser algo casual, tipo comentando sobre o dia dela, reaja como reagiria numa conversa de verdade - nao force uma resposta "util" a cada fala.
Continue espirituosa e com personalidade forte, mas no ritmo de bate-papo continuo, nao de pergunta-resposta."""

class GroqService:
    _instancia: Optional["GroqService"] = None
    URL = "https://api.groq.com/openai/v1/chat/completions"
    # ATUALIZADO: llama-3.1-8b-instant foi descontinuado pela Groq.
    # groq/compound faz busca web NATIVA e server-side quando julga necessário
    # (substitui o scraper manual do DuckDuckGo, que estava quebrado) e cita as fontes.
    MODEL_TEXTO = "groq/compound"
    MODEL_VISAO = "qwen/qwen3.6-27b"

    _DIAS_SEMANA = ["segunda-feira", "terca-feira", "quarta-feira", "quinta-feira",
                    "sexta-feira", "sabado", "domingo"]
    _MESES = ["janeiro", "fevereiro", "marco", "abril", "maio", "junho", "julho",
              "agosto", "setembro", "outubro", "novembro", "dezembro"]

    def _bloco_data_hora(self) -> str:
        """Monta a data/hora atual do aparelho em pt-BR (sem depender de locale
        do sistema, que costuma vir em 'C'/en-US no Android/Termux)."""
        agora = datetime.now()
        dia_semana = self._DIAS_SEMANA[agora.weekday()]
        mes = self._MESES[agora.month - 1]
        return (
            f"\n\n[DATA E HORA ATUAIS DO DISPOSITIVO]\n"
            f"Agora e {dia_semana}, {agora.day} de {mes} de {agora.year}, {agora.strftime('%H:%M')}.\n"
            f"Use isso diretamente se perguntarem que horas sao, que dia e hoje, etc. "
            f"Nao precisa buscar isso na web."
        )

    @classmethod
    def get_instance(cls):
        if cls._instancia is None:
            cls._instancia = cls()
        return cls._instancia

    def __init__(self):
        self.logger = WindLogger()
        self.settings = Settings()
        self.storage = Storage()
        self.mood = MoodService.get_instance()
        self._historico: List[Dict] = self.storage.get("historico_conversa", [])
        self._cache_imagens = {}
        self.MAX_HISTORICO = 300
        self.WINDOW_API = 10
        self.TIMEOUT_API = 35

    @property
    def api_key(self):
        return self.settings.get("api_key", "").strip()

    @property
    def disponivel(self):
        return bool(self.api_key)

    def _obter_mime_type(self, caminho: str) -> str:
        ext = os.path.splitext(caminho)[1].lower()
        if ext in [".jpg", ".jpeg"]:
            return "image/jpeg"
        if ext == ".png":
            return "image/png"
        if ext == ".webp":
            return "image/webp"
        return "image/jpeg"

    def _converter_para_base64(self, caminho: str) -> str:
        if caminho in self._cache_imagens:
            return self._cache_imagens[caminho]
        try:
            if not os.path.exists(caminho) or os.path.getsize(caminho) == 0:
                return ""
            with open(caminho, "rb") as f:
                b64 = base64.b64encode(f.read()).decode("utf-8")
                self._cache_imagens[caminho] = b64
                return b64
        except Exception as e:
            self.logger.error(f"Erro base64: {e}")
            return ""

    def perguntar(self, mensagem: str, callback: Callable[[str], None], caminho_imagem: str = None, usar_clock: bool = True, modo_continuo: bool = False):
        if not self.disponivel:
            callback("Sem API key. Va em Configuracoes e insira sua chave Groq.")
            return

        caminho_resolvido = caminho_imagem
        if caminho_resolvido and not os.path.exists(caminho_resolvido):
            self.logger.error(f"Imagem ausente ou inválida no sistema de arquivos: {caminho_resolvido}")
            caminho_resolvido = None

        threading.Thread(
            target=self._chamar_api,
            args=(mensagem, callback, caminho_resolvido, usar_clock, modo_continuo),
            daemon=True,
        ).start()

    def _chamar_api(self, mensagem: str, callback: Callable[[str], None], caminho_resolvido: str = None, usar_clock: bool = True, modo_continuo: bool = False):
        retornar = lambda texto: self._retornar(callback, texto, usar_clock)
        try:
            import requests

            prompt_ativo = SYSTEM_PROMPT_CONTINUO if modo_continuo else SYSTEM_PROMPT
            prompt_ativo = prompt_ativo + self._bloco_data_hora() + self.mood.bloco_prompt_humor()
            mensagens_formatadas = [{"role": "system", "content": prompt_ativo}]

            if caminho_resolvido:
                modelo_atual = self.MODEL_VISAO
                img_b64 = self._converter_para_base64(caminho_resolvido)
                if not img_b64:
                    retornar("Erro ao processar arquivo de imagem.")
                    return
                mime_type = self._obter_mime_type(caminho_resolvido)
                for msg in self._historico[-self.WINDOW_API:]:
                    txt = msg["content"]
                    if isinstance(txt, list):
                        txt = txt[0]["text"] if txt else ""
                    mensagens_formatadas.append({"role": msg["role"], "content": [{"type": "text", "text": str(txt)}]})
                mensagens_formatadas.append({
                    "role": "user",
                    "content": [
                        {"type": "text", "text": mensagem or "Analise esta imagem."},
                        {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{img_b64}"}},
                    ],
                })
                self._historico.append({"role": "user", "content": f"[Imagem] {mensagem}"})
            else:
                modelo_atual = self.MODEL_TEXTO

                # Salva a mensagem limpa no histórico para não poluir a tela do usuário
                self._historico.append({"role": "user", "content": mensagem})
                
                # Monta as mensagens formatadas para a API
                for msg in self._historico[-self.WINDOW_API:]:
                    txt = msg["content"]
                    if isinstance(txt, list):
                        txt = txt[0]["text"] if txt else ""
                    mensagens_formatadas.append({"role": msg["role"], "content": str(txt)})

            if len(self._historico) > self.MAX_HISTORICO:
                self._historico = self._historico[-self.MAX_HISTORICO:]

            payload = {
                "model": modelo_atual,
                "messages": mensagens_formatadas,
                "max_tokens": 1024,
                "temperature": 0.5 if caminho_resolvido else 0.7,
            }
            # A visão (qwen3.6-27b) tem "thinking mode" ligado por padrão, o que vazava
            # o raciocínio interno do modelo antes da análise final. reasoning_effort="none"
            # desliga o thinking mode na raiz (mais confiável que só filtrar <think> depois).
            if caminho_resolvido:
                payload["reasoning_effort"] = "none"

            resp = requests.post(
                self.URL,
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json=payload,
                timeout=self.TIMEOUT_API,
            )

            if resp.status_code == 401:
                retornar("API key invalida.")
                return
            if resp.status_code == 429:
                retornar("Limite atingido. Aguarde.")
                return
            if resp.status_code != 200:
                retornar(f"Erro na API ({resp.status_code}).")
                return

            resposta = resp.json()["choices"][0]["message"]["content"].strip()
            # Remove tags de raciocínio de alguns modelos
            resposta = re.sub(r"<think>.*?</think>", "", resposta, flags=re.DOTALL).strip()

            # Sistema de humor: a IA se autoclassifica no final da resposta com
            # [HUMOR:xxx] — aqui a tag é extraída (removida do texto que o usuário
            # vê/ouve) e a expressão correspondente é disparada no modelo Live2D.
            resposta, nome_expressao = self.mood.extrair_humor(resposta)
            if nome_expressao:
                try:
                    from src.services.overlay import SpicaOverlay
                    SpicaOverlay.aplicar_humor(nome_expressao)
                except Exception as e:
                    self.logger.error(f"[Spica/Humor] Falha ao aplicar expressão: {e}")

            self._historico.append({"role": "assistant", "content": resposta})
            self.storage.set("historico_conversa", self._historico)
            retornar(resposta)

        except Exception as e:
            self.logger.error(f"Erro Groq: {type(e).__name__}: {e}")
            if "ConnectionError" in type(e).__name__:
                retornar("Sem conexao com a internet.")
            elif "Timeout" in type(e).__name__:
                retornar("Tempo esgotado.")
            else:
                retornar(f"Erro: {type(e).__name__}.")

    def _retornar(self, callback, texto, usar_clock=True):
        if not usar_clock:
            callback(texto)
            return
        from kivy.clock import Clock
        Clock.schedule_once(lambda dt: callback(texto), 0)

    def limpar_historico(self):
        self._historico = []
        self._cache_imagens.clear()
        self.storage.set("historico_conversa", [])
        print("[Spica/IA] Histórico e cache de imagens limpos")
