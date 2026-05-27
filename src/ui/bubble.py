# bubble.py — Bolha flutuante arrastável + painel de navegação
from kivy.core.window import Window
from kivy.animation import Animation
from kivy.clock import Clock
from kivy.metrics import dp
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel
from kivymd.uix.button import MDIconButton
from kivymd.app import MDApp


class FloatingBubble(MDCard):
    BUBBLE_SIZE = dp(60)
    MARGEM = dp(10)
    ANIM_DURACAO = 0.3

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (None, None)
        self.size = (self.BUBBLE_SIZE, self.BUBBLE_SIZE)
        self.radius = [self.BUBBLE_SIZE / 2]
        self.elevation = 8
        self.md_bg_color = MDApp.get_running_app().theme_cls.primary_color

        self._dragging = False
        self._touch_start = (0, 0)
        self._last_pos = (0, 0)
        self._drag_threshold = dp(8)
        self.panel_aberto = False

        self._icon = MDIconButton(
            icon="weather-windy",
            icon_size=dp(28),
            pos_hint={"center_x": 0.5, "center_y": 0.5},
            theme_icon_color="Custom",
            icon_color=[1, 1, 1, 1],
        )
        self.add_widget(self._icon)

        self.pos = (Window.width - self.BUBBLE_SIZE - self.MARGEM, Window.height * 0.7)
        Window.add_widget(self)
        self._painel = PainelPrincipal()

        self.opacity = 0
        Clock.schedule_once(self._animar_entrada, 0.1)

    def _animar_entrada(self, dt):
        Animation(opacity=1, duration=0.4, t="out_back").start(self)

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self._touch_start = touch.pos
            self._last_pos = touch.pos
            self._dragging = False
            touch.grab(self)
            return True
        return super().on_touch_down(touch)

    def on_touch_move(self, touch):
        if touch.grab_current is self:
            dx = touch.pos[0] - self._touch_start[0]
            dy = touch.pos[1] - self._touch_start[1]
            # Só considera drag se passou do threshold
            if abs(dx) > self._drag_threshold or abs(dy) > self._drag_threshold:
                self._dragging = True
            if self._dragging:
                mdx = touch.pos[0] - self._last_pos[0]
                mdy = touch.pos[1] - self._last_pos[1]
                nova_x = max(self.MARGEM, min(self.x + mdx, Window.width - self.BUBBLE_SIZE - self.MARGEM))
                nova_y = max(self.MARGEM, min(self.y + mdy, Window.height - self.BUBBLE_SIZE - self.MARGEM))
                self.pos = (nova_x, nova_y)
            self._last_pos = touch.pos
            return True
        return super().on_touch_move(touch)

    def on_touch_up(self, touch):
        if touch.grab_current is self:
            touch.ungrab(self)
            if self._dragging:
                self._grudar_na_borda()
            else:
                self._toggle_painel()
            return True
        return super().on_touch_up(touch)

    def _grudar_na_borda(self):
        centro_x = self.x + self.BUBBLE_SIZE / 2
        destino_x = self.MARGEM if centro_x < Window.width / 2 else Window.width - self.BUBBLE_SIZE - self.MARGEM
        Animation(x=destino_x, duration=self.ANIM_DURACAO, t="out_cubic").start(self)

    def _toggle_painel(self):
        self._fechar_painel() if self.panel_aberto else self._abrir_painel()

    def _abrir_painel(self):
        self._painel.abrir(self.pos)
        self.panel_aberto = True
        self._icon.icon = "close"

    def _fechar_painel(self):
        self._painel.fechar()
        self.panel_aberto = False
        self._icon.icon = "weather-windy"

    def pulsar(self):
        anim = (Animation(size=(self.BUBBLE_SIZE * 1.2, self.BUBBLE_SIZE * 1.2), duration=0.3)
                + Animation(size=(self.BUBBLE_SIZE, self.BUBBLE_SIZE), duration=0.3))
        anim.repeat = True
        anim.start(self)

    def parar_pulsar(self):
        Animation.cancel_all(self)
        self.size = (self.BUBBLE_SIZE, self.BUBBLE_SIZE)


class PainelPrincipal(MDCard):
    LARGURA = dp(300)
    ALTURA = dp(400)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (None, None)
        self.size = (self.LARGURA, self.ALTURA)
        self.radius = [dp(20)]
        self.elevation = 12
        self.opacity = 0
        self.padding = dp(16)
        self.spacing = dp(8)
        self.orientation = "vertical"
        self._na_window = False
        self._construir_ui()

    def _construir_ui(self):
        from kivymd.uix.boxlayout import MDBoxLayout
        from kivymd.uix.button import MDIconButton, MDRaisedButton
        from kivymd.uix.textfield import MDTextField

        self.add_widget(MDLabel(
            text="Spica", font_style="H6", halign="center",
            size_hint_y=None, height=dp(40),
        ))

        nav = MDBoxLayout(orientation="horizontal", size_hint_y=None, height=dp(60), spacing=dp(8))
        for icon, tela in [("home", "home"), ("chat-outline", "chat"),
                           ("notebook", "notas"), ("cog", "configuracoes")]:
            nav.add_widget(MDIconButton(icon=icon, on_release=lambda x, t=tela: self._navegar(t)))
        self.add_widget(nav)

        self.campo_texto = MDTextField(
            hint_text="Digite um comando...",
            mode="round",
            size_hint_y=None,
            height=dp(50)
        )
        self.add_widget(self.campo_texto)

        acoes = MDBoxLayout(orientation="horizontal", size_hint_y=None, height=dp(50), spacing=dp(8))
        acoes.add_widget(MDIconButton(icon="microphone", icon_size=dp(28), on_release=self._ativar_voz))
        acoes.add_widget(MDRaisedButton(text="Enviar", on_release=self._enviar_comando))
        self.add_widget(acoes)

    def _navegar(self, tela):
        MDApp.get_running_app().navigate_to(tela)
        self.fechar()

    def _ativar_voz(self, *args):
        from src.services.voice_service import VoiceService
        MDApp.get_running_app().bubble.pulsar()
        VoiceService.get_instance().ouvir()

    def _enviar_comando(self, *args):
        from src.modules.commands import CommandProcessor
        texto = self.campo_texto.text.strip()
        if texto:
            CommandProcessor.get_instance().processar(texto)
            self.campo_texto.text = ""

    def abrir(self, pos_bolha):
        if not self._na_window:
            Window.add_widget(self)
            self._na_window = True
        px, py = pos_bolha
        self.pos = (
            max(dp(10), min(px - self.LARGURA / 2, Window.width - self.LARGURA - dp(10))),
            min(py + dp(70), Window.height - self.ALTURA - dp(10)),
        )
        Animation(opacity=1, duration=0.25, t="out_quad").start(self)

    def fechar(self):
        anim = Animation(opacity=0, duration=0.2, t="in_quad")
        anim.bind(on_complete=lambda *a: Window.remove_widget(self) if self._na_window else None)
        anim.start(self)
        self._na_window = False
