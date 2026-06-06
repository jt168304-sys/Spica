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


# ── Utilitarios de banco ──────────────────────────────────────────────────────

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


# ── Utilitarios de imagem ─────────────────────────────────────────────────────

def _get_temp_dir():
    try:
        from android.storage import app_storage_path
        pasta = os.path.join(app_storage_path(), "imagens")
    except Exception:
        pasta = os.path.join(os.path.expanduser("~"), "imagens")
    os.makedirs(pasta, exist_ok=True)
    return pasta


def _copiar_da_uri(uri_java):
    """
    Copia conteudo de uma URI Android para arquivo local.
    Usa duas estrategias para maxima compatibilidade.
    """
    try:
        from jnius import autoclass
        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        ctx = PythonActivity.mActivity
        resolver = ctx.getContentResolver()
        pasta = _get_temp_dir()
        destino = os.path.join(pasta, f"img_{int(time.time())}.jpg")

        # ── Estrategia 1: ParcelFileDescriptor → shutil (mais confiavel) ──
        # Evita completamente o problema de bytearray pyjnius
        try:
            pfd = resolver.openFileDescriptor(uri_java, "r")
            raw_fd = pfd.getFd()
            py_fd = os.dup(raw_fd)   # duplica o FD antes de fechar o PFD
            pfd.close()
            with open(py_fd, "rb") as src:
                with open(destino, "wb") as dst:
                    shutil.copyfileobj(src, dst)
            if os.path.exists(destino) and os.path.getsize(destino) > 0:
                print(f"[Spica] Imagem copiada via PFD: {destino}")
                return destino
        except Exception as e1:
            print(f"[Spica] PFD falhou ({e1}), tentando Java IO...")

        # ── Estrategia 2: Java FileOutputStream + buffer Java nativo ──
        # Usa Array.newInstance para criar byte[] Java real (sem conversao Python)
        try:
            FileOutputStream = autoclass("java.io.FileOutputStream")
            Array = autoclass("java.lang.reflect.Array")
            ByteType = autoclass("java.lang.Byte").TYPE
            stream_in = resolver.openInputStream(uri_java)
            stream_out = FileOutputStream(destino)
            buf = Array.newInstance(ByteType, 8192)
            while True:
                n = stream_in.read(buf, 0, 8192)
                if n < 0:
                    break
                stream_out.write(buf, 0, n)
            stream_out.flush()
            stream_in.close()
            stream_out.close()
            if os.path.exists(destino) and os.path.getsize(destino) > 0:
                print(f"[Spica] Imagem copiada via Java IO: {destino}")
                return destino
        except Exception as e2:
            print(f"[Spica] Java IO falhou: {e2}")

    except Exception as e:
        print(f"[Spica] _copiar_da_uri erro geral: {e}")
    return None


# URI da foto fica fora do closure para sobreviver ao retorno da Activity
_uri_foto_camera = [None]


def _abrir_camera(callback):
    try:
        from android.permissions import request_permissions, check_permission, Permission
        from jnius import autoclass
        from android.activity import bind as ab, unbind as aub

        if not check_permission(Permission.CAMERA):
            def _apos(perms, results):
                if results and results[0]:
                    Clock.schedule_once(lambda dt: _abrir_camera(callback), 0.5)
                else:
                    Clock.schedule_once(lambda dt: callback(None), 0)
            request_permissions([Permission.CAMERA], _apos)
            return

        Intent = autoclass("android.content.Intent")
        MediaStore = autoclass("android.provider.MediaStore")
        ContentValues = autoclass("android.content.ContentValues")
        PythonActivity = autoclass("org.kivy.android.PythonActivity")

        ctx = PythonActivity.mActivity
        resolver = ctx.getContentResolver()

        values = ContentValues()
        values.put(MediaStore.Images.Media.DISPLAY_NAME, f"spica_{int(time.time())}.jpg")
        values.put(MediaStore.Images.Media.MIME_TYPE, "image/jpeg")
        _uri_foto_camera[0] = resolver.insert(MediaStore.Images.Media.EXTERNAL_CONTENT_URI, values)

        intent = Intent(MediaStore.ACTION_IMAGE_CAPTURE)
        intent.putExtra(MediaStore.EXTRA_OUTPUT, _uri_foto_camera[0])

        def on_result(req, res, data):
            aub(on_activity_result=on_result)
            uri_salva = _uri_foto_camera[0]
            try:
                if res == -1 and uri_salva is not None:   # RESULT_OK
                    caminho = _copiar_da_uri(uri_salva)
                    Clock.schedule_once(lambda dt: callback(caminho), 0.3)
                    return
            except Exception as e:
                print(f"[Spica] camera on_result: {e}")
            # Cancela ou erro: remove o registro vazio
            try:
                if uri_salva:
                    resolver.delete(uri_salva, None, None)
            except Exception:
                pass
            Clock.schedule_once(lambda dt: callback(None), 0)

        ab(on_activity_result=on_result)
        ctx.startActivityForResult(intent, 102)

    except Exception as e:
        print(f"[Spica] _abrir_camera erro: {e}")
        Clock.schedule_once(lambda dt: callback(None), 0)


