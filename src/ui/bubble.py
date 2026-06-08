# bubble.py — Bolha flutuante Spica
# NOTA: A bolha atual opera DENTRO do app Kivy (Window.add_widget).
# Para sobrepor outros apps (WhatsApp, Chrome etc.) é necessário implementar
# um Android Foreground Service com WindowManager TYPE_APPLICATION_OVERLAY,
# o que requer código Java/Kotlin e alterações no buildozer.spec e AndroidManifest.
# Isso está documentado como próximo passo de desenvolvimento.

from kivy.core.window import Window
from kivy.animation import Animation
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.uix.label import Label
from kivy.graphics import Color, Ellipse
from kivymd.app import MDApp


class FloatingBubble(Label):
    """
    Bolha flutuante dentro do contexto Kivy.
    Aparece sobre as telas do app, mas NÃO sobre outros aplicativos.
    Para overlay real sobre outros apps, implementar Android Service separado.
    """
    SIZE   = dp(60)
    MARGEM = dp(10)
    DRAG   = dp(10)

    def __init__(self, **kwargs):
        super().__init__(
            text="\u2736",
            font_size=dp(26),
            bold=True,
            color=[1, 1, 1, 1],
            size_hint=(None, None),
            size=(self.SIZE, self.SIZE),
            halign="center",
            valign="middle",
            **kwargs,
        )
        # Círculo azul desenhado antes do texto
        with self.canvas.before:
            self._cor = Color(0.18, 0.42, 0.82, 1)
            self._circulo = Ellipse(pos=self.pos, size=self.size)
        self.bind(
            pos=lambda *a: setattr(self._circulo, "pos", self.pos),
            size=lambda *a: (
                setattr(self._circulo, "size", self.size),
                setattr(self, "text_size", self.size),
            ),
        )
        self.text_size = self.size

        # Posição inicial
        self.pos = (Window.width - self.SIZE - self.MARGEM, Window.height * 0.70)
        Window.add_widget(self)

        # Dialog do menu (criado uma vez, reutilizado)
        self._dialog = None
        Clock.schedule_once(self._criar_dialog, 0.8)

        # Arraste
        self._drag_start_t = (0.0, 0.0)
        self._drag_start_p = (0.0, 0.0)
        self._dragging = False

        # Fade in
        self.opacity = 0
        Clock.schedule_once(
            lambda dt: Animation(opacity=1, duration=0.4).start(self), 0.4
        )

        # Solicitar permissão de overlay (apenas pede a permissão; overlay real requer Service)
        Clock.schedule_once(self._solicitar_overlay, 4.0)

    # ── Pulsação ──────────────────────────────────────────────────────────────

    def pulsar(self):
        """Anima a bolha pulsando para indicar atividade."""
        anim = (
            Animation(opacity=0.5, duration=0.4) +
            Animation(opacity=1.0, duration=0.4)
        )
        anim.repeat = True
        anim.start(self)

    def parar_pulsar(self):
        """Para a animação de pulsação."""
        Animation.cancel_all(self)
        self.opacity = 1.0

    # ── Dialog ────────────────────────────────────────────────────────────────

    def _criar_dialog(self, dt=None):
        try:
            from kivymd.uix.dialog import MDDialog
            from kivymd.uix.button import MDFlatButton

            self._dialog = MDDialog(
                title="Spica \u2736",
                text="Escolha uma opcao:",
                buttons=[
                    MDFlatButton(
                        text="CHAT",
                        on_release=lambda x: self._ir("chat"),
                    ),
                    MDFlatButton(
                        text="CONFIGURACOES",
                        on_release=lambda x: self._ir("configuracoes"),
                    ),
                ],
            )
        except Exception as e:
            print(f"[Spica] dialog criar: {e}")

    def _ir(self, tela):
        try:
            if self._dialog:
                self._dialog.dismiss()
        except Exception:
            pass
        Clock.schedule_once(
            lambda dt: MDApp.get_running_app().navigate_to(tela), 0.15
        )

    # ── Touch ─────────────────────────────────────────────────────────────────

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            touch.grab(self)
            self._drag_start_t = (touch.x, touch.y)
            self._drag_start_p = (self.x, self.y)
            self._dragging = False
            return True
        return False

    def on_touch_move(self, touch):
        if touch.grab_current is self:
            dx = touch.x - self._drag_start_t[0]
            dy = touch.y - self._drag_start_t[1]
            if abs(dx) > self.DRAG or abs(dy) > self.DRAG:
                self._dragging = True
            if self._dragging:
                self.pos = (
                    max(self.MARGEM, min(
                        self._drag_start_p[0] + dx,
                        Window.width - self.SIZE - self.MARGEM,
                    )),
                    max(self.MARGEM, min(
                        self._drag_start_p[1] + dy,
                        Window.height - self.SIZE - self.MARGEM,
                    )),
                )
            return True
        return False

    def on_touch_up(self, touch):
        if touch.grab_current is self:
            touch.ungrab(self)
            if self._dragging:
                self._grudar()
            else:
                Clock.schedule_once(self._abrir_menu, 0.05)
            return True
        return False

    def _grudar(self):
        alvo = (
            self.MARGEM if (self.x + self.SIZE / 2) < Window.width / 2
            else Window.width - self.SIZE - self.MARGEM
        )
        Animation(x=alvo, duration=0.25, t="out_cubic").start(self)

    def _abrir_menu(self, dt=None):
        if self._dialog is None:
            self._criar_dialog()
        if self._dialog:
            try:
                self._dialog.open()
            except Exception as e:
                print(f"[Spica] open dialog: {e}")
                MDApp.get_running_app().navigate_to("chat")

    # ── Overlay ───────────────────────────────────────────────────────────────

    def _solicitar_overlay(self, dt):
        """
        Solicita a permissão SYSTEM_ALERT_WINDOW.
        IMPORTANTE: mesmo com a permissão concedida, a bolha atual só aparece
        dentro do app Kivy. Para sobreposição real (como Chat Heads do Messenger),
        é necessário implementar um Android Foreground Service separado com
        WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY.
        """
        try:
            from kivy.utils import platform
            if platform != "android":
                return
            from jnius import autoclass
            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            Settings   = autoclass("android.provider.Settings")
            Intent     = autoclass("android.content.Intent")
            Uri        = autoclass("android.net.Uri")
            ctx = PythonActivity.mActivity
            if not Settings.canDrawOverlays(ctx):
                print("[Spica] Solicitando permissao de overlay...")
                ctx.startActivity(Intent(
                    Settings.ACTION_MANAGE_OVERLAY_PERMISSION,
                    Uri.parse(f"package:{ctx.getPackageName()}"),
                ))
            else:
                print("[Spica] Permissao de overlay ja concedida.")
        except Exception as e:
            print(f"[Spica] overlay request: {e}")
