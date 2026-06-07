# bubble.py — Bolha flutuante Spica
from kivy.core.window import Window
from kivy.animation import Animation
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.uix.modalview import ModalView
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.graphics import Color, RoundedRectangle
from kivymd.uix.card import MDCard
from kivymd.uix.button import MDIconButton
from kivymd.app import MDApp


# ── Painel (ModalView puro Kivy — sem MDCard no Window) ───────────────────────

class _PainelModal(ModalView):
    """
    Usa ModalView do Kivy base (sem KivyMD) para evitar crash do shader
    de sombra do MDCard quando adicionado diretamente ao Window.
    """

    def __init__(self, **kwargs):
        super().__init__(
            size_hint=(0.75, None),
            height=dp(230),
            background="",
            background_color=[0, 0, 0, 0],
            overlay_color=[0, 0, 0, 0.5],
            auto_dismiss=True,
            **kwargs,
        )
        caixa = BoxLayout(
            orientation="vertical",
            padding=dp(18),
            spacing=dp(12),
        )

        # Fundo arredondado desenhado em canvas
        with caixa.canvas.before:
            Color(0.09, 0.09, 0.15, 0.97)
            self._bg = RoundedRectangle(
                size=caixa.size,
                pos=caixa.pos,
                radius=[dp(20)],
            )
        caixa.bind(
            pos=lambda i, v: setattr(self._bg, "pos", v),
            size=lambda i, v: setattr(self._bg, "size", v),
        )

        titulo = Label(
            text="Spica \u2736",
            font_size=dp(20),
            bold=True,
            color=[1, 1, 1, 1],
            size_hint_y=None,
            height=dp(38),
        )
        caixa.add_widget(titulo)

        for txt, tela in [("  Chat", "chat"), ("  Configuracoes", "configuracoes")]:
            btn = Button(
                text=txt,
                size_hint_y=None,
                height=dp(52),
                background_normal="",
                background_color=[0.16, 0.40, 0.80, 1],
                color=[1, 1, 1, 1],
                bold=True,
                font_size=dp(15),
                halign="center",
            )
            btn.bind(on_release=lambda x, t=tela: self._ir(t))
            caixa.add_widget(btn)

        self.add_widget(caixa)

    def _ir(self, tela):
        self.dismiss()
        Clock.schedule_once(
            lambda dt: MDApp.get_running_app().navigate_to(tela), 0.1
        )


# ── Bolha flutuante ───────────────────────────────────────────────────────────

class FloatingBubble(MDCard):
    BUBBLE_SIZE = dp(60)
    MARGEM = dp(10)
    DRAG_THRESHOLD = dp(12)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (None, None)
        self.size = (self.BUBBLE_SIZE, self.BUBBLE_SIZE)
        self.radius = [self.BUBBLE_SIZE / 2]
        self.elevation = 0          # 0 evita shader de sombra problemático
        self.md_bg_color = MDApp.get_running_app().theme_cls.primary_color

        self._touch_down_pos = (0, 0)
        self._last_pos = (0, 0)
        self._dragging = False
        self._touch_active = False
        self.panel_aberto = False

        self._icon = MDIconButton(
            icon="auto-fix",
            icon_size=dp(28),
            pos_hint={"center_x": 0.5, "center_y": 0.5},
            theme_icon_color="Custom",
            icon_color=[1, 1, 1, 1],
        )
        self.add_widget(self._icon)

        self.pos = (
            Window.width - self.BUBBLE_SIZE - self.MARGEM,
            Window.height * 0.7,
        )
        Window.add_widget(self)

        # Cria o painel DEPOIS de tudo estar pronto
        self._painel = _PainelModal()
        self._painel.bind(on_dismiss=self._ao_fechar_painel)

        self.opacity = 0
        Clock.schedule_once(
            lambda dt: Animation(opacity=1, duration=0.4).start(self), 0.3
        )
        Clock.schedule_once(self._solicitar_overlay, 3.0)

    # ── Overlay ───────────────────────────────────────────────────────────────

    def _solicitar_overlay(self, dt):
        try:
            from kivy.utils import platform
            if platform != "android":
                return
            from jnius import autoclass
            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            Settings = autoclass("android.provider.Settings")
            ctx = PythonActivity.mActivity
            if not Settings.canDrawOverlays(ctx):
                Intent = autoclass("android.content.Intent")
                Uri = autoclass("android.net.Uri")
                intent = Intent(
                    Settings.ACTION_MANAGE_OVERLAY_PERMISSION,
                    Uri.parse(f"package:{ctx.getPackageName()}"),
                )
                ctx.startActivity(intent)
        except Exception as e:
            print(f"[Spica] overlay: {e}")

    # ── Touch ─────────────────────────────────────────────────────────────────

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            touch.grab(self)
            self._touch_down_pos = (touch.x, touch.y)
            self._last_pos = (touch.x, touch.y)
            self._dragging = False
            self._touch_active = True
            return True
        if self.panel_aberto:
            # toque fora do painel é gerenciado pelo auto_dismiss do ModalView
            pass
        return super().on_touch_down(touch)

    def on_touch_move(self, touch):
        if touch.grab_current is self and self._touch_active:
            dx = touch.x - self._touch_down_pos[0]
            dy = touch.y - self._touch_down_pos[1]
            if abs(dx) > self.DRAG_THRESHOLD or abs(dy) > self.DRAG_THRESHOLD:
                self._dragging = True
            if self._dragging:
                nx = max(self.MARGEM, min(
                    self.x + (touch.x - self._last_pos[0]),
                    Window.width - self.BUBBLE_SIZE - self.MARGEM,
                ))
                ny = max(self.MARGEM, min(
                    self.y + (touch.y - self._last_pos[1]),
                    Window.height - self.BUBBLE_SIZE - self.MARGEM,
                ))
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
        alvo_x = (
            self.MARGEM if cx < Window.width / 2
            else Window.width - self.BUBBLE_SIZE - self.MARGEM
        )
        Animation(x=alvo_x, duration=0.28, t="out_cubic").start(self)

    # ── Painel ────────────────────────────────────────────────────────────────

    def _toggle_painel(self):
        if self.panel_aberto:
            self._painel.dismiss()
        else:
            self._abrir_painel()

    def _abrir_painel(self):
        try:
            self._painel.open()
            self.panel_aberto = True
            self._icon.icon = "close"
        except Exception as e:
            print(f"[Spica] abrir painel: {e}")

    def _ao_fechar_painel(self, *args):
        self.panel_aberto = False
        self._icon.icon = "auto-fix"
