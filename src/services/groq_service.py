# groq_service.py — Integração com Groq API (Texto + Visão)
import threading
import json
import base64
import os
import time
import shutil
from typing import Optional, Callable, List, Dict
from src.utils.logger import WindLogger
from src.config.settings import Settings

SYSTEM_PROMPT = """Você é Spica, uma assistente virtual inteligente, direta e com personalidade marcante.
Responde em português brasileiro, de forma natural e descontraída.
É eficiente: vai direto ao ponto, sem enrolação.
Se o usuário enviar uma imagem, analise-a com atenção e responda exatamente ao que foi pedido."""


def _pasta_imagens():
    try:
        from android.storage import app_storage_path
        p = os.path.join(app_storage_path(), "imagens")
    except Exception:
        p = os.path.join(os.path.expanduser("~"), "imagens")
    os.makedirs(p, exist_ok=True)
    return p


def _copiar_uri_para_arquivo(uri_str: str) -> str:
    """
    Copia conteúdo de uma URI Android para arquivo local.
    Três estratégias em cascata para máxima compatibilidade.
    CORREÇÃO: usa os.fdopen() em vez de open() com file descriptor inteiro.
    """
    destino = os.path.join(_pasta_imagens(), f"img_{int(time.time())}.jpg")
    print(f"[Spica/groq] URI: {uri_str} → {destino}")

    try:
        from jnius import autoclass
        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        Uri = autoclass("android.net.Uri")
        ctx = PythonActivity.mActivity
        resolver = ctx.getContentResolver()
        uri_java = Uri.parse(uri_str)

        # Estratégia 1 — Java NIO Files.copy (Android 8+)
        try:
            Files = autoclass("java.nio.file.Files")
            Paths = autoclass("java.nio.file.Paths")
            istream = resolver.openInputStream(uri_java)
            Files.copy(istream, Paths.get(destino))
            istream.close()
            if os.path.exists(destino) and os.path.getsize(destino) > 0:
                print(f"[Spica/groq] NIO OK — {os.path.getsize(destino)} bytes")
                return destino
        except Exception as e1:
            print(f"[Spica/groq] NIO falhou: {e1}")

        # Estratégia 2 — ParcelFileDescriptor com os.fdopen (CORRIGIDO)
        try:
            pfd = resolver.openFileDescriptor(uri_java, "r")
            if pfd is not None:
                py_fd = os.dup(pfd.getFd())
                pfd.close()
                with os.fdopen(py_fd, "rb") as src, open(destino, "wb") as dst:
                    shutil.copyfileobj(src, dst)
                if os.path.exists(destino) and os.path.getsize(destino) > 0:
                    print(f"[Spica/groq] PFD OK — {os.path.getsize(destino)} bytes")
                    return destino
        except Exception as e2:
            print(f"[Spica/groq] PFD falhou: {e2}")

        # Estratégia 3 — Bitmap com inSampleSize (evita OOM em fotos grandes)
        try:
            BitmapFactory = autoclass("android.graphics.BitmapFactory")
            BitmapOptions = autoclass("android.graphics.BitmapFactory$Options")
            CompFmt = autoclass("android.graphics.Bitmap$CompressFormat")
            FileOutStream = autoclass("java.io.FileOutputStream")

            opts_check = BitmapOptions()
            opts_check.inJustDecodeBounds = True
            istream_check = resolver.openInputStream(uri_java)
            BitmapFactory.decodeStream(istream_check, None, opts_check)
            istream_check.close()

            w, h = opts_check.outWidth, opts_check.outHeight
            sample = 1
            while (w // sample) > 2048 or (h // sample) > 2048:
                sample *= 2

            opts_dec = BitmapOptions()
            opts_dec.inSampleSize = sample
            istream2 = resolver.openInputStream(uri_java)
            bm = BitmapFactory.decodeStream(istream2, None, opts_dec)
            istream2.close()

            if bm is not None:
                fos = FileOutStream(destino)
                bm.compress(CompFmt.JPEG, 85, fos)
                fos.flush()
                fos.close()
                bm.recycle()
                if os.path.exists(destino) and os.path.getsize(destino) > 0:
                    print(f"[Spica/groq] Bitmap OK — {os.path.getsize(destino)} bytes")
                    return destino
        except Exception as e3:
            print(f"[Spica/groq] Bitmap falhou: {e3}")

    except Exception as e:
        print(f"[Spica/groq] _copiar_uri_para_arquivo erro geral: {e}")

    return ""


def _resolver_caminho_imagem(caminho: str) -> str:
    if not caminho:
        return ""
    if os.path.exists(caminho):
        return caminho
    if caminho.startswith("content://") or caminho.startswith("file://"):
        return _copiar_uri_para_arquivo(caminho)
    return caminho


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

    @property
    def api_key(self): return self.settings.get("api_key", "").strip()

    @property
    def disponivel(self): return bool(self.api_key)

    def _obter_mime_type(self, caminho: str) -> str:
        ext = os.path.splitext(caminho)[1].lower()
        if ext in ['.jpg', '.jpeg']: return 'image/jpeg'
        if ext == '.png': return 'image/png'
        if ext == '.webp': return 'image/webp'
        return 'image/jpeg'

    def _converter_para_base64(self, caminho: str) -> str:
        try:
            if not os.path.exists(caminho) or os.path.getsize(caminho) == 0:
                return ""
            with open(caminho, "rb") as f:
                return base64.b64encode(f.read()).decode('utf-8')
        except Exception as e:
            self.logger.error(f"Erro base64: {e}")
            return ""

    def perguntar(self, mensagem: str, callback: Callable[[str], None], caminho_imagem: str = None):
        if not self.disponivel:
            callback("Sem API key. Va em Configuracoes e insira sua chave Groq.")
            return
        threading.Thread(
            target=self._chamar_api,
            args=(mensagem, callback, caminho_imagem),
            daemon=True
        ).start()

    def _chamar_api(self, mensagem: str, callback: Callable[[str], None], caminho_imagem: str = None):
        try:
            import requests, urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

            caminho_resolvido = None
            if caminho_imagem:
                caminho_resolvido = _resolver_caminho_imagem(caminho_imagem)
                if not caminho_resolvido or not os.path.exists(caminho_resolvido):
                    self.logger.error(f"Imagem nao encontrada: {caminho_imagem}")
                    caminho_resolvido = None

            mensagens_formatadas = [{"role": "system", "content": SYSTEM_PROMPT}]

            if caminho_resolvido:
                modelo_atual = self.MODEL_VISAO
                img_b64 = self._converter_para_base64(caminho_resolvido)
                if not img_b64:
                    self._retornar(callback, "Erro ao processar a imagem. Use JPEG ou PNG.")
                    return
                mime_type = self._obter_mime_type(caminho_resolvido)
                for msg in self._historico[-6:]:
                    txt = msg["content"]
                    if isinstance(txt, list):
                        txt = txt[0]["text"] if txt else ""
                    mensagens_formatadas.append({"role": msg["role"], "content": [{"type": "text", "text": str(txt)}]})
                mensagens_formatadas.append({
                    "role": "user",
                    "content": [
                        {"type": "text", "text": mensagem or "Analise e descreva esta imagem."},
                        {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{img_b64}"}}
                    ]
                })
                self._historico.append({"role": "user", "content": f"[Imagem] {mensagem}"})
            else:
                modelo_atual = self.MODEL_TEXTO
                self._historico.append({"role": "user", "content": mensagem})
                for msg in self._historico[-12:]:
                    txt = msg["content"]
                    if isinstance(txt, list):
                        txt = txt[0]["text"] if txt else ""
                    mensagens_formatadas.append({"role": msg["role"], "content": str(txt)})

            payload = {
                "model": modelo_atual,
                "messages": mensagens_formatadas,
                "max_tokens": 1024,
                "temperature": 0.5 if caminho_resolvido else 0.7,
            }

            resp = requests.post(
                self.URL,
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json=payload,
                timeout=35,
                verify=False,
            )

            if resp.status_code == 401:
                self._retornar(callback, "API key invalida. Verifique em Configuracoes.")
                return
            if resp.status_code == 429:
                self._retornar(callback, "Limite de requisicoes atingido. Aguarde.")
                return
            if resp.status_code != 200:
                self._retornar(callback, f"Erro na API ({resp.status_code}). Tente novamente.")
                return

            resposta = resp.json()["choices"][0]["message"]["content"].strip()
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
