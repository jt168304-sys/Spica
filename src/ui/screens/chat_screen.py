# chat_screen.py — Chat principal do Spica
import os
import time
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


# ── Storage interno ───────────────────────────────────────────────────────────

def _pasta_imagens():
    try:
        from android.storage import app_storage_path
        p = os.path.join(app_storage_path(), "imgs")
    except Exception:
        p = os.path.join(os.path.expanduser("~"), "imgs")
    os.makedirs(p, exist_ok=True)
    return p


# ── Seletor de imagem ─────────────────────────────────────────────────────────

def _abrir_seletor(callback):
    """
    Seleciona imagem via ACTION_GET_CONTENT.
    on_result guarda so a URI (string) e delega tudo para a thread Kivy.
    """
    try:
        from jnius import autoclass
        from android.activity import bind as ab, unbind as aub
        Intent      = autoclass("android.content.Intent")
        PythonAct   = autoclass("org.kivy.android.PythonActivity")
        ctx         = PythonAct.mActivity

        intent = Intent(Intent.ACTION_GET_CONTENT)
        intent.setType("image/*")
        intent.addCategory(Intent.CATEGORY_OPENABLE)

        def on_result(req, res, data):
            uri_str = None
            try:
                aub(on_activity_result=on_result)
            except BaseException:
                pass
            try:
                if res == -1 and data is not None:
                    uri = data.getData()
                    if uri is not None:
                        uri_str = uri.toString()
            except BaseException as e:
                print(f"[Spica] on_result uri: {e}")

            if uri_str:
                Clock.schedule_once(
                    lambda dt, u=uri_str: _copiar_imagem(u, callback), 0.4
                )
            else:
                Clock.schedule_once(lambda dt: callback(None), 0.3)

        ab(on_activity_result=on_result)
        ctx.startActivityForResult(intent, 103)

    except Exception as e:
        print(f"[Spica] _abrir_seletor: {e}")
        Clock.schedule_once(lambda dt: callback(None), 0)


def _copiar_imagem(uri_str, callback):
    """Copia via Java NIO Files.copy — sem bytearray, sem PFD mode issues."""
    caminho = None
    try:
        from jnius import autoclass
        PythonAct = autoclass("org.kivy.android.PythonActivity")
        Uri       = autoclass("android.net.Uri")
        ctx       = PythonAct.mActivity
        resolver  = ctx.getContentResolver()
        uri_java  = Uri.parse(uri_str)

        destino = os.path.join(_pasta_imagens(), f"img_{int(time.time())}.jpg")

        # Tentativa 1 — Java NIO Files.copy (Android 8+, API 26)
        try:
            Files = autoclass("java.nio.file.Files")
            Paths = autoclass("java.nio.file.Paths")
            istream = resolver.openInputStream(uri_java)
            Files.copy(istream, Paths.get(destino))
            istream.close()
            if os.path.exists(destino) and os.path.getsize(destino) > 0:
                caminho = destino
                print("[Spica] NIO OK")
        except Exception as e1:
            print(f"[Spica] NIO: {e1}")

        # Tentativa 2 — ParcelFileDescriptor (se Files.copy nao funcionar)
        if not caminho:
            try:
                import shutil
                pfd = resolver.openFileDescriptor(uri_java, "r")
                if pfd is not None:
                    py_fd = os.dup(pfd.getFd())
                    pfd.close()
                    with open(py_fd, "rb") as src, open(destino, "wb") as dst:
                        shutil.copyfileobj(src, dst)
                    if os.path.exists(destino) and os.path.getsize(destino) > 0:
                        caminho = destino
                        print("[Spica] PFD OK")
            except Exception as e2:
                print(f"[Spica] PFD: {e2}")

        # Tentativa 3 — Bitmap (ultima opcao)
        if not caminho:
            try:
                BitmapFactory = autoclass("android.graphics.BitmapFactory")
                CompFmt       = autoclass("android.graphics.Bitmap$CompressFormat")
                FileOutStream = autoclass("java.io.FileOutputStream")
                istream2 = resolver.openInputStream(uri_java)
                bm = BitmapFactory.decodeStream(istream2)
                istream2.close()
                if bm is not None:
                    fos = FileOutStream(destino)
                    bm.compress(CompFmt.JPEG, 90, fos)
                    fos.flush()
                    fos.close()
                    bm.recycle()
                    if os.path.exists(destino) and os.path.getsize(destino) > 0:
                        caminho = destino
                        print("[Spica] Bitmap OK")
            except Exception as e3:
                print(f"[Spica] Bitmap: {e3}")

    except BaseException as e:
        print(f"[Spica] _copiar_imagem geral: {e}")

    callback(caminho)


