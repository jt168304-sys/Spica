# chat_screen.py — Chat principal do Spica
import os
import time
import shutil
import sqlite3
from datetime import datetime
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.uix.scrollview import ScrollView
from kivymd.uix.screen import MDScreen
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel
from kivymd.uix.textfield import MDTextField
from kivymd.uix.button import MDIconButton
from kivymd.uix.toolbar import MDTopAppBar
from kivymd.app import MDApp


# ── Banco ─────────────────────────────────────────────────────────────────────

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
                sessao TEXT, autor TEXT, mensagem TEXT, ts TEXT
            )
        """)
        con.commit()
        con.close()
    except Exception:
        pass


# ── Diretorio interno para imagens ────────────────────────────────────────────

def _get_pasta_imagens():
    try:
        from android.storage import app_storage_path
        pasta = os.path.join(app_storage_path(), "imagens")
    except Exception:
        pasta = os.path.join(os.path.expanduser("~"), "imagens")
    os.makedirs(pasta, exist_ok=True)
    return pasta


# ── Seletor de galeria ────────────────────────────────────────────────────────

def _abrir_seletor(callback):
    """
    Abre seletor de imagens.  on_result apenas guarda a URI como string
    (trabalho minimo na callback) e delega a copia para a thread Kivy.
    """
    try:
        from jnius import autoclass
        from android.activity import bind as ab, unbind as aub
        Intent = autoclass("android.content.Intent")
        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        ctx = PythonActivity.mActivity

        intent = Intent(Intent.ACTION_GET_CONTENT)
        intent.setType("image/*")
        intent.addCategory(Intent.CATEGORY_OPENABLE)

        def on_result(req, res, data):
            uri_str = None
            try:
                aub(on_activity_result=on_result)
            except Exception:
                pass
            try:
                if res == -1 and data is not None:
                    uri = data.getData()
                    if uri is not None:
                        uri_str = uri.toString()
            except Exception as e:
                print(f"[Spica] on_result: {e}")

            if uri_str:
                Clock.schedule_once(
                    lambda dt: _copiar_uri_e_retornar(uri_str, callback), 0.3
                )
            else:
                Clock.schedule_once(lambda dt: callback(None), 0.3)

        ab(on_activity_result=on_result)
        ctx.startActivityForResult(intent, 103)

    except Exception as e:
        print(f"[Spica] _abrir_seletor: {e}")
        Clock.schedule_once(lambda dt: callback(None), 0)


def _copiar_uri_e_retornar(uri_str, callback):
    """Copia a imagem para storage interna e chama callback com o caminho real."""
    caminho = None
    try:
        from jnius import autoclass
        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        Uri = autoclass("android.net.Uri")
        ctx = PythonActivity.mActivity
        resolver = ctx.getContentResolver()
        uri_java = Uri.parse(uri_str)

        pasta = _get_pasta_imagens()
        destino = os.path.join(pasta, f"img_{int(time.time())}.jpg")

        # Estrategia: ParcelFileDescriptor → shutil (Python puro, sem bugs de bytearray)
        pfd = resolver.openFileDescriptor(uri_java, "r")
        if pfd is not None:
            py_fd = os.dup(pfd.getFd())
            pfd.close()
            with open(py_fd, "rb") as src, open(destino, "wb") as dst:
                shutil.copyfileobj(src, dst)
            if os.path.exists(destino) and os.path.getsize(destino) > 0:
                caminho = destino
                print(f"[Spica] Imagem copiada: {destino}")

    except Exception as e:
        print(f"[Spica] _copiar_uri_e_retornar: {e}")

    callback(caminho)


# ── Widget bolha de mensagem ──────────────────────────────────────────────────

class Bolha(MDBoxLayout):
    def __init__(self, texto, autor, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "horizontal"
        self.size_hint_y = None
        self.padding = [dp(4), dp(2)]

        e_usuario = (autor == "usuario")
        card = MDCard(
            size_hint=(0.82, None),
            padding=dp(12),
            elevation=0,
            radius=[
                dp(16), dp(16),
                dp(4 if e_usuario else 16),
                dp(16 if e_usuario else 4),
            ],
            md_bg_color=[0.15, 0.38, 0.72, 1] if e_usuario else [0.18, 0.18, 0.24, 1],
        )
        label = MDLabel(
            text=texto,
            size_hint_y=None,
            font_style="Body2",
            theme_text_color="Custom",
            text_color=[1, 1, 1, 1],
        )
        label.bind(texture_size=lambda i, v: setattr(i, "height", v[1] + dp(8)))
        label.bind(width=lambda i, w: setattr(i, "text_size", (w, None)))
        card.bind(minimum_height=card.setter("height"))
        card.add_widget(label)

        espaco = MDBoxLayout(size_hint_x=0.18)
        self.add_widget(espaco if e_usuario else card)
        self.add_widget(card if e_usuario else espaco)
        self.bind(minimum_height=self.setter("height"))


# ── Tela de chat ──────────────────────────────────────────────────────────────

class ChatScreen(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._sessao = datetime.now().strftime("%Y%m%d_%H%M%S")
        _init_db(_get_db_path())
        self._imagem_pendente = None
        self._aguardando = False
        self._bolha_digitando = None
        self._construir_layout()
        Clock.schedule_once(self._boas_vindas, 0.4)

    def _construir_layout(self):
        raiz = MDBoxLayout(orientation="vertical")
        raiz.add_widget(MDTopAppBar(
            title="Spica \u2736",
            right_action_items=[
                ["cog-outline",          lambda x: MDApp.get_running_app().navigate_to("configuracoes")],
                ["delete-sweep-outline", lambda x: self._limpar_chat()],
            ],
        ))

        self._scroll = ScrollView(do_scroll_x=False)
        self._msgs = MDBoxLayout(
            orientation="vertical",
            size_hint_y=None,
            padding=dp(10),
            spacing=dp(8),
        )
        self._msgs.bind(minimum_height=self._msgs.setter("height"))
        self._scroll.add_widget(self._msgs)
        raiz.add_widget(self._scroll)

        self._preview_box = MDBoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=0,
            padding=[dp(8), 0, dp(8), 0],
            spacing=dp(6),
        )
        raiz.add_widget(self._preview_box)

        entrada = MDBoxLayout(
            size_hint_y=None,
            height=dp(60),
            padding=[dp(6), dp(6)],
            spacing=dp(2),
        )
        entrada.add_widget(MDIconButton(
            icon="image-outline",
            icon_size=dp(24),
            on_release=lambda x: self._acao_galeria(),
        ))
        self._campo = MDTextField(
            hint_text="Mensagem...",
            mode="round",
            multiline=False,
            size_hint_x=1,
        )
        self._campo.bind(on_text_validate=lambda x: self._enviar())
        entrada.add_widget(self._campo)
        entrada.add_widget(MDIconButton(
            icon="send",
            icon_size=dp(24),
            theme_icon_color="Custom",
            icon_color=[0.25, 0.55, 1.0, 1],
            on_release=lambda x: self._enviar(),
        ))
        raiz.add_widget(entrada)
        self.add_widget(raiz)

    def _boas_vindas(self, dt):
        from src.services.groq_service import GroqService
        if GroqService.get_instance().disponivel:
            self._spica("Ola! Sou a Spica \u2736 \u2014 me mande texto ou imagens. Como posso ajudar?")
        else:
            self._spica(
                "Ola! Sou a Spica \u2736\n\n"
                "Va em \u2699 Configuracoes e insira sua chave Groq "
                "(console.groq.com \u2014 gratuito)."
            )

    def _enviar(self):
        if self._aguardando:
            return
        texto = self._campo.text.strip()
        if not texto and not self._imagem_pendente:
            return

        from src.services.groq_service import GroqService
        if not GroqService.get_instance().disponivel:
            self._spica("\u2699 Sem API Key \u2014 va em Configuracoes e insira sua chave Groq.")
            return

        exibir = texto or "\U0001F5BC Imagem"
        if self._imagem_pendente and texto:
            exibir = f"\U0001F5BC {texto}"
        self._usuario(exibir)

        img = self._imagem_pendente
        self._imagem_pendente = None
        self._limpar_preview()
        self._campo.text = ""
        self._aguardando = True
        self._mostrar_digitando()

        GroqService.get_instance().perguntar(
            mensagem=texto or "Descreva e analise esta imagem detalhadamente.",
            callback=self._receber_resposta,
            caminho_imagem=img,
        )

    def _receber_resposta(self, resposta):
        self._remover_digitando()
        self._aguardando = False
        self._spica(resposta)

    def _acao_galeria(self):
        if self._aguardando:
            return
        _abrir_seletor(self._ao_receber_imagem)

    def _ao_receber_imagem(self, caminho):
        if not caminho or not os.path.exists(caminho):
            self._spica("Nao consegui carregar a imagem. Tente novamente.")
            return
        self._imagem_pendente = caminho
        self._mostrar_preview(caminho)

    def _mostrar_preview(self, caminho):
        from kivy.uix.image import Image as KivyImage
        self._limpar_preview()
        self._preview_box.height = dp(84)
        img = KivyImage(
            source=caminho,
            size_hint=(None, None),
            size=(dp(72), dp(72)),
            allow_stretch=True,
            keep_ratio=True,
        )
        btn_rem = MDIconButton(
            icon="close-circle-outline",
            icon_size=dp(20),
            size_hint=(None, None),
            size=(dp(36), dp(36)),
            on_release=lambda x: self._remover_imagem(),
        )
        lbl = MDLabel(
            text="Imagem pronta \u2014 escreva algo ou envie direto",
            font_style="Caption",
            theme_text_color="Secondary",
        )
        self._preview_box.add_widget(img)
        self._preview_box.add_widget(btn_rem)
        self._preview_box.add_widget(lbl)

    def _limpar_preview(self):
        self._preview_box.clear_widgets()
        self._preview_box.height = 0

    def _remover_imagem(self):
        self._imagem_pendente = None
        self._limpar_preview()

    def _usuario(self, texto):
        self._msgs.add_widget(Bolha(texto=texto, autor="usuario"))
        self._rolar_baixo()

    def _spica(self, texto):
        self._msgs.add_widget(Bolha(texto=texto, autor="spica"))
        self._rolar_baixo()

    def _mostrar_digitando(self):
        self._bolha_digitando = Bolha(texto="\u2022  \u2022  \u2022", autor="spica")
        self._msgs.add_widget(self._bolha_digitando)
        self._rolar_baixo()

    def _remover_digitando(self):
        if self._bolha_digitando and self._bolha_digitando in self._msgs.children:
            self._msgs.remove_widget(self._bolha_digitando)
        self._bolha_digitando = None

    def _rolar_baixo(self):
        Clock.schedule_once(lambda dt: setattr(self._scroll, "scroll_y", 0), 0.1)

    def _limpar_chat(self):
        self._msgs.clear_widgets()
        self._imagem_pendente = None
        self._aguardando = False
        self._bolha_digitando = None
        self._limpar_preview()
        self._sessao = datetime.now().strftime("%Y%m%d_%H%M%S")
        from src.services.groq_service import GroqService
        GroqService.get_instance().limpar_historico()
        Clock.schedule_once(lambda dt: self._spica("Chat limpo! Como posso ajudar?"), 0.1)
