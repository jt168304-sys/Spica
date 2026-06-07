# bubble.py — Bolha flutuante Spica (Widget puro Kivy — sem MDCard no Window)
from kivy.core.window import Window
from kivy.animation import Animation
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.uix.widget import Widget
from kivy.graphics import Color, Ellipse, RoundedRectangle
from kivy.uix.label import Label
from kivymd.app import MDApp


# ── Botao do speed-dial ───────────────────────────────────────────────────────

class _BotaoPainel(Widget):
    ALTURA = dp(46)
    LARGURA = dp(190)

    def __init__(self, texto, callback_fn, **kwargs):
        super().__init__(
            size_hint=(None, None),
            size=(self.LARGURA, self.ALTURA),
            opacity=0,
            **kwargs,
        )
        with self.canvas:
            Color(0.13, 0.38, 0.80, 0.96)
            self._bg = RoundedRectangle(
                size=self.size, pos=self.pos, radius=[dp(10)]
            )
        self.bind(
            pos=lambda *a: setattr(self._bg, "pos", self.pos),
            size=lambda *a: setattr(self._bg, "size", self.size),
        )
        self._lbl = Label(
            text=texto,
            font_size=dp(14),
            bold=True,
            color=[1, 1, 1, 1],
            size=self.size,
            pos=self.pos,
        )
        self.bind(pos=lambda *a: setattr(self._lbl, "pos", self.pos))
        self.add_widget(self._lbl)
        self._fn = callback_fn
        Window.add_widget(self)

    def on_touch_down(self, touch):
        if self.opacity > 0.5 and self.collide_point(*touch.pos):
            touch.grab(self)
            return True
        return False

    def on_touch_up(self, touch):
        if touch.grab_current is self:
            touch.ungrab(self)
            if self.collide_point(*touch.pos) and self.opacity > 0.5:
                Clock.schedule_once(lambda dt: self._fn(), 0.05)
            return True
        return False


# ── Bolha flutuante ───────────────────────────────────────────────────────────

class FloatingBubble(Widget):
    SIZE = dp(60)
    MARGEM = dp(10)
    DRAG_THRESHOLD = dp(10)

    def __init__(self, **kwargs):
        super().__init__(
            size_hint=(None, None),
            size=(self.SIZE, self.SIZE),
            **kwargs,
        )

        # Circulo colorido no canvas
        app = MDApp.get_running_app()
        r, g, b, _ = app.theme_cls.primary_color
        with self.canvas:
            self._cor = Color(r, g, b, 1)
            self._circulo = Ellipse(pos=self.pos, size=self.size)
        self.bind(
            pos=lambda *a: setattr(self._circulo, "pos", self.pos),
            size=lambda *a: setattr(self._circulo, "size", self.size),
        )

        # Icone (Label de texto)
        self._icone = Label(
            text="\u2736",
            font_size=dp(24),
            bold=True,
            color=[1, 1, 1, 1],
            size=self.size,
            pos=self.pos,
        )
        self.bind(pos=lambda *a: setattr(self._icone, "pos", self.pos))
        self.add_widget(self._icone)

        # Botoes speed-dial (criados e adicionados ao Window)
        self._btns = [
            _BotaoPainel("  Chat",          lambda: self._ir("chat")),
            _BotaoPainel("  Configuracoes", lambda: self._ir("configuracoes")),
        ]
        self._painel_aberto = False

        # Estado de arraste
        self._drag_start_touch = (0.0, 0.0)
        self._drag_start_pos = (0.0, 0.0)
        self._dragging = False

        # Posiciona e adiciona ao Window
        self.pos = (
            Window.width - self.SIZE - self.MARGEM,
            Window.height * 0.70,
        )
        Window.add_widget(self)

        # Fade-in
        self.opacity = 0
        Clock.schedule_once(
            lambda dt: Animation(opacity=1, duration=0.4).start(self), 0.4
        )
        Clock.schedule_once(self._solicitar_overlay, 3.0)

    # ── Touch ─────────────────────────────────────────────────────────────────

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            touch.grab(self)
            self._drag_start_touch = (touch.x, touch.y)
            self._drag_start_pos = (self.x, self.y)
            self._dragging = False
            return True
        # Toque fora enquanto painel aberto → fecha
        if self._painel_aberto:
            em_botao = any(
                b.opacity > 0.5 and b.collide_point(*touch.pos)
                for b in self._btns
            )
            if not em_botao:
                Clock.schedule_once(lambda dt: self._fechar_painel(), 0.05)
        return False

    def on_touch_move(self, touch):
        if touch.grab_current is self:
            dx = touch.x - self._drag_start_touch[0]
            dy = touch.y - self._drag_start_touch[1]
            if abs(dx) > self.DRAG_THRESHOLD or abs(dy) > self.DRAG_THRESHOLD:
                self._dragging = True
            if self._dragging:
                nx = max(self.MARGEM, min(
                    self._drag_start_pos[0] + dx,
                    Window.width - self.SIZE - self.MARGEM,
                ))
                ny = max(self.MARGEM, min(
                    self._drag_start_pos[1] + dy,
                    Window.height - self.SIZE - self.MARGEM,
                ))
                self.pos = (nx, ny)
            return True
        return False

    def on_touch_up(self, touch):
        if touch.grab_current is self:
            touch.ungrab(self)
            if self._dragging:
                self._grudar_na_borda()
            else:
                Clock.schedule_once(lambda dt: self._toggle_painel(), 0.05)
            return True
        return False

    def _grudar_na_borda(self):
        cx = self.x + self.SIZE / 2
        alvo = (
            self.MARGEM if cx < Window.width / 2
            else Window.width - self.SIZE - self.MARGEM
        )
        Animation(x=alvo, duration=0.28, t="out_cubic").start(self)

    # ── Painel speed-dial ─────────────────────────────────────────────────────

    def _toggle_painel(self):
        if self._painel_aberto:
            self._fechar_painel()
        else:
            self._abrir_painel()

    def _abrir_painel(self):
        self._painel_aberto = True
        self._icone.text = "\u2715"
        bx = self.x + self.SIZE / 2
        for i, btn in enumerate(self._btns):
            alvo_y = self.y + self.SIZE + dp(10) + i * (btn.ALTURA + dp(8))
            btn.x = max(dp(4), min(
                bx - btn.LARGURA / 2,
                Window.width - btn.LARGURA - dp(4),
            ))
            btn.y = self.y
            Animation(opacity=1, y=alvo_y, duration=0.22, t="out_back").start(btn)

    def _fechar_painel(self):
        self._painel_aberto = False
        self._icone.text = "\u2736"
        for btn in self._btns:
            Animation(opacity=0, y=self.y, duration=0.15).start(btn)

    def _ir(self, tela):
        self._fechar_painel()
        Clock.schedule_once(
            lambda dt: MDApp.get_running_app().navigate_to(tela), 0.2
        )

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
                ctx.startActivity(Intent(
                    Settings.ACTION_MANAGE_OVERLAY_PERMISSION,
                    Uri.parse(f"package:{ctx.getPackageName()}"),
                ))
        except Exception as e:
            print(f"[Spica] overlay: {e}")
