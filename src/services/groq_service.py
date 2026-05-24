# groq_service.py — Integração com Groq API (Texto + Visão)
import threading
import json
import base64
import os
from typing import Optional, Callable, List, Dict
from src.utils.logger import WindLogger
from src.config.settings import Settings

SYSTEM_PROMPT = """Você é WindIA, uma assistente virtual inteligente, direta e com personalidade marcante.
Responde em português brasileiro, de forma natural e descontraída.
É eficiente: vai direto ao ponto, sem enrolação.
Se o usuário enviar uma imagem, analise-a com atenção e responda exatamente ao que foi pedido."""


class GroqService:
    _instancia: Optional["GroqService"] = None
    URL   = "https://api.groq.com/openai/v1/chat/completions"
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

    @property
    def api_key(self): return self.settings.get("api_key", "").strip()

    @property
    def disponivel(self): return bool(self.api_key)

    def _obter_mime_type(self, caminho_imagem: str) -> str:
        """Retorna o MIME type baseado na extensão do arquivo."""
        ext = os.path.splitext(caminho_imagem)[1].lower()
        if ext in ['.jpg', '.jpeg']:
            return 'image/jpeg'
        elif ext == '.png':
            return 'image/png'
        # A API Groq também aceita WEBP? Não documentado, mas por segurança:
        elif ext == '.webp':
            return 'image/webp'
        else:
            # Fallback para JPEG, mas o backend pode rejeitar
            self.logger.warning(f"Extensão não suportada: {ext}. Tentando como JPEG.")
            return 'image/jpeg'

    def _converter_para_base64(self, caminho_imagem: str) -> str:
        try:
            # Verifica se o arquivo existe e não está vazio
            if not os.path.exists(caminho_imagem):
                self.logger.error(f"Arquivo não encontrado: {caminho_imagem}")
                return ""
            if os.path.getsize(caminho_imagem) == 0:
                self.logger.error(f"Arquivo vazio: {caminho_imagem}")
                return ""
            
            with open(caminho_imagem, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
        except Exception as e:
            self.logger.error(f"Erro ao converter imagem para base64: {e}")
            return ""

    def perguntar(self, mensagem: str, callback: Callable[[str], None], caminho_imagem: str = None):
        if not self.disponivel:
            callback("Sem API key. Va em Configuracoes e insira sua chave Groq.")
            return
        threading.Thread(target=self._chamar_api, args=(mensagem, callback, caminho_imagem), daemon=True).start()

    def _chamar_api(self, mensagem: str, callback: Callable[[str], None], caminho_imagem: str = None):
        try:
            import requests, urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

            # Inicializa a lista final de mensagens com a instrução do sistema
            mensagens_formatadas = [{"role": "system", "content": SYSTEM_PROMPT}]

            # 1. Fluxo de processamento se contiver Imagem (Multimodal)
            if caminho_imagem and os.path.exists(caminho_imagem):
                modelo_atual = self.MODEL_VISAO
                img_b64 = self._converter_para_base64(caminho_imagem)
                
                if not img_b64:
                    self._retornar(callback, "Erro ao processar o arquivo de imagem.")
                    return

                # Obtém o MIME type correto
                mime_type = self._obter_mime_type(caminho_imagem)

                # Monta o nó estruturado de conteúdo visual
                conteudo_imagem = [
                    {"type": "text", "text": mensagem if mensagem else "Analise e descreva esta imagem detalhadamente."},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime_type};base64,{img_b64}"}
                    }
                ]

                # Para evitar erros 400 por misturas complexas de tipos nas mensagens anteriores,
                # convertemos de forma segura o histórico prévio para o formato estruturado que o modelo aceita
                for msg in self._historico[-6:]:
                    txt_anterior = msg["content"]
                    if isinstance(txt_anterior, list):
                        # Caso já seja uma lista estruturada de imagem, extrai apenas o campo texto para simplificar
                        txt_anterior = txt_anterior[0]["text"] if txt_anterior else ""
                    
                    mensagens_formatadas.append({
                        "role": msg["role"],
                        "content": [{"type": "text", "text": str(txt_anterior)}]
                    })

                # Adiciona o comando de imagem atual como a última mensagem do usuário
                mensagens_formatadas.append({"role": "user", "content": conteudo_imagem})
                
                # Guarda uma representação amigável no histórico local para conversas futuras de texto puro
                self._historico.append({"role": "user", "content": f"[📸 Imagem] {mensagem}"})

            # 2. Fluxo de processamento padrão (Texto Puro)
            else:
                modelo_atual = self.MODEL_TEXTO
                self._historico.append({"role": "user", "content": mensagem})

                # Normaliza mensagens antigas de imagem para texto puro antes de enviar para o modelo de texto
                for msg in self._historico[-12:]:
                    txt_normalizado = msg["content"]
                    if isinstance(txt_normalizado, list):
                        txt_normalizado = txt_normalizado[0]["text"] if txt_normalizado else ""
                    
                    mensagens_formatadas.append({
                        "role": msg["role"],
                        "content": str(txt_normalizado)
                    })

            payload = {
                "model": modelo_atual,
                "messages": mensagens_formatadas,
                "max_tokens": 1024,
                "temperature": 0.5 if caminho_imagem else 0.7,
            }

            # Log para depuração (opcional, comente se quiser)
            # self.logger.debug(f"Payload enviado: {json.dumps(payload, indent=2)[:500]}")

            resp = requests.post(
                self.URL,
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json=payload,
                timeout=35,
                verify=False,
            )

            self.logger.info(f"Groq status: {resp.status_code}")

            if resp.status_code == 401:
                self._retornar(callback, "API key invalida. Verifique em Configuracoes.")
                return
            if resp.status_code == 429:
                self._retornar(callback, "Limite de requisicoes atingido. Aguarde alguns segundos.")
                return
            if resp.status_code != 200:
                self.logger.error(f"Groq erro {resp.status_code}: {resp.text}")
                # Mensagem mais descritiva para erro 400
                if resp.status_code == 400:
                    erro_msg = "Erro 400: requisição mal formatada. Verifique o tipo da imagem (deve ser JPEG ou PNG)."
                    # Tenta extrair detalhe da resposta, se possível
                    try:
                        erro_json = resp.json()
                        if "error" in erro_json:
                            erro_msg += f" Detalhe: {erro_json['error'].get('message', '')}"
                    except:
                        pass
                    self._retornar(callback, erro_msg)
                else:
                    self._retornar(callback, f"Erro na API ({resp.status_code}). Tente novamente.")
                return

            resposta = resp.json()["choices"][0]["message"]["content"].strip()
            
            # Registra a resposta do assistente no histórico local de forma textual simples
            self._historico.append({"role": "assistant", "content": resposta})
            self._retornar(callback, resposta)

        except Exception as e:
            self.logger.error(f"Erro Groq: {type(e).__name__}: {e}")
            if "ConnectionError" in type(e).__name__:
                self._retornar(callback, "Sem conexao com a internet.")
            elif "Timeout" in type(e).__name__:
                self._retornar(callback, "Tempo esgotado ao acessar a API.")
            else:
                self._retornar(callback, f"Erro inesperado: {type(e).__name__}.")

    def _retornar(self, callback, texto):
        from kivy.clock import Clock
        Clock.schedule_once(lambda dt: callback(texto), 0)

    def limpar_historico(self):
        self._historico = []