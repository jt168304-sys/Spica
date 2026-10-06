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


class _CardMensagem(MDCard):
    """MDCard sem o comportamento de botão/ripple (que consumia o toque e atrapalhava
    o scroll). Toque longo (0,6 s sem mover o dedo) chama `ao_toque_longo`."""
    ao_toque_longo = None

    def on_touch_down(self, touch):
        if self.ao_toque_longo and self.collide_point(*touch.pos):
            inicio = tuple(touch.pos)

            def _disparar(dt, touch=touch, inicio=inicio):
                parado = (abs(touch.pos[0] - inicio[0]) < dp(12)
                          and abs(touch.pos[1] - inicio[1]) < dp(12))
                if touch.time_end == -1 and parado:   # dedo ainda na tela e parado
                    self.ao_toque_longo()
            Clock.schedule_once(_disparar, 0.6)
        return False

    def on_touch_move(self, touch):
        return False

    def on_touch_up(self, touch):
        return False


from kivymd.uix.label import MDLabel
from kivymd.uix.textfield import MDTextField
from kivymd.uix.button import MDIconButton
from kivymd.uix.toolbar import MDTopAppBar
from kivymd.app import MDApp

# Import do seletor de imagens seguro e do novo serviço de voz global centralizado
from src.ui.image_handler import abrir_seletor_seguro
from src.ui import tema as T
from src.ui.barra import criar_barra
from src.services.tts_service import TtsService


