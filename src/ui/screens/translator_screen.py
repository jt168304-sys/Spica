# translator_screen.py — Tradutor
from kivy.metrics import dp
from kivy.uix.scrollview import ScrollView
from kivymd.uix.screen import MDScreen
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.textfield import MDTextField
from kivymd.uix.button import MDRaisedButton
from kivymd.uix.toolbar import MDTopAppBar
from kivymd.uix.card import MDCard
from kivymd.app import MDApp


class TranslatorScreen(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._construir_layout()

    def _construir_layout(self):
        raiz = MDBoxLayout(orientation="vertical")
        raiz.add_widget(MDTopAppBar(
            title="Tradutor",
            left_action_items=[["arrow-left", lambda x: MDApp.get_running_app().navigate_to("home")]],
        ))

        corpo = MDBoxLayout(orientation="vertical", padding=dp(16), spacing=dp(12))

        self.campo_entrada = MDTextField(
            hint_text="Digite o texto para traduzir...",
            mode="rectangle",
            multiline=True,
            size_hint_y=None,
            height=dp(120),
        )
        corpo.add_widget(self.campo_entrada)

        self.campo_idioma = MDTextField(
            hint_text="Para qual idioma? (ex: ingles, espanhol, japones)",
            mode="round",
            size_hint_y=None,
            height=dp(50),
        )
        corpo.add_widget(self.campo_idioma)

        corpo.add_widget(MDRaisedButton(
            text="Traduzir",
            size_hint_y=None, height=dp(46),
            on_release=self._traduzir
        ))

        self.card_resultado = MDCard(
            size_hint_y=None, height=dp(150),
            padding=dp(16), radius=[dp(12)], elevation=2
        )
        self.label_resultado = MDLabel(
            text="O resultado aparecerá aqui...",
            font_style="Body1"
        )
        self.card_resultado.add_widget(self.label_resultado)
        corpo.add_widget(self.card_resultado)

        raiz.add_widget(corpo)
        self.add_widget(raiz)

    def _traduzir(self, *args):
        texto = self.campo_entrada.text.strip()
        idioma = self.campo_idioma.text.strip() or "ingles"
        if not texto:
            return
        self.label_resultado.text = "Traduzindo..."
        from src.services.groq_service import GroqService
        prompt = f"Traduza o seguinte texto para {idioma}. Responda APENAS com a traducao, sem explicacoes:\n\n{texto}"
        GroqService.get_instance().perguntar(prompt, self._receber_traducao)

    def _receber_traducao(self, resultado):
        self.label_resultado.text = resultado
