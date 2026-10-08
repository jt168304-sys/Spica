# live2d_teste_screen.py — Tela de TESTE do modelo Live2D (etapa 1 da 1.2)
# Abre o modelo numa WebView dentro de uma tela normal do app, com diagnóstico
# visível (WebGL, bibliotecas, erro). Quando funcionar aqui, vai para a bolha.
import os
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.utils import platform
from kivymd.app import MDApp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDRaisedButton
from kivymd.uix.gridlayout import MDGridLayout
from kivymd.uix.screen import MDScreen
from src.ui import tema as T

HAS_ANDROID = False
if platform == "android":
    try:
        from jnius import autoclass, cast
        from android.runnable import run_on_ui_thread
        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        WebView = autoclass("android.webkit.WebView")
        WebViewClient = autoclass("android.webkit.WebViewClient")
        LayoutParams = autoclass("android.widget.FrameLayout$LayoutParams")
        Gravity = autoclass("android.view.Gravity")
        HAS_ANDROID = True
    except Exception as e:
        print(f"[Spica/Live2D] jnius indisponível: {e}")

if not HAS_ANDROID:
    def run_on_ui_thread(func):
        return func

FRACAO_WEBVIEW = 0.58   # parte de cima da tela reservada para o modelo


class Live2DTesteScreen(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._wv = None
        T.estilizar(self, md_bg_color=T.FUNDO)
        raiz = MDBoxLayout(orientation="vertical")
        T.estilizar(raiz, md_bg_color=T.FUNDO)
        # espaço onde a WebView (nativa) fica por cima
        raiz.add_widget(MDBoxLayout(size_hint_y=FRACAO_WEBVIEW))
        grade = MDGridLayout(cols=2, spacing=dp(8), padding=dp(12), size_hint_y=1 - FRACAO_WEBVIEW)
        for rotulo, js in [
            ("Boca: falar", "SpicaLive2D.falarSimples(true)"),
            ("Boca: parar", "SpicaLive2D.falarSimples(false)"),
            ("Neutro", "SpicaLive2D.setHumor('neutro')"),
            ("Feliz", "SpicaLive2D.setHumor('feliz')"),
            ("Surpresa", "SpicaLive2D.setHumor('surpresa')"),
            ("Confusa", "SpicaLive2D.setHumor('confusa')"),
            ("Triste", "SpicaLive2D.setHumor('triste')"),
            ("Chocada", "SpicaLive2D.setHumor('chocada')"),
        ]:
            grade.add_widget(self._botao(rotulo, lambda x, js=js: self._js(js)))
        grade.add_widget(self._botao("Voltar", lambda x: self._voltar()))
        raiz.add_widget(grade)
        self.add_widget(raiz)

    def _botao(self, texto, acao):
        b = MDRaisedButton(text=texto, size_hint_x=1, on_release=acao)
        return T.estilizar(b, md_bg_color=T.MENTA, theme_text_color="Custom", text_color=T.FUNDO)

    # ---------------------------------------------------------------- ciclo da tela
    def on_enter(self, *args):
        if not HAS_ANDROID:
            return
        altura = int(Window.height * FRACAO_WEBVIEW)
        Clock.schedule_once(lambda dt: self._criar_webview(Window.width, altura), 0.1)

    def on_pre_leave(self, *args):
        self._remover_webview()

    def _voltar(self):
        self._remover_webview()
        MDApp.get_running_app().navigate_to("configuracoes")

    # ---------------------------------------------------------------- WebView
    @run_on_ui_thread
    def _criar_webview(self, largura, altura):
        try:
            if self._wv is not None:
                return
            ctx = PythonActivity.mActivity
            wv = WebView(ctx)
            s = wv.getSettings()
            s.setJavaScriptEnabled(True)
            s.setDomStorageEnabled(True)
            s.setAllowFileAccess(True)
            try:  # necessário para o modelo/Cubism carregarem via file://
                s.setAllowFileAccessFromFileURLs(True)
                s.setAllowUniversalAccessFromFileURLs(True)
            except Exception as e:
                print(f"[Spica/Live2D] acesso a arquivos: {e}")
            wv.setBackgroundColor(0)         # fundo transparente
            # IMPORTANTE: sem setLayerType(SOFTWARE) — WebGL precisa de aceleração por hardware
            wv.setWebViewClient(WebViewClient())
            ctx.addContentView(wv, LayoutParams(largura, altura, Gravity.TOP))
            base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
            wv.loadUrl("file://" + os.path.join(base, "assets", "live2d", "index.html"))
            self._wv = wv
            print("[Spica/Live2D] WebView criada")
        except Exception as e:
            print(f"[Spica/Live2D] erro ao criar WebView: {e}")

    @run_on_ui_thread
    def _remover_webview(self):
        wv, self._wv = self._wv, None
        if wv is None:
            return
        try:
            cast("android.view.ViewGroup", wv.getParent()).removeView(wv)
            wv.destroy()
            print("[Spica/Live2D] WebView removida")
        except Exception as e:
            print(f"[Spica/Live2D] erro ao remover WebView: {e}")

    def _js(self, codigo):
        self._executar_js(codigo)

    @run_on_ui_thread
    def _executar_js(self, codigo):
        try:
            if self._wv is not None:
                self._wv.evaluateJavascript(codigo, None)
        except Exception as e:
            print(f"[Spica/Live2D] js: {e}")
