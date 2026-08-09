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

SYSTEM_PROMPT = """Voce e a Spica, uma amiga virtual de verdade - nao uma atendente, nao uma assistente formal.

Como responder:
- Curta e direto ao ponto a maior parte do tempo. Sem introducao tipo "claro, vou te ajudar" nem fechamento tipo "espero ter ajudado".
- Em assunto leve/casual, pode ser indireta, brincalhona, do jeito que uma amiga de verdade responderia - nao precisa ser sempre literal ou 100% "util" a cada frase.
- So seja completa e detalhada quando for uma pergunta seria de verdade - algo que a pessoa realmente precisa resolver, entender ou decidir.
- Tem opiniao propria: discorda quando faz sentido, implica com leveza, nao fica so concordando com tudo.
- NUNCA recapitule ou resuma a conversa que ja rolou, a menos que peçam isso explicitamente. Trate cada mensagem como continuacao natural, sem repetir o que ja foi dito antes.
- Escreva em texto corrido, SEM markdown: nada de *asterisco*, _sublinhado_, #titulo, listas com traço, ou blocos de codigo. Esse texto as vezes e falado em voz alta, entao formatacao visual nao serve pra nada aqui.
- Se nao tiver certeza sobre algo atual, recente ou que muda com o tempo (noticias, precos, versoes, eventos), pesquise antes de responder em vez de chutar.
Se o usuario enviar uma imagem, analise com atencao e responda exatamente ao que foi pedido."""

SYSTEM_PROMPT_CONTINUO = """Voce e a Spica, e agora esta no modo de escuta continua - uma conversa de verdade,
tipo estar no viva-voz com uma amiga, nao uma troca de comandos formais.

Como responder:
- Trate cada fala como parte de uma conversa em andamento, nao como um pedido isolado.
- Curta a maior parte do tempo. Pode usar pausas, interjeicoes ("hmm", "ah", "opa"), mudar de assunto se a pessoa mudar.
- Nao espere frases "completas" ou formatadas como comando - interprete o contexto e a intencao, mesmo se vier picotado.
- Se a pessoa disser algo casual, tipo comentando sobre o dia dela, reaja como reagiria numa conversa de verdade - nao force uma resposta "util" a cada fala.
- NUNCA recapitule ou resuma a conversa que ja rolou, a menos que peçam isso explicitamente.
- Sem markdown nenhum (nada de *asterisco*, _sublinhado_, #, listas com traço) - isso vai direto pra fala, formatacao visual so atrapalha.
- Continue espirituosa e com personalidade forte, mas no ritmo de bate-papo continuo, nao de pergunta-resposta."""

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

    # Regex de limpeza de markdown, compiladas uma vez só
    _RE_BOLD = re.compile(r"\*\*(.*?)\*\*")
    _RE_ITALIC = re.compile(r"\*(.*?)\*")
    _RE_UNDERSCORE_DUPLA = re.compile(r"__(.*?)__")
    _RE_UNDERSCORE = re.compile(r"_(.*?)_")
    _RE_CODE = re.compile(r"`{1,3}(.*?)`{1,3}", re.DOTALL)
    _RE_HEADER = re.compile(r"^#{1,6}\s*", re.MULTILINE)
    _RE_LISTA = re.compile(r"^[\-\*\+]\s+", re.MULTILINE)
    _RE_SOBRAS = re.compile(r"[*_`#]")
    _RE_QUEBRAS_EXTRAS = re.compile(r"\n{3,}")

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

    def _limpar_formatacao(self, texto: str) -> str:
        """Remove markdown do texto (negrito, listas, headers, código) —
        o app não renderiza markdown visualmente (é texto puro na tela) e
        às vezes esse texto é falado em voz alta, então símbolos como
        asterisco/sublinhado só atrapalham (e o TTS narra o símbolo)."""
        if not texto:
            return texto
        t = texto
        t = self._RE_BOLD.sub(r"\1", t)
        t = self._RE_ITALIC.sub(r"\1", t)
        t = self._RE_UNDERSCORE_DUPLA.sub(r"\1", t)
        t = self._RE_UNDERSCORE.sub(r"\1", t)
        t = self._RE_CODE.sub(r"\1", t)
        t = self._RE_HEADER.sub("", t)
        t = self._RE_LISTA.sub("", t)
        t = self._RE_SOBRAS.sub("", t)  # qualquer símbolo remanescente
        t = self._RE_QUEBRAS_EXTRAS.sub("\n\n", t)
        return t.strip()

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
        # Carregado uma vez aqui só como valor inicial — a cada pergunta,
        # _chamar_api relê do Storage (que agora sempre busca do disco) pra
        # garantir que o histórico está com as mensagens mais recentes,
        # mesmo que tenham vindo de outro processo (Activity vs service.py).
        self._historico: List[Dict] = self.storage.get("historico_conversa", [])
        self._cache_imagens = {}
        self.MAX_HISTORICO = 300
        self.WINDOW_API = 10
        # ATUALIZADO: 35s era curto demais pro groq/compound, que pode fazer
        # até 10 chamadas de ferramenta (busca web, visitar site) numa única
        # requisição — isso passava de 35s com frequência, derrubando a
        # busca web por timeout bem na hora que ela mais precisava pesquisar.
        self.TIMEOUT_API = 60

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

            # Sistema de memória via cache compartilhado: relê o histórico do
            # disco (Storage já faz isso sempre fresco agora) antes de montar
            # a mensagem, pra garantir que estamos vendo a conversa mais
            # recente mesmo se ela veio de outro processo (chat aberto vs
            # bolha em segundo plano). Isso ataca direto a causa mais provável
            # da Spica parecer "recapitular"/perder o fio da conversa.
            self._historico = self.storage.get("historico_conversa", [])

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
                # Reduzido de 1024 pra 700 como trava extra contra textão —
                # o prompt já pede brevidade, isso é reforço, não a solução
                # principal (uma resposta séria de verdade ainda cabe em 700).
                "max_tokens": 700,
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
            from src.utils.service_log import slog
            slog(f"Groq respondeu HTTP {resp.status_code}, texto bruto: {resposta[:60]!r}")
            # Remove tags de raciocínio de alguns modelos
            resposta = re.sub(r"<think>.*?</think>", "", resposta, flags=re.DOTALL).strip()

            # Sistema de humor: a IA se autoclassifica no final da resposta com
            # [HUMOR:xxx] — aqui a tag é extraída (removida do texto que o usuário
            # vê/ouve) e a expressão correspondente é disparada na bolha.
            resposta, nome_expressao = self.mood.extrair_humor(resposta)
            if nome_expressao:
                try:
                    from src.services.overlay import SpicaOverlay
                    SpicaOverlay.aplicar_humor(nome_expressao)
                except Exception as e:
                    self.logger.error(f"[Spica/Humor] Falha ao aplicar expressão: {e}")

            # Limpa markdown (negrito, listas, etc) — o app não renderiza isso
            # visualmente, e o texto às vezes é falado em voz alta, então
            # símbolos tipo * e _ só atrapalhavam (o TTS chegava a narrar
            # "asterisco").
            resposta = self._limpar_formatacao(resposta)

            self._historico.append({"role": "assistant", "content": resposta})
            self.storage.set("historico_conversa", self._historico)
            retornar(resposta)

        except Exception as e:
            try:
                from src.utils.service_log import slog
                slog(f"EXCEÇÃO em _chamar_api: {type(e).__name__}: {e}")
            except Exception:
                pass
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