# ── Bolhas de mensagem ────────────────────────────────────────────────────────

class Bolha(MDBoxLayout):
    def __init__(self, texto, autor, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "horizontal"
        self.size_hint_y = None
        self.padding = [dp(4), dp(2)]
        e_usuario = (autor == "usuario")
        card = MDCard(
            size_hint=(0.82, None), padding=dp(12), elevation=0,
            radius=[dp(16), dp(16), dp(4 if e_usuario else 16), dp(16 if e_usuario else 4)],
            md_bg_color=[0.15, 0.38, 0.72, 1] if e_usuario else [0.18, 0.18, 0.24, 1],
        )
        label = MDLabel(
            text=texto, size_hint_y=None, font_style="Body2",
            theme_text_color="Custom", text_color=[1, 1, 1, 1],
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
        _init_db(_get_db_path())
        self._imagem_pendente = None
        self._aguardando = False
        self._digitando = None
        self._construir_layout()
        Clock.schedule_once(self._boas_vindas, 0.4)

    def _construir_layout(self):
        raiz = MDBoxLayout(orientation="vertical")
        raiz.add_widget(MDTopAppBar(
            title="Spica \u2736",
            right_action_items=[
                ["cog-outline",          lambda x: MDApp.get_running_app().navigate_to("configuracoes")],
                ["delete-sweep-outline", lambda x: self._limpar()],
            ],
        ))
        self._scroll = ScrollView(do_scroll_x=False)
        self._msgs = MDBoxLayout(
            orientation="vertical", size_hint_y=None, padding=dp(10), spacing=dp(8),
        )
        self._msgs.bind(minimum_height=self._msgs.setter("height"))
        self._scroll.add_widget(self._msgs)
        raiz.add_widget(self._scroll)

        self._prev = MDBoxLayout(
            orientation="horizontal", size_hint_y=None, height=0,
            padding=[dp(8), 0, dp(8), 0], spacing=dp(6),
        )
        raiz.add_widget(self._prev)

        barra = MDBoxLayout(
            size_hint_y=None, height=dp(60), padding=[dp(6), dp(6)], spacing=dp(2),
        )
        barra.add_widget(MDIconButton(
            icon="image-outline", icon_size=dp(24),
            on_release=lambda x: self._galeria(),
        ))
        self._campo = MDTextField(
            hint_text="Mensagem...", mode="round", multiline=False, size_hint_x=1,
        )
        self._campo.bind(on_text_validate=lambda x: self._enviar())
        barra.add_widget(self._campo)
        barra.add_widget(MDIconButton(
            icon="send", icon_size=dp(24),
            theme_icon_color="Custom", icon_color=[0.25, 0.55, 1.0, 1],
            on_release=lambda x: self._enviar(),
        ))
        raiz.add_widget(barra)
        self.add_widget(raiz)

    # ── Voz (TTS) ─────────────────────────────────────────────────────────────

    def _falar(self, texto):
        """TTS usando Android TextToSpeech (sem biblioteca externa)."""
        try:
            from kivy.utils import platform
            if platform != "android":
                return
            from jnius import autoclass
            PythonAct = autoclass("org.kivy.android.PythonActivity")
            TTS       = autoclass("android.speech.tts.TextToSpeech")
            Locale    = autoclass("java.util.Locale")
            ctx       = PythonAct.mActivity

            if not hasattr(self, "_tts") or self._tts is None:
                self._tts_ready = [False]

                class TtsListener:
                    def onInit(inner_self, status):
                        if status == 0:  # SUCCESS
                            self._tts.setLanguage(Locale("pt", "BR"))
                            self._tts_ready[0] = True

                self._tts = TTS(ctx, TtsListener())

            if getattr(self, "_tts_ready", [False])[0]:
                self._tts.speak(texto, 0, None, None)  # QUEUE_FLUSH=0
        except Exception as e:
            print(f"[Spica] TTS: {e}")

    # ── Boas-vindas ───────────────────────────────────────────────────────────

    def _boas_vindas(self, dt):
        from src.services.groq_service import GroqService
        if GroqService.get_instance().disponivel:
            self._spica("Ola! Sou a Spica \u2736 \u2014 fale comigo por texto ou envie imagens!")
        else:
            self._spica(
                "Ola! Sou a Spica \u2736\n\n"
                "Va em \u2699 Configuracoes e insira sua chave Groq "
                "(console.groq.com \u2014 gratuito)."
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
            self._spica("\u2699 Sem API Key \u2014 va em Configuracoes.")
            return
        exibir = texto or "\U0001F5BC Imagem"
        if self._imagem_pendente and texto:
            exibir = f"\U0001F5BC {texto}"
        self._usuario(exibir)
        img = self._imagem_pendente
        self._imagem_pendente = None
        self._limpar_prev()
        self._campo.text = ""
        self._aguardando = True
        self._show_typing()
        GroqService.get_instance().perguntar(
            mensagem=texto or "Descreva e analise esta imagem detalhadamente.",
            callback=self._resposta,
            caminho_imagem=img,
        )

    def _resposta(self, texto):
        self._hide_typing()
        self._aguardando = False
        self._spica(texto)
        Clock.schedule_once(lambda dt: self._falar(texto), 0.3)

    # ── Galeria ───────────────────────────────────────────────────────────────

    def _galeria(self):
        if self._aguardando:
            return
        _abrir_seletor(self._receber_img)

    def _receber_img(self, caminho):
        if not caminho or not os.path.exists(caminho):
            self._spica("Nao consegui carregar a imagem. Tente novamente.")
            return
        self._imagem_pendente = caminho
        self._show_prev(caminho)

    def _show_prev(self, caminho):
        from kivy.uix.image import Image as KImg
        self._limpar_prev()
        self._prev.height = dp(82)
        img = KImg(source=caminho, size_hint=(None,None), size=(dp(70),dp(70)),
                   allow_stretch=True, keep_ratio=True)
        btn = MDIconButton(icon="close-circle-outline", icon_size=dp(18),
                           size_hint=(None,None), size=(dp(34),dp(34)),
                           on_release=lambda x: self._del_img())
        lbl = MDLabel(text="Pronta \u2014 escreva ou envie", font_style="Caption",
                      theme_text_color="Secondary")
        self._prev.add_widget(img)
        self._prev.add_widget(btn)
        self._prev.add_widget(lbl)

    def _limpar_prev(self):
        self._prev.clear_widgets()
        self._prev.height = 0

    def _del_img(self):
        self._imagem_pendente = None
        self._limpar_prev()

    # ── Mensagens ─────────────────────────────────────────────────────────────

    def _usuario(self, t): self._msgs.add_widget(Bolha(t, "usuario")); self._rolar()
    def _spica(self, t):   self._msgs.add_widget(Bolha(t, "spica"));   self._rolar()

    def _show_typing(self):
        self._digitando = Bolha("\u2022  \u2022  \u2022", "spica")
        self._msgs.add_widget(self._digitando)
        self._rolar()

    def _hide_typing(self):
        if self._digitando and self._digitando in self._msgs.children:
            self._msgs.remove_widget(self._digitando)
        self._digitando = None

    def _rolar(self):
        Clock.schedule_once(lambda dt: setattr(self._scroll, "scroll_y", 0), 0.1)

    def _limpar(self):
        self._msgs.clear_widgets()
        self._imagem_pendente = None
        self._aguardando = False
        self._digitando = None
        self._limpar_prev()
        from src.services.groq_service import GroqService
        GroqService.get_instance().limpar_historico()
        Clock.schedule_once(lambda dt: self._spica("Chat limpo!"), 0.1)
