# groq_service.py — Integração com Groq API
import threading, json
from typing import Optional, Callable, List, Dict
from src.utils.logger import WindLogger
from src.config.settings import Settings

SYSTEM_PROMPT = """Você é WindIA, uma assistente virtual inteligente, direta e com personalidade marcante.
Responde em português brasileiro, de forma natural e descontraída.
É eficiente: vai direto ao ponto, sem enrolação.
Tem senso de humor leve quando o contexto permite.
Quando não sabe algo, assume com clareza em vez de inventar.
Respostas curtas para perguntas simples, detalhadas quando necessário.
Nunca finge ser humana se perguntada diretamente."""


class GroqService:
    _instancia: Optional["GroqService"] = None
    URL   = "https://api.groq.com/openai/v1/chat/completions"
    MODEL = "llama-3.1-8b-instant"

    @classmethod
    def get_instance(cls):
        if cls._instancia is None:
            cls._instancia = cls()
        return cls._instancia

    def __init__(self):
        self.logger = WindLogger()
        self.settings = Settings()
        self._historico: List[Dict] = []

    @property
    def api_key(self): return self.settings.get("api_key", "").strip()

    @property
    def disponivel(self): return bool(self.api_key)

    def perguntar(self, mensagem: str, callback: Callable[[str], None]):
        if not self.disponivel:
            callback("Sem API key. Va em Configuracoes e insira sua chave Groq.")
            return
        threading.Thread(target=self._chamar_api, args=(mensagem, callback), daemon=True).start()

    def _chamar_api(self, mensagem: str, callback: Callable[[str], None]):
        try:
            import requests, urllib3
            # Desativa aviso de SSL (necessário no Android/Pydroid)
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

            self._historico.append({"role": "user", "content": mensagem})

            payload = {
                "model": self.MODEL,
                "messages": [{"role": "system", "content": SYSTEM_PROMPT}] + self._historico[-20:],
                "max_tokens": 1024,
                "temperature": 0.7,
            }

            resp = requests.post(
                self.URL,
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json=payload,
                timeout=30,
                verify=False,  # Evita erro de certificado SSL no Android
            )

            # Log do status para debug
            self.logger.info(f"Groq status: {resp.status_code}")

            if resp.status_code == 401:
                self._retornar(callback, "API key invalida ou expirada. Verifique em Configuracoes.")
                return
            if resp.status_code == 429:
                self._retornar(callback, "Limite de requisicoes atingido. Aguarde alguns segundos.")
                return
            if resp.status_code != 200:
                self.logger.error(f"Groq erro {resp.status_code}: {resp.text[:200]}")
                self._retornar(callback, f"Erro na API ({resp.status_code}). Tente novamente.")
                return

            resposta = resp.json()["choices"][0]["message"]["content"].strip()
            self._historico.append({"role": "assistant", "content": resposta})
            self._retornar(callback, resposta)

        except Exception as e:
            self.logger.error(f"Erro Groq: {type(e).__name__}: {e}")
            # Mostra o tipo do erro para facilitar debug
            if "ConnectionError" in type(e).__name__:
                self._retornar(callback, "Sem conexao com a internet.")
            elif "Timeout" in type(e).__name__:
                self._retornar(callback, "Tempo esgotado. Verifique sua conexao.")
            else:
                self._retornar(callback, f"Erro: {type(e).__name__}. Veja o log.")

    def _retornar(self, callback, texto):
        from kivy.clock import Clock
        Clock.schedule_once(lambda dt: callback(texto), 0)

    def limpar_historico(self):
        self._historico = []
