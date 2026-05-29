# calculator_screen.py — Calculadora com IA
from kivy.metrics import dp
from kivymd.uix.screen import MDScreen
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.textfield import MDTextField
from kivymd.uix.button import MDRaisedButton, MDIconButton
from kivymd.uix.toolbar import MDTopAppBar
from kivymd.uix.card import MDCard
from kivymd.uix.gridlayout import MDGridLayout
from kivymd.app import MDApp


class CalculatorScreen(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._expr = ""
        self._construir_layout()

    def _construir_layout(self):
        raiz = MDBoxLayout(orientation="vertical")
        raiz.add_widget(MDTopAppBar(
            title="Calculadora",
            left_action_items=[["arrow-left", lambda x: MDApp.get_running_app().navigate_to("home")]],
        ))

        corpo = MDBoxLayout(orientation="vertical", padding=dp(12), spacing=dp(8))

        # Display
        self.display = MDLabel(
            text="0",
            font_style="H4",
            halign="right",
            size_hint_y=None, height=dp(80),
        )
        corpo.add_widget(self.display)

        # Grid de botões
        grade = MDGridLayout(cols=4, spacing=dp(6), size_hint_y=None, height=dp(320))
        botoes = [
            ("C", "limpar"), ("(", "("), (")", ")"), ("/", "/"),
            ("7", "7"), ("8", "8"), ("9", "9"), ("×", "*"),
            ("4", "4"), ("5", "5"), ("6", "6"), ("-", "-"),
            ("1", "1"), ("2", "2"), ("3", "3"), ("+", "+"),
            ("0", "0"), (".", "."), ("⌫", "apagar"), ("=", "calcular"),
        ]
        for label, valor in botoes:
            btn = MDRaisedButton(
                text=label,
                size_hint=(1, 1),
                on_release=lambda x, v=valor: self._botao(v)
            )
            grade.add_widget(btn)
        corpo.add_widget(grade)

        # Campo para perguntas à IA
        corpo.add_widget(MDLabel(
            text="Perguntar à IA:",
            font_style="Caption", size_hint_y=None, height=dp(24)
        ))
        linha_ia = MDBoxLayout(size_hint_y=None, height=dp(50), spacing=dp(8))
        self.campo_ia = MDTextField(hint_text="Ex: quanto é 15% de 200?", mode="round", size_hint_x=1)
        linha_ia.add_widget(self.campo_ia)
        linha_ia.add_widget(MDRaisedButton(text="→", size_hint_x=None, width=dp(50), on_release=self._perguntar_ia))
        corpo.add_widget(linha_ia)

        self.label_ia = MDLabel(text="", font_style="Body2", size_hint_y=None, height=dp(40))
        corpo.add_widget(self.label_ia)

        raiz.add_widget(corpo)
        self.add_widget(raiz)

    def _botao(self, valor):
        if valor == "limpar":
            self._expr = ""
            self.display.text = "0"
        elif valor == "apagar":
            self._expr = self._expr[:-1]
            self.display.text = self._expr or "0"
        elif valor == "calcular":
            try:
                resultado = eval(self._expr)
                self.display.text = str(resultado)
                self._expr = str(resultado)
            except Exception:
                self.display.text = "Erro"
                self._expr = ""
        else:
            self._expr += valor
            self.display.text = self._expr

    def _perguntar_ia(self, *args):
        pergunta = self.campo_ia.text.strip()
        if not pergunta:
            return
        self.label_ia.text = "Calculando..."
        from src.services.groq_service import GroqService
        prompt = f"Resolva este calculo ou problema matematico de forma direta e objetiva: {pergunta}"
        GroqService.get_instance().perguntar(prompt, lambda r: setattr(self.label_ia, "text", r))
