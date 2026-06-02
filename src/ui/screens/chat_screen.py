# chat_screen.py
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
    except Exception:
        return False


def _uri_para_arquivo(uri_str):
    """Converte URI content:// para arquivo físico copiando o stream."""
    import time
    try:
        from jnius import autoclass
        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        Uri = autoclass("android.net.Uri")
        ctx = PythonActivity.mActivity
        uri = Uri.parse(str(uri_str))

        # Tenta pegar caminho direto via _data
        try:
            cursor = ctx.getContentResolver().query(uri, None, None, None, None)
            if cursor and cursor.moveToFirst():
                idx = cursor.getColumnIndex("_data")
                if idx >= 0:
                    p = cursor.getString(idx)
                    cursor.close()
                    if p and os.path.exists(p):
                        return p
            if cursor:
                cursor.close()
        except Exception:
            pass

        # Copia stream para arquivo temp
        pasta = "/sdcard/Pictures/Spica"
        os.makedirs(pasta, exist_ok=True)
        destino = os.path.join(pasta, f"img_{int(time.time())}.jpg")
        stream = ctx.getContentResolver().openInputStream(uri)
        with open(destino, "wb") as f:
            buf = bytearray(8192)
            while True:
                n = stream.read(buf)
                if n <= 0:
                    break
                f.write(buf[:n])
        stream.close()
        return destino if os.path.exists(destino) else None
    except Exception:
        return None


def _resolver_caminho(caminho):
    """Resolve caminho ou URI para arquivo físico acessível."""
    if not caminho:
        return None
    s = str(caminho)
    # Já é arquivo físico
    if os.path.exists(s):
        return s
    # É URI do Android
    if s.startswith("content://") or s.startswith("file://"):
        return _uri_para_arquivo(s)
    return None


def _abrir_camera(callback):
    import time
    try:
        from plyer import camera
        pasta = "/sdcard/Pictures/Spica"
        os.makedirs(pasta, exist_ok=True)
        foto = os.path.join(pasta, f"foto_{int(time.time())}.jpg")
        camera.take_picture(
            filename=foto,
            on_complete=lambda p: Clock.schedule_once(
                lambda dt: callback(
                    foto if os.path.exists(foto) else (_resolver_caminho(p) if p else None)
                ), 0.3
            )
        )
    except Exception:
        from kivy.clock import Clock as C; C.schedule_once(lambda dt: callback(f"ERRO:{type(e).__name__}:{e}"), 0)


def _abrir_seletor(callback):
    try:
        from plyer import filechooser
        def _on_sel(sel):
            if not sel:
                Clock.schedule_once(lambda dt: callback(None), 0.2)
                return
            caminho = _resolver_caminho(sel[0])
            Clock.schedule_once(lambda dt: callback(caminho), 0.2)

        filechooser.open_file(
            title="Selecionar imagem",
            filters=[["Imagens", "*.jpg", "*.jpeg", "*.png"]],
            on_selection=_on_sel
        )
    except Exception:
        from kivy.clock import Clock as C; C.schedule_once(lambda dt: callback(f"ERRO:{type(e).__name__}:{e}"), 0)


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
        self._construir_layout()

    def _construir_layout(self):
        raiz = MDBoxLayout(orientation="vertical")

        raiz.add_widget(MDTopAppBar(
            title="Spica",
            left_action_items=[["arrow-left", lambda x: MDApp.get_running_app().navigate_to("home")]],
            right_action_items=[
                ["history",      lambda x: MDApp.get_running_app().navigate_to("historico")],
                ["delete-sweep", lambda x: self._limpar_chat()],
                ["microphone",   lambda x: self._ativar_voz()],
            ],
        ))

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
            size_hint_y=None, height=dp(56),
            padding=[dp(6), dp(4)], spacing=dp(4)
        )
        self.btn_anexo = MDIconButton(
            icon="paperclip",
            size_hint=(None, None), size=(dp(44), dp(44)),
            on_release=self._abrir_opcoes_imagem
        )
        entrada.add_widget(self.btn_anexo)

        self.campo = MDTextField(
            hint_text="Mensagem...", mode="round",
            multiline=False, size_hint_x=1,
            size_hint_y=None, height=dp(44),
        )
        self.campo.bind(on_text_validate=self._enviar)
        entrada.add_widget(self.campo)
        entrada.add_widget(MDIconButton(
            icon="send", size_hint=(None, None), size=(dp(44), dp(44)),
            on_release=self._enviar
        ))
        raiz.add_widget(entrada)
        self.add_widget(raiz)
        Clock.schedule_once(self._boas_vindas, 0.5)

    def _abrir_opcoes_imagem(self, *args):
        from kivymd.uix.dialog import MDDialog
        from kivymd.uix.button import MDFlatButton

        self._dialogo_img = MDDialog(
            title="Adicionar imagem",
            text="Escolha a origem:",
            buttons=[
                MDFlatButton(
                    text="📷  Câmera",
                    on_release=lambda x: (
                        self._dialogo_img.dismiss(),
                        Clock.schedule_once(lambda dt: _abrir_camera(self._imagem_selecionada), 0.4)
                    )
                ),
                MDFlatButton(
                    text="📁  Arquivos",
                    on_release=lambda x: (
                        self._dialogo_img.dismiss(),
                        Clock.schedule_once(lambda dt: _abrir_seletor(self._imagem_selecionada), 0.4)
                    )
                ),
            ]
        )
        self._dialogo_img.open()

    def _imagem_selecionada(self, caminho):
        if not caminho:
            self._wind("Nenhuma imagem selecionada.")
            return
        self.caminho_imagem_selecionada = caminho
        self.btn_anexo.icon = "image-check"
        self.campo.hint_text = f"📸 {os.path.basename(caminho)}"

    def _boas_vindas(self, dt):
        from src.services.groq_service import GroqService
        if GroqService.get_instance().disponivel:
            self._wind("Ola! Sou a Spica, pronta para ajudar!\nUse 📎 para anexar imagens.")
        else:
            self._wind("Ola! Sou a Spica.\n\nVa em Configuracoes e insira sua API key da Groq.")

    def carregar_sessao(self, sessao_id):
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
                self.msgs.add_widget(Bolha(texto=mensagem, autor=autor))
            self._scroll_baixo()
        except Exception as e:
            self.logger.error(f"Erro: {e}")

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
            nome = os.path.basename(str(imagem))
            msg = f"📸 [{nome}]\n{texto}" if texto else f"📸 [{nome}]"
            self._usuario(msg)
            self._salvar_db("usuario", msg)
            self._mostrar_digitando()
            from src.services.groq_service import GroqService
            GroqService.get_instance().perguntar(
                texto or "Analise e descreva esta imagem.",
                self._receber_resposta,
                caminho_imagem=imagem
            )
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
            size_hint=(0.78, None), padding=dp(12), elevation=2,
            radius=[dp(16), dp(16),
                    dp(4 if e_usuario else 16),
                    dp(16 if e_usuario else 4)],
        )
        label = MDLabel(text=texto, size_hint_y=None, font_style="Body2")
        label.bind(texture_size=lambda i, v: setattr(i, "height", v[1] + dp(8)))
        card.bind(minimum_height=card.setter("height"))
        card.add_widget(label)

        espaco = MDBoxLayout(size_hint_x=0.22)
        self.add_widget(espaco if e_usuario else card)
        self.add_widget(card if e_usuario else espaco)
        self.bind(minimum_height=self.setter("height"))
