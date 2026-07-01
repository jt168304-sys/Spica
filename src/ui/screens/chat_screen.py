# chat_screen.py — Spica v16 (Sincronizado com o Motor de Voz Global)
import os
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.utils import platform
from kivymd.uix.screen import MDScreen
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel
from kivymd.uix.textfield import MDTextField
from kivymd.uix.button import MDIconButton
from kivymd.uix.appbar import MDTopAppBar, MDTopAppBarTrailingButtonContainer, MDTopAppBarTitle
from kivymd.app import MDApp

# Import do seletor de imagens seguro e do novo serviço de voz global centralizado
from src.ui.image_handler import abrir_seletor_seguro
from src.services.tts_service import TtsService


# ── Bolha de mensagem — MDCard atualizado para MD3 ───────────────────────────
class Bolha(MDBoxLayout):
    def __init__(self, texto, autor, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "horizontal"
        self.size_hint_y = None
        self.padding = [dp(4), dp(2)]
        self._texto = texto
        e_usuario = (autor == "usuario")

        card = MDCard(
            style="filled",
            size_hint=(0.82, None), padding=dp(12),
            radius=[dp(16), dp(16),
                    dp(4 if e_usuario else 16),
                    dp(16 if e_usuario else 4)],
            md_bg_color=[0.15, 0.38, 0.72, 1] if e_usuario else [0.18, 0.18, 0.24, 1],
        )
        label = MDLabel(
            text=texto, size_hint_y=None, font_style="Body", role="medium",
            theme_text_color="Custom", text_color=[1, 1, 1, 1],
        )
        label.bind(texture_size=lambda i, v: setattr(i, "height", v[1] + dp(8)))
        label.bind(width=lambda i, w: setattr(i, "text_size", (w, None)))
        card.bind(minimum_height=card.setter("height"))
        card.add_widget(label)

        if not e_usuario:
            btn = MDIconButton(
                icon="content-copy", 
                size_hint=(None, None), size=(dp(32), dp(32)),
                on_release=lambda x: self._copiar(),
            )
            col = MDBoxLayout(
                orientation="vertical", size_hint_x=0.18,
                padding=[0, dp(4), 0, 0]
            )
            col.add_widget(btn)
            col.add_widget(MDBoxLayout(size_hint_y=1))
            self.add_widget(card)
            self.add_widget(col)
        else:
            self.add_widget(MDBoxLayout(size_hint_x=0.18))
            self.add_widget(card)

        self.bind(minimum_height=self.setter("height"))

    def _copiar(self):
        try:
            from kivy.core.clipboard import Clipboard
            Clipboard.copy(self._texto)
        except Exception as e:
            print(f"[Spica] copiar: {e}")


# ── Tela de chat — MD3 Compliant ──────────────────────────────────────────────
class ChatScreen(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._imagem_pendente = None
        self._aguardando      = False
        self._digitando       = None
        self._ouvindo         = False
        self._som_ativo       = True # Gerencia se o chat deve reproduzir áudio localmente
        
        # Conecta ao motor de fala único e persistente da Spica
        self._tts = TtsService.get_instance()
        
        self._construir_layout()
        Clock.schedule_once(self._boas_vindas, 0.5)

    def on_leave(self):
        """Apenas interrompe a fala atual ao sair da tela, preservando o motor para a bolha."""
        if hasattr(self, '_tts') and self._tts:
            self._tts.parar()

    def _construir_layout(self):
        raiz = MDBoxLayout(orientation="vertical")

        barra_superior = MDTopAppBar(type="small")
        titulo_app = MDTopAppBarTitle(text="Spica ✶")
        barra_superior.add_widget(titulo_app)
        
        container_acoes = MDTopAppBarTrailingButtonContainer()
        btn_cog = MDIconButton(icon="cog-outline", on_release=lambda x: MDApp.get_running_app().navigate_to("configuracoes"))
        btn_del = MDIconButton(icon="delete-sweep-outline", on_release=lambda x: self._limpar())
        
        container_acoes.add_widget(btn_cog)
        container_acoes.add_widget(btn_del)
        barra_superior.add_widget(container_acoes)
        raiz.add_widget(barra_superior)

        self._scroll = ScrollView(
            do_scroll_x=False, do_scroll_y=True, size_hint=(1, 1),
            bar_width=dp(3), scroll_type=["bars", "content"],
            bar_color=[0.4, 0.6, 1, 0.7],
        )
        self._msgs = GridLayout(
            cols=1, size_hint_y=None,
            padding=[dp(8), dp(8)], spacing=dp(6),
        )
        self._msgs.bind(minimum_height=self._msgs.setter("height"))
        self._scroll.add_widget(self._msgs)
        raiz.add_widget(self._scroll)

        self._prev = MDBoxLayout(
            orientation="horizontal", size_hint_y=None, height=0,
            padding=[dp(8), 0], spacing=dp(6),
        )
        raiz.add_widget(self._prev)

        self._indicador = MDLabel(
            text="", size_hint_y=None, height=0,
            halign="center", font_style="Label", role="small",
            theme_text_color="Custom", text_color=[0.4, 0.8, 1, 1],
        )
        raiz.add_widget(self._indicador)

        barra = MDBoxLayout(
            size_hint_y=None, height=dp(60),
            padding=[dp(4), dp(6)], spacing=dp(2),
        )

        barra.add_widget(MDIconButton(
            icon="image-outline", 
            on_release=lambda x: self._galeria(),
        ))

        self._campo = MDTextField(
            hint_text="Mensagem...", mode="outlined",
            multiline=False, size_hint_x=1,
        )
        self._campo.bind(on_text_validate=lambda x: self._enviar())
        barra.add_widget(self._campo)

        self._btn_mic = MDIconButton(
            icon="microphone-outline", 
            theme_icon_color="Custom",
            icon_color=[0.4, 0.8, 1, 1],
            on_release=lambda x: self._toggle_mic(),
        )
        barra.add_widget(self._btn_mic)

        self._btn_som = MDIconButton(
            icon="volume-high", 
            theme_icon_color="Custom",
            icon_color=[0.4, 0.8, 1, 1],
            on_release=lambda x: self._toggle_som(),
        )
        barra.add_widget(self._btn_som)

        barra.add_widget(MDIconButton(
            icon="send", 
            theme_icon_color="Custom", icon_color=[0.25, 0.55, 1.0, 1],
            on_release=lambda x: self._enviar(),
        ))

        raiz.add_widget(barra)
        self.add_widget(raiz)

    # ── Microfone ─────────────────────────────────────────────────────────────
    def _toggle_mic(self):
        if self._ouvindo:
            self._parar_mic()
        else:
            self._iniciar_mic()

    def _iniciar_mic(self):
        if self._aguardando:
            return
        try:
            if platform == "android":
                from android.permissions import check_permission, request_permissions, Permission
                if not check_permission(Permission.RECORD_AUDIO):
                    def on_perm(perms, grants):
                        if grants and grants[0]:
                            Clock.schedule_once(lambda dt: self._iniciar_mic(), 0.3)
                        else:
                            self._spica("Permissao de microfone negada.")
                    request_permissions([Permission.RECORD_AUDIO], on_perm)
                    return
        except Exception as e:
            print(f"[Spica] check_permission: {e}")

        self._ouvindo = True
        self._tts.parar()
        self._btn_mic.icon = "microphone"
        self._btn_mic.icon_color = [1, 0.3, 0.3, 1]
        self._indicador.text = "● Ouvindo..."
        self._indicador.height = dp(24)
        
        from src.services.voice_service import VoiceService
        from src.services.overlay import SpicaOverlay
        
        # Opcional: Avisa a bolha para fechar a boca enquanto o app ouve o microfone
        # SpicaOverlay().definir_avatar_png(falar=False)

        VoiceService.get_instance().ouvir(
            callback=lambda texto: Clock.schedule_once(
                lambda dt: self._voz_recebida(texto), 0)
        )

    def _parar_mic(self):
        self._ouvindo = False
        self._btn_mic.icon = "microphone-outline"
        self._btn_mic.icon_color = [0.4, 0.8, 1, 1]
        self._indicador.text = ""
        self._indicador.height = 0

    def _toggle_som(self):
        self._som_ativo = not self._som_ativo
        if not self._som_ativo:
            self._btn_som.icon = "volume-off"
            self._btn_som.icon_color = [0.5, 0.5, 0.5, 1]
            self._tts.parar()
        else:
            self._btn_som.icon = "volume-high"
            self._btn_som.icon_color = [0.4, 0.8, 1, 1]

    def _voz_recebida(self, texto):
        self._parar_mic()
        if not texto or "Erro" in texto or "Nao ouvi" in texto:
            self._spica(texto or "Nao ouvi. Tente novamente.")
            return
        from src.services.groq_service import GroqService
        if not GroqService.get_instance().disponivel:
            self._spica("Configure sua chave Groq.")
            return
        self._usuario(f"🎙 {texto}")
        self._aguardando = True
        self._show_typing()
        GroqService.get_instance().perguntar(
            mensagem=texto,
            callback=lambda r: Clock.schedule_once(
                lambda dt: self._resposta_voz(r), 0),
        )

    def _resposta_voz(self, texto):
        self._hide_typing()
        self._aguardando = False
        self._spica(texto)
        if self._som_ativo:
            self._tts.falar(texto)

    def iniciar_escuta_voz(self):
        self._iniciar_mic()

    # ── Chat ──────────────────────────────────────────────────────────────────
    def _boas_vindas(self, dt):
        from src.services.groq_service import GroqService
        if GroqService.get_instance().disponivel:
            self._spica("Ola! Sou a Spica ✶ — fale, escreva ou envie imagens!")
        else:
            self._spica("Ola! Sou a Spica ✶\n\nVa em ⚙ Configuracoes e insira sua chave Groq.")

    def _enviar(self):
        if self._aguardando:
            return
        texto = self._campo.text.strip()
        if not texto and not self._imagem_pendente:
            return
        from src.services.groq_service import GroqService
        if not GroqService.get_instance().disponivel:
            self._spica("⚙ Sem API Key.")
            return
        exibir = texto or "🖼 Imagem"
        if self._imagem_pendente and texto:
            exibir = f"🖼 {texto}"
        self._usuario(exibir)
        img = self._imagem_pendente
        self._imagem_pendente = None
        self._limpar_prev()
        self._campo.text = ""
        self._aguardando = True
        self._show_typing()
        GroqService.get_instance().perguntar(
            mensagem=texto or "Descreva esta imagem.",
            callback=self._resposta,
            caminho_imagem=img,
        )

    def _resposta(self, texto):
        self._hide_typing()
        self._aguardando = False
        self._spica(texto)
        if self._som_ativo:
            Clock.schedule_once(lambda dt: self._tts.falar(texto), 0.3)

    def _galeria(self):
        if self._aguardando:
            return
        abrir_seletor_seguro(self._receber_img)

    def _receber_img(self, caminho):
        if not caminho or not os.path.exists(caminho):
            self._spica("Nao consegui carregar a imagem.")
            return
        self._imagem_pendente = caminho
        self._show_prev(caminho)

    def _show_prev(self, caminho):
        from kivy.uix.image import Image as KImg
        self._limpar_prev()
        self._prev.height = dp(82)
        img = KImg(source=caminho, size_hint=(None, None),
                   size=(dp(70), dp(70)), allow_stretch=True, keep_ratio=True)
        btn = MDIconButton(icon="close-circle-outline", 
                           size_hint=(None, None), size=(dp(34), dp(34)),
                           on_release=lambda x: self._del_img())
        lbl = MDLabel(text="Pronta — escreva ou envie",
                      font_style="Label", role="small", theme_text_color="Secondary")
        self._prev.add_widget(img)
        self._prev.add_widget(btn)
        self._prev.add_widget(lbl)

    def _limpar_prev(self):
        self._prev.clear_widgets()
        self._prev.height = 0

    def _del_img(self):
        self._imagem_pendente = None
        self._limpar_prev()

    def _usuario(self, t):
        self._msgs.add_widget(Bolha(t, "usuario"))
        self._rolar()

    def _spica(self, t):
        self._msgs.add_widget(Bolha(t, "spica"))
        self._rolar()

    def _show_typing(self):
        self._digitando = Bolha("• • •", "spica")
        self._msgs.add_widget(self._digitando)
        self._rolar()

    def _hide_typing(self):
        if self._digitando and self._digitando in self._msgs.children:
            self._msgs.remove_widget(self._digitando)
        self._digitando = None

    def _rolar(self):
        Clock.schedule_once(lambda dt: setattr(self._scroll, "scroll_y", 0), 0.15)

    def _limpar(self):
        self._msgs.clear_widgets()
        self._imagem_pendente = None
        self._aguardando = False
        self._digitando = None
        self._parar_mic()
        self._limpar_prev()
        from src.services.groq_service import GroqService
        GroqService.get_instance().limpar_historico()
        Clock.schedule_once(lambda dt: self._spica("Chat limpo!"), 0.1)