def _abrir_seletor(callback):
    try:
        from jnius import autoclass
        from android.activity import bind as ab, unbind as aub
        Intent = autoclass("android.content.Intent")
        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        ctx = PythonActivity.mActivity

        intent = Intent(Intent.ACTION_GET_CONTENT)
        intent.setType("image/*")

        def on_result(req, res, data):
            aub(on_activity_result=on_result)
            try:
                if res == -1 and data is not None:
                    uri = data.getData()
                    if uri:
                        caminho = _copiar_da_uri(uri)
                        Clock.schedule_once(lambda dt: callback(caminho), 0.2)
                        return
            except Exception as e:
                print(f"[Spica] seletor on_result: {e}")
            Clock.schedule_once(lambda dt: callback(None), 0.2)

        ab(on_activity_result=on_result)
        ctx.startActivityForResult(intent, 103)

    except Exception as e:
        print(f"[Spica] _abrir_seletor erro: {e}")
        Clock.schedule_once(lambda dt: callback(None), 0)


# ── Widget de bolha de mensagem ───────────────────────────────────────────────

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
            elevation=2,
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

    # ── Layout ────────────────────────────────────────────────────────────────

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

        # Preview de imagem pendente
        self._preview_box = MDBoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=0,
            padding=[dp(8), 0, dp(8), 0],
            spacing=dp(6),
        )
        raiz.add_widget(self._preview_box)

        # Barra de entrada
        entrada = MDBoxLayout(
            size_hint_y=None,
            height=dp(60),
            padding=[dp(6), dp(6)],
            spacing=dp(2),
        )
        entrada.add_widget(MDIconButton(
            icon="camera-outline",
            icon_size=dp(24),
            on_release=lambda x: self._acao_camera(),
        ))
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

    # ── Boas-vindas ───────────────────────────────────────────────────────────

    def _boas_vindas(self, dt):
        from src.services.groq_service import GroqService
        if GroqService.get_instance().disponivel:
            self._spica("Ola! Sou a Spica \u2736 \u2014 pode me enviar mensagens de texto ou imagens. Como posso ajudar?")
        else:
            self._spica(
                "Ola! Sou a Spica \u2736\n\n"
                "Para ativar a IA, va em \u2699 Configuracoes e insira sua chave da Groq "
                "(console.groq.com \u2014 e gratuito)."
            )

    # ── Envio ─────────────────────────────────────────────────────────────────

    def _enviar(self):
        if self._aguardando:
            return
        texto = self._campo.text.strip()
        if not texto and not self._imagem_pendente:
            return

        from src.services.groq_service import GroqService
        if not GroqService.get_instance().disponivel:
            self._spica("\u2699 Sem API Key \u2014 abra as Configuracoes e insira sua chave Groq.")
            return

        exibir = texto or "\U0001F4F7 Imagem"
        if self._imagem_pendente and texto:
            exibir = f"\U0001F4F7  {texto}"
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

    # ── Camera / Galeria ──────────────────────────────────────────────────────

    def _acao_camera(self):
        if self._aguardando:
            return
        _abrir_camera(self._ao_receber_imagem)

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
        from kivy.uix.image import AsyncImage
        self._limpar_preview()
        self._preview_box.height = dp(84)
        img = AsyncImage(
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
            text="Imagem pronta \u2014 adicione texto ou toque em enviar",
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

    # ── Mensagens ─────────────────────────────────────────────────────────────

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