# ── Bolha de mensagem — MDCard atualizado para MD3 ───────────────────────────
class Bolha(MDBoxLayout):
    def __init__(self, texto, autor, animar=False, ao_terminar_anim=None, imagem=None,
                 ao_passo_anim=None, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "horizontal"
        self.size_hint_y = None
        self.padding = [dp(4), dp(2)]
        self._texto = texto
        self._finalizar_anim = None
        e_usuario = (autor == "usuario")

        card = _CardMensagem(
            style="filled", orientation="vertical", spacing=dp(8),
            size_hint=(0.82, None), padding=dp(12),
            radius=[dp(16), dp(16),
                    dp(4 if e_usuario else 16),
                    dp(16 if e_usuario else 4)],
            md_bg_color=T.MENTA if e_usuario else T.BALAO_IA,
        )
        label = MDLabel(
            text=("" if animar else texto), size_hint_y=None, font_style="Body1",
            theme_text_color="Custom", text_color=T.FUNDO if e_usuario else T.CREME,
        )
        label.bind(texture_size=lambda i, v: setattr(i, "height", v[1] + dp(8)))
        label.bind(width=lambda i, w: setattr(i, "text_size", (w, None)))
        card.bind(minimum_height=card.setter("height"))
        card.ao_toque_longo = lambda: self._copiar_com_aviso(card)
        if imagem and e_usuario:
            try:
                from kivy.uix.image import Image as KImg
                altura = dp(170)
                img = KImg(source=imagem, size_hint=(None, None), height=altura,
                           allow_stretch=True, keep_ratio=True)

                def _ajustar(*a):
                    tw, th = img.texture_size
                    if th:
                        img.width = min(altura * tw / th, max(card.width - dp(24), dp(80)))
                img.bind(texture_size=_ajustar)
                card.bind(width=_ajustar)
                _ajustar()
                card.add_widget(img)
            except Exception as e:
                print(f"[Spica] miniatura: {e}")
        if texto:                       # imagem sem texto: só a foto, sem legenda
            card.add_widget(label)

        if not e_usuario:
            btn = MDIconButton(
                icon="content-copy", 
                size_hint=(None, None), size=(dp(32), dp(32)),
                on_release=lambda x: self._copiar(),
            )
            T.icone(btn)
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

        if animar:
            self._animar_texto(label, texto, ao_terminar_anim, ao_passo_anim)

    def _animar_texto(self, label, texto_completo, ao_terminar=None, ao_passo=None):
        """Revela o texto aos poucos, mas SEM travar: ~14 atualizações por segundo,
        em palavras inteiras, e no máximo ~2 s mesmo para respostas longas."""
        n = len(texto_completo)
        tps = 14
        passo = max(3, -(-n // int(2.2 * tps)))
        estado = {"i": 0, "fim": False, "evento": None}

        def _finalizar():
            if estado["fim"]:
                return
            estado["fim"] = True
            if estado["evento"] is not None:
                estado["evento"].cancel()
            label.text = texto_completo
            if ao_terminar:
                ao_terminar()

        def _passo(dt):
            if estado["fim"]:
                return False
            prox = estado["i"] + passo
            if prox >= n:
                _finalizar()
                return False
            corte = texto_completo.find(" ", prox)       # termina a palavra
            i = n if corte == -1 else corte
            estado["i"] = i
            label.text = texto_completo[:i]
            if ao_passo:
                ao_passo()
            if i >= n:
                _finalizar()
                return False

        self._finalizar_anim = _finalizar
        estado["evento"] = Clock.schedule_interval(_passo, 1.0 / tps)

    def finalizar_animacao(self):
        """Mostra o texto inteiro agora e para a animação (usado ao interromper)."""
        if self._finalizar_anim:
            self._finalizar_anim()

    def _copiar_com_aviso(self, card):
        if not self._texto:
            return
        self._copiar()
        try:
            from kivymd.toast import toast
            toast("Mensagem copiada")
        except Exception as e:
            print(f"[Spica] toast: {e}")
        try:                                               # piscadinha de confirmação
            original = list(card.md_bg_color)
            card.md_bg_color = T.PESSEGO[:3] + [0.35]
            Clock.schedule_once(lambda dt: setattr(card, "md_bg_color", original), 0.18)
        except Exception:
            pass

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
        self._anim_atual      = None
        self._geracao         = 0
        self._digitando       = None
        self._ouvindo         = False
        self._som_ativo       = True # Gerencia se o chat deve reproduzir áudio localmente
        
        # Conecta ao motor de fala único e persistente da Spica
        self._tts = TtsService.get_instance()
        
        self._construir_layout()
        Clock.schedule_once(self._boas_vindas, 0.5)

    def on_leave(self):
        """Apenas interrompe a fala atual ao sair da tela, preservando o motor para a bolha."""
        self._interromper_resposta()

    def _interromper_resposta(self):
        """Para a fala e termina na hora o texto que ainda está aparecendo."""
        if self._anim_atual is not None:
            self._anim_atual.finalizar_animacao()
            self._anim_atual = None
        if hasattr(self, "_tts") and self._tts:
            self._tts.parar()

    def _construir_layout(self):
        raiz = MDBoxLayout(orientation="vertical")

        T.estilizar(raiz, md_bg_color=T.FUNDO)
        raiz.add_widget(criar_barra(
            "Spica", logo=True,
            direita=[
                ("cog-outline", lambda: MDApp.get_running_app().navigate_to("configuracoes")),
                ("trash-can-outline", lambda: self._limpar()),
            ],
        ))

        self._scroll = ScrollView(
            do_scroll_x=False, do_scroll_y=True, size_hint=(1, 1),
            bar_width=dp(3), scroll_type=["bars", "content"],
            bar_color=T.PESSEGO[:3] + [0.7],
            always_overscroll=False,
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
            halign="center", font_style="Caption",
            theme_text_color="Primary",
        )
        T.estilizar(self._indicador, theme_text_color="Custom", text_color=T.PESSEGO)
        raiz.add_widget(self._indicador)

        barra = MDBoxLayout(
            size_hint_y=None, height=dp(60),
            padding=[dp(4), dp(6)], spacing=dp(2),
        )
        T.estilizar(barra, md_bg_color=T.SUPERFICIE)

        btn_img = MDIconButton(
            icon="image-outline", 
            on_release=lambda x: self._galeria(),
        )
        T.icone(btn_img)
        barra.add_widget(btn_img)

        self._campo = MDTextField(
            hint_text="Mensagem...", mode="rectangle",
            multiline=False, size_hint_x=1,
            keyboard_suggestions=False,
            radius=[dp(20)],
        )
        T.estilizar(self._campo,
                    line_color_normal=T.BORDA, line_color_focus=T.MENTA,
                    text_color_normal=T.CREME, text_color_focus=T.CREME,
                    hint_text_color_normal=T.TEXTO_2, hint_text_color_focus=T.MENTA)
        self._campo.bind(on_text_validate=lambda x: self._enviar())
        barra.add_widget(self._campo)

        self._btn_mic = MDIconButton(
            icon="microphone-outline", 
            theme_icon_color="Primary",
            on_release=lambda x: self._toggle_mic(),
        )
        T.icone(self._btn_mic)
        barra.add_widget(self._btn_mic)

        self._btn_som = MDIconButton(
            icon="volume-high", 
            theme_icon_color="Primary",
            on_release=lambda x: self._toggle_som(),
        )
        T.icone(self._btn_som)
        barra.add_widget(self._btn_som)

        btn_enviar = MDIconButton(
            icon="send", 
            theme_icon_color="Primary",
            on_release=lambda x: self._enviar(),
        )
        T.icone(btn_enviar, T.PESSEGO)
        barra.add_widget(btn_enviar)

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
        T.icone(self._btn_mic, T.PESSEGO)
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
        T.icone(self._btn_mic)
        self._indicador.text = ""
        self._indicador.height = 0

    def _toggle_som(self):
        self._som_ativo = not self._som_ativo
        if not self._som_ativo:
            self._btn_som.icon = "volume-off"
            T.icone(self._btn_som, T.TEXTO_2[:3] + [0.5])
            self._tts.parar()
        else:
            self._btn_som.icon = "volume-high"
            T.icone(self._btn_som)

    def _voz_recebida(self, texto):
        self._parar_mic()
        if not texto or "Erro" in texto or "Nao ouvi" in texto:
            self._spica(texto or "Nao ouvi. Tente novamente.")
            return
        from src.services.groq_service import GroqService
        if not GroqService.get_instance().disponivel:
            self._spica("Configure sua chave Groq.")
            return
        self._interromper_resposta()
        self._usuario(f"{texto}")
        self._aguardando = True
        self._show_typing()
        g = self._geracao
        GroqService.get_instance().perguntar(
            mensagem=texto,
            callback=lambda r: Clock.schedule_once(
                lambda dt: self._resposta_voz(r, g), 0),
        )

    def _resposta_voz(self, texto, geracao=None):
        if geracao is not None and geracao != self._geracao:
            return                      # chat foi limpo enquanto respondia
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
            self._spica("Ola! Sou a Spica — fale, escreva ou envie imagens!")
        else:
            self._spica("Ola! Sou a Spica\n\nVa em Configuracoes e insira sua chave Groq.")

    def _enviar(self):
        if self._aguardando:
            return
        texto = self._campo.text.strip()
        if not texto and not self._imagem_pendente:
            return
        from src.services.groq_service import GroqService
        if not GroqService.get_instance().disponivel:
            self._spica("Sem API Key.")
            return
        self._interromper_resposta()
        img = self._imagem_pendente
        self._usuario(texto, imagem=img)
        self._imagem_pendente = None
        self._limpar_prev()
        self._campo.text = ""
        self._aguardando = True
        self._show_typing()
        g = self._geracao
        GroqService.get_instance().perguntar(
            mensagem=texto or "Descreva esta imagem.",
            callback=lambda r: self._resposta(r, g),
            caminho_imagem=img,
        )

    def _resposta(self, texto, geracao=None):
        if geracao is not None and geracao != self._geracao:
            return                      # chat foi limpo enquanto respondia
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
                      font_style="Caption", theme_text_color="Secondary")
        self._prev.add_widget(img)
        self._prev.add_widget(btn)
        self._prev.add_widget(lbl)

    def _limpar_prev(self):
        self._prev.clear_widgets()
        self._prev.height = 0

    def _del_img(self):
        self._imagem_pendente = None
        self._limpar_prev()

    def _usuario(self, t, imagem=None):
        self._msgs.add_widget(Bolha(t, "usuario", imagem=imagem))
        self._rolar()

    def _spica(self, t):
        if self._anim_atual is not None:        # termina a anterior antes de começar outra
            self._anim_atual.finalizar_animacao()
        bolha = Bolha(t, "spica", animar=True, ao_terminar_anim=self._rolar,
                      ao_passo_anim=self._rolar_agora)
        self._anim_atual = bolha
        self._msgs.add_widget(bolha)
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

    def _rolar_agora(self):
        Clock.schedule_once(lambda dt: setattr(self._scroll, "scroll_y", 0), 0)

    def _limpar(self):
        self._geracao += 1
        self._interromper_resposta()
        self._msgs.clear_widgets()
        self._imagem_pendente = None
        self._aguardando = False
        self._digitando = None
        self._parar_mic()
        self._limpar_prev()
        from src.services.groq_service import GroqService
        GroqService.get_instance().limpar_historico()
        Clock.schedule_once(lambda dt: self._spica("Chat limpo!"), 0.1)
