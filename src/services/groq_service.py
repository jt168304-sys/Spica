# groq_service.py — Integracao com Groq API
import threading
import base64
import os
from typing import Optional, Callable, List, Dict
from src.utils.logger import WindLogger
from src.config.settings import Settings

SYSTEM_PROMPT = """Voce e Spica, uma assistente virtual inteligente, direta e com personalidade marcante.
Responde em portugues brasileiro, de forma natural e descontraida.
E eficiente: vai direto ao ponto, sem enrolacao.
Se o usuario enviar uma imagem, analise-a com atencao e responda exatamente ao que foi pedido."""

class GroqService:
    _instancia: Optional["GroqService"] = None
    URL = "https://api.groq.com/openai/v1/chat/completions"
    MODEL_TEXTO = "llama-3.1-8b-instant"
    MODEL_VISAO = "meta-llama/llama-4-scout-17b-16e-instruct"

    @classmethod
    def get_instance(cls):
        if cls._instancia is None:
            cls._instancia = cls()
        return cls._instancia

    def __init__(self):
        self.logger = WindLogger()
        self.settings = Settings()
        self._historico: List[Dict] = []
        self._cache_imagens = {}  # ✅ NOVO: Cache de imagens em base64
        self.MAX_HISTORICO = 100  # ✅ NOVO: Limitar histórico
        self.WINDOW_API = 6  # ✅ NOVO: Usar últimas 6 mensagens para API
        self.TIMEOUT_API = 35  # ✅ NOVO: Timeout configurável

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
        # ✅ NOVO: Verificar cache primeiro
        if caminho in self._cache_imagens:
            return self._cache_imagens[caminho]
        
        try:
            if not os.path.exists(caminho) or os.path.getsize(caminho) == 0:
                return ""
            with open(caminho, "rb") as f:
                b64 = base64.b64encode(f.read()).decode("utf-8")
                self._cache_imagens[caminho] = b64  # ✅ NOVO: Armazenar em cache
                return b64
        except Exception as e:
            self.logger.error(f"Erro base64: {e}")
            return ""

    def perguntar(self, mensagem: str, callback: Callable[[str], None], caminho_imagem: str = None):
        if not self.disponivel:
            callback("Sem API key. Va em Configuracoes e insira sua chave Groq.")
            return

        caminho_resolvido = caminho_imagem
        # Como o image_handler.py já validou a imagem, apenas checamos a existência aqui
        if caminho_resolvido and not os.path.exists(caminho_resolvido):
            self.logger.error(f"Imagem ausente ou inválida no sistema de arquivos: {caminho_resolvido}")
            caminho_resolvido = None

        threading.Thread(
            target=self._chamar_api,
            args=(mensagem, callback, caminho_resolvido),
            daemon=True,
        ).start()

    def _chamar_api(self, mensagem: str, callback: Callable[[str], None], caminho_resolvido: str = None):
        try:
            import requests
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

            mensagens_formatadas = [{"role": "system", "content": SYSTEM_PROMPT}]

            if caminho_resolvido:
                modelo_atual = self.MODEL_VISAO
                img_b64 = self._converter_para_base64(caminho_resolvido)
                if not img_b64:
                    self._retornar(callback, "Erro ao processar arquivo de imagem.")
                    return
                mime_type = self._obter_mime_type(caminho_resolvido)
                # ✅ NOVO: Usar WINDOW_API em vez de hardcoded -6
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
                self._historico.append({"role": "user", "content": mensagem})
                # ✅ NOVO: Usar WINDOW_API em vez de hardcoded -12
                for msg in self._historico[-self.WINDOW_API:]:
                    txt = msg["content"]
                    if isinstance(txt, list):
                        txt = txt[0]["text"] if txt else ""
                    mensagens_formatadas.append({"role": msg["role"], "content": str(txt)})

            # ✅ NOVO: Manter apenas últimas MAX_HISTORICO mensagens
            if len(self._historico) > self.MAX_HISTORICO:
                self._historico = self._historico[-self.MAX_HISTORICO:]

            payload = {
                "model": modelo_atual,
                "messages": mensagens_formatadas,
                "max_tokens": 1024,
                "temperature": 0.5 if caminho_resolvido else 0.7,
            }

            # ✅ NOVO: Usar TIMEOUT_API configurável
            resp = requests.post(
                self.URL,
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json=payload,
                timeout=self.TIMEOUT_API,
                verify=False,
            )

            if resp.status_code == 401:
                self._retornar(callback, "API key invalida.")
                return
            if resp.status_code == 429:
                self._retornar(callback, "Limite atingido. Aguarde.")
                return
            if resp.status_code != 200:
                self._retornar(callback, f"Erro na API ({resp.status_code}).")
                return

            resposta = resp.json()["choices"][0]["message"]["content"].strip()
            self._historico.append({"role": "assistant", "content": resposta})
            self._retornar(callback, resposta)

        except Exception as e:
            self.logger.error(f"Erro Groq: {type(e).__name__}: {e}")
            if "ConnectionError" in type(e).__name__:
                self._retornar(callback, "Sem conexao com a internet.")
            elif "Timeout" in type(e).__name__:
                self._retornar(callback, "Tempo esgotado.")
            else:
                self._retornar(callback, f"Erro: {type(e).__name__}.")

    def _retornar(self, callback, texto):
        from kivy.clock import Clock
        Clock.schedule_once(lambda dt: callback(texto), 0)

    def limpar_historico(self):
        self._historico = []
        self._cache_imagens.clear()  # ✅ NOVO: Limpar cache também
        print("[Spica/IA] Histórico e cache de imagens limpos")
