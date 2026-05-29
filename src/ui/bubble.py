# bubble.py — Bolha flutuante corrigida
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
    DRAG_THRESHOLD = dp(12)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (None, None)
        self.size = (self.BUBBLE_SIZE, self.BUBBLE_SIZE)
        self.radius = [self.BUBBLE_SIZE / 2]
        self.elevation = 8
        self.md_bg_color = MDApp.get_running_app().theme_cls.primary_color

        self._touch_down_pos = (0, 0)
        self._last_pos = (0, 0)
        self._dragging = False
        self._touch_active = False
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
        Clock.schedule_once(lambda dt: Animation(opacity=1, duration=0.4).start(self), 0.2)

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            touch.grab(self)
            self._touch_down_pos = (touch.x, touch.y)
            self._last_pos = (touch.x, touch.y)
            self._dragging = False
            self._touch_active = True
            return True
        # Clique fora fecha o painel
        if self.panel_aberto:
            if not self._painel.collide_point(*touch.pos):
                self._fechar_painel()
        return super().on_touch_down(touch)

    def on_touch_move(self, touch):
        if touch.grab_current is self and self._touch_active:
            dx = touch.x - self._touch_down_pos[0]
            dy = touch.y - self._touch_down_pos[1]
            if abs(dx) > self.DRAG_THRESHOLD or abs(dy) > self.DRAG_THRESHOLD:
                self._dragging = True
            if self._dragging:
                move_x = touch.x - self._last_pos[0]
                move_y = touch.y - self._last_pos[1]
                nx = max(self.MARGEM, min(self.x + move_x, Window.width - self.BUBBLE_SIZE - self.MARGEM))
                ny = max(self.MARGEM, min(self.y + move_y, Window.height - self.BUBBLE_SIZE - self.MARGEM))
                self.pos = (nx, ny)
            self._last_pos = (touch.x, touch.y)
            return True
        return super().on_touch_move(touch)

    def on_touch_up(self, touch):
        if touch.grab_current is self and self._touch_active:
            touch.ungrab(self)
            self._touch_active = False
            if self._dragging:
                self._grudar_na_borda()
            else:
                Clock.schedule_once(lambda dt: self._toggle_painel(), 0.05)
            return True
        return super().on_touch_up(touch)

    def _grudar_na_borda(self):
        cx = self.x + self.BUBBLE_SIZE / 2
        dx = self.MARGEM if cx < Window.width / 2 else Window.width - self.BUBBLE_SIZE - self.MARGEM
        Animation(x=dx, duration=0.3, t="out_cubic").start(self)

    def _toggle_painel(self):
        if self.panel_aberto:
            self._fechar_painel()
        else:
            self._abrir_painel()

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
    LARGURA = dp(260)
    ALTURA = dp(320)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (None, None)
        self.size = (self.LARGURA, self.ALTURA)
        self.radius = [dp(16)]
        self.elevation = 12
        self.opacity = 0
        self.padding = dp(12)
        self.spacing = dp(8)
        self.orientation = "vertical"
        self._na_window = False
        self._construir_ui()

    def _construir_ui(self):
        from kivymd.uix.boxlayout import MDBoxLayout
        from kivymd.uix.button import MDRaisedButton

        self.add_widget(MDLabel(
            text="Spica", font_style="H6", halign="center",
            size_hint_y=None, height=dp(36),
        ))

        # Nav com 5 botões
        nav = MDBoxLayout(orientation="horizontal", size_hint_y=None, height=dp(56), spacing=dp(4))
        botoes = [
            ("home",         "home"),
            ("chat-outline", "chat"),
            ("history",      "historico"),
            ("notebook",     "notas"),
            ("cog",          "configuracoes"),
        ]
        for icon, tela in botoes:
            nav.add_widget(MDIconButton(
                icon=icon,
                icon_size=dp(22),
                on_release=lambda x, t=tela: self._navegar(t)
            ))
        self.add_widget(nav)

        # Botão novo chat
        from kivymd.uix.button import MDRaisedButton
        self.add_widget(MDRaisedButton(
            text="+ Novo Chat",
            size_hint_y=None, height=dp(40),
            on_release=lambda x: self._novo_chat()
        ))

        # Atalhos rápidos
        atalhos = MDBoxLayout(orientation="vertical", size_hint_y=None, height=dp(140), spacing=dp(6))
        for icon, label, tela in [
            ("microphone", "Assistente de Voz", "voz"),
            ("translate",  "Tradutor",          "tradutor"),
            ("calculator", "Calculadora",       "calculadora"),
        ]:
            btn = MDRaisedButton(
                text=f"  {label}",
                icon=icon,
                size_hint_y=None, height=dp(38),
                on_release=lambda x, t=tela: self._navegar(t)
            )
            atalhos.add_widget(btn)
        self.add_widget(atalhos)

    def _navegar(self, tela):
        app = MDApp.get_running_app()
        app.navigate_to(tela)
        app.bubble._fechar_painel()

    def _novo_chat(self):
        app = MDApp.get_running_app()
        chat = app.screen_manager.get_screen("chat")
        chat._limpar_chat()
        app.navigate_to("chat")
        app.bubble._fechar_painel()

    def abrir(self, pos_bolha):
        if not self._na_window:
            Window.add_widget(self)
            self._na_window = True
        px, py = pos_bolha
        self.pos = (
            max(dp(8), min(px - self.LARGURA / 2, Window.width - self.LARGURA - dp(8))),
            min(py + dp(66), Window.height - self.ALTURA - dp(8)),
        )
        Animation(opacity=1, duration=0.2).start(self)

    def fechar(self):
        def _rm(*a):
            if self._na_window:
                try:
                    Window.remove_widget(self)
                except Exception:
                    pass
                self._na_window = False
        anim = Animation(opacity=0, duration=0.15)
        anim.bind(on_complete=_rm)
        anim.start(self)
