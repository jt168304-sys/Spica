# chat_screen.py — Chat com Spica + Histórico SQLite
import os
import sqlite3
from datetime import datetime
from kivy.metrics import dp
from kivy.clock import Clock
from kivy.uix.scrollview import ScrollView
from kivymd.uix.screen import MDScreen
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel
from kivymd.uix.textfield import MDTextField
from kivymd.uix.button import MDIconButton
from kivymd.uix.toolbar import MDTopAppBar
from kivymd.uix.filemanager import MDFileManager
from kivymd.app import MDApp
from src.modules.commands import CommandProcessor
from src.utils.logger import WindLogger


def _get_db_path():
    try:
        from android.storage import app_storage_path
        base = app_storage_path()
    except Exception:
        base = os.path.expanduser("~")
    return os.path.join(base, "spica_historico.db")


def _init_db(db_path):
    try:
        con = sqlite3.connect(db_path)
        con.execute("""
            CREATE TABLE IF NOT EXISTS chats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sessao TEXT NOT NULL,
                autor TEXT NOT NULL,
                mensagem TEXT NOT NULL,
                ts TEXT NOT NULL
            )
        """)
        con.commit()
        con.close()
        return True
    except Exception as e:
        return False


class ChatScreen(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.logger = WindLogger()
        self.processor = CommandProcessor.get_instance()
        self._bolha_digitando = None
        self.caminho_imagem_selecionada = None
        self.sessao_id = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.db_path = _get_db_path()
        self.db_ok = _init_db(self.db_path)

        self.file_manager = MDFileManager(
            exit_manager=self._fechar_gerenciador,
            select_path=self._imagem_selecionada,
            preview=True
        )
        self._construir_layout()

    def _construir_layout(self):
        raiz = MDBoxLayout(orientation="vertical")

        self._toolbar = MDTopAppBar(
            title="Spica",
            left_action_items=[["arrow-left", lambda x: MDApp.get_running_app().navigate_to("home")]],
            right_action_items=[
                ["history", lambda x: MDApp.get_running_app().navigate_to("historico")],
                ["delete-sweep", lambda x: self._limpar_chat()],
                ["microphone", lambda x: self._ativar_voz()],
            ],
        )
        raiz.add_widget(self._toolbar)

        # ScrollView - touch_multiselect permite rolar sobre os textos
        self.scroll = ScrollView(
            always_overscroll=False,
            do_scroll_x=False,
            scroll_type=["bars", "content"],
            bar_width=dp(4),
        )
        self.msgs = MDBoxLayout(
            orientation="vertical",
            size_hint_y=None,
            padding=dp(12),
            spacing=dp(8)
        )
        self.msgs.bind(minimum_height=self.msgs.setter("height"))
        self.scroll.add_widget(self.msgs)
        raiz.add_widget(self.scroll)

        entrada = MDBoxLayout(
            size_hint_y=None,
            height=dp(60),
            padding=[dp(8), dp(4)],
            spacing=dp(4)
        )
        self.btn_anexo = MDIconButton(icon="paperclip", on_release=self._abrir_gerenciador)
        entrada.add_widget(self.btn_anexo)

        self.campo = MDTextField(
            hint_text="Mensagem...",
            mode="round",
            multiline=False,
            size_hint_x=1,
        )
        self.campo.bind(on_text_validate=self._enviar)
        entrada.add_widget(self.campo)
        entrada.add_widget(MDIconButton(icon="send", on_release=self._enviar))
        raiz.add_widget(entrada)

        self.add_widget(raiz)
        Clock.schedule_once(self._boas_vindas, 0.5)

    def _abrir_gerenciador(self, *args):
        pasta = "/sdcard" if os.path.exists("/sdcard") else os.path.expanduser("~")
        self.file_manager.show(pasta)

    def _fechar_gerenciador(self, *args):
        self.file_manager.close()

    def _imagem_selecionada(self, caminho):
        self._fechar_gerenciador()
        ext = os.path.splitext(caminho)[1].lower()
        if ext in ['.png', '.jpg', '.jpeg']:
            self.caminho_imagem_selecionada = caminho
            self.btn_anexo.icon = "image-check"
            self.campo.hint_text = "Imagem pronta! Faca sua pergunta..."
        else:
            self.campo.hint_text = "Formato invalido! Use JPG ou PNG."

    def _boas_vindas(self, dt):
        from src.services.groq_service import GroqService
        if GroqService.get_instance().disponivel:
            self._wind("Ola! Sou a Spica, pronta para ajudar!")
        else:
            self._wind("Ola! Sou a Spica.\n\nVa em Configuracoes e insira sua API key da Groq.")

    def carregar_sessao(self, sessao_id):
        """Carrega mensagens de uma sessão anterior."""
        self.msgs.clear_widgets()
        self.sessao_id = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        try:
            con = sqlite3.connect(self.db_path)
            rows = con.execute(
                "SELECT autor, mensagem FROM chats WHERE sessao=? ORDER BY ts ASC",
                (sessao_id,)
            ).fetchall()
            con.close()
            for autor, mensagem in rows:
                if autor == "usuario":
                    self.msgs.add_widget(Bolha(texto=mensagem, autor="usuario"))
                else:
                    self.msgs.add_widget(Bolha(texto=mensagem, autor="wind"))
            self._scroll_baixo()
        except Exception as e:
            self.logger.error(f"Erro ao carregar sessao: {e}")

    def _enviar(self, *args):
        texto = self.campo.text.strip()
        imagem = self.caminho_imagem_selecionada
        if not texto and not imagem:
            return

        self.campo.text = ""
        self.caminho_imagem_selecionada = None
        self.btn_anexo.icon = "paperclip"
        self.campo.hint_text = "Mensagem..."

        if imagem:
            nome = os.path.basename(imagem)
            msg = f"[Imagem: {nome}]\n{texto}"
            self._usuario(msg)
            self._salvar_db("usuario", msg)
            self._mostrar_digitando()
            from src.services.groq_service import GroqService
            GroqService.get_instance().perguntar(texto, self._receber_resposta, caminho_imagem=imagem)
        else:
            self._usuario(texto)
            self._salvar_db("usuario", texto)
            self._mostrar_digitando()
            self.processor.processar(texto, callback=self._receber_resposta)

    def _receber_resposta(self, resposta):
        self._remover_digitando()
        self._wind(resposta)
        self._salvar_db("spica", resposta)

    def _salvar_db(self, autor, mensagem):
        if not self.db_ok:
            return
        try:
            con = sqlite3.connect(self.db_path)
            con.execute(
                "INSERT INTO chats (sessao, autor, mensagem, ts) VALUES (?,?,?,?)",
                (self.sessao_id, autor, mensagem, datetime.now().isoformat())
            )
            con.commit()
            con.close()
        except Exception as e:
            self.logger.error(f"DB error: {e}")

    def _usuario(self, texto):
        self.msgs.add_widget(Bolha(texto=texto, autor="usuario"))
        self._scroll_baixo()

    def _wind(self, texto):
        self.msgs.add_widget(Bolha(texto=texto, autor="wind"))
        self._scroll_baixo()

    def _mostrar_digitando(self):
        self._bolha_digitando = Bolha(texto="...", autor="wind")
        self.msgs.add_widget(self._bolha_digitando)
        self._scroll_baixo()

    def _remover_digitando(self):
        if self._bolha_digitando and self._bolha_digitando in self.msgs.children:
            self.msgs.remove_widget(self._bolha_digitando)
        self._bolha_digitando = None

    def _limpar_chat(self):
        self.msgs.clear_widgets()
        from src.services.groq_service import GroqService
        GroqService.get_instance().limpar_historico()
        self.sessao_id = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self._wind("Chat limpo! Como posso ajudar?")

    def _scroll_baixo(self):
        Clock.schedule_once(lambda dt: setattr(self.scroll, "scroll_y", 0), 0.15)

    def _ativar_voz(self):
        from src.services.voice_service import VoiceService
        app = MDApp.get_running_app()
        if hasattr(app, "bubble"):
            app.bubble.pulsar()
        VoiceService.get_instance().ouvir(callback=lambda t: (
            self._usuario(t),
            self._salvar_db("usuario", t),
            self._mostrar_digitando(),
            self.processor.processar(t, self._receber_resposta)
        ))


class Bolha(MDBoxLayout):
    def __init__(self, texto, autor, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "horizontal"
        self.size_hint_y = None
        self.padding = [dp(4), dp(2)]

        e_usuario = (autor == "usuario")
        card = MDCard(
            size_hint=(0.78, None),
            padding=dp(12),
            elevation=2,
            radius=[dp(16), dp(16), dp(4 if e_usuario else 16), dp(16 if e_usuario else 4)],
        )
        label = MDLabel(text=texto, size_hint_y=None, font_style="Body2")
        label.bind(texture_size=lambda i, v: setattr(i, "height", v[1] + dp(8)))
        card.bind(minimum_height=card.setter("height"))
        card.add_widget(label)

        espaco = MDBoxLayout(size_hint_x=0.22)
        self.add_widget(espaco if e_usuario else card)
        self.add_widget(card if e_usuario else espaco)
        self.bind(minimum_height=self.setter("height"))
