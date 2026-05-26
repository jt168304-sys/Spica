# home_screen.py — Tela inicial com saudação, status e atalhos
import datetime
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.uix.gridlayout import GridLayout
from kivymd.uix.screen import MDScreen
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel
from kivymd.uix.button import MDIconButton
from kivymd.app import MDApp


class HomeScreen(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._construir_layout()
        Clock.schedule_interval(self._atualizar_saudacao, 60)

    def _construir_layout(self):
        raiz = MDBoxLayout(orientation="vertical", padding=dp(16), spacing=dp(12))
        raiz.add_widget(self._criar_cabecalho())
        raiz.add_widget(self._criar_card_status())
        raiz.add_widget(self._criar_grade_atalhos())
        self.add_widget(raiz)

    def _criar_cabecalho(self):
        layout = MDBoxLayout(orientation="vertical", size_hint_y=None, height=dp(100),
                             padding=[dp(8), dp(16), dp(8), dp(8)])
        self.label_saudacao = MDLabel(text=self._gerar_saudacao(), font_style="H5", halign="center")
        self.label_sub = MDLabel(text="Como posso ajudar você hoje?", font_style="Caption",
                                 halign="center", theme_text_color="Secondary")
        layout.add_widget(self.label_saudacao)
        layout.add_widget(self.label_sub)
        return layout

    def _criar_card_status(self):
        card = MDCard(orientation="horizontal", size_hint_y=None, height=dp(80),
                      padding=dp(16), spacing=dp(12), radius=[dp(16)], elevation=4)
        card.add_widget(MDLabel(text="W", font_size=dp(36), size_hint=(None, None), size=(dp(50), dp(50))))
        col = MDBoxLayout(orientation="vertical")
        self.label_status = MDLabel(text="Spica esta pronta!", font_style="Subtitle1")
        self.label_status_sub = MDLabel(text="Toque na bolha ou diga 'Hey Spica'",
                                        font_style="Caption", theme_text_color="Secondary")
        col.add_widget(self.label_status)
        col.add_widget(self.label_status_sub)
        card.add_widget(col)
        return card

    def _criar_grade_atalhos(self):
        container = MDBoxLayout(orientation="vertical", spacing=dp(8))
        container.add_widget(MDLabel(text="Atalhos Rapidos", font_style="Subtitle2",
                                     size_hint_y=None, height=dp(30), theme_text_color="Secondary"))
        grade = GridLayout(cols=2, spacing=dp(10))
        atalhos = [
            ("microphone",       "Assistente de Voz", "chat"),
            ("chat-outline",     "Chat com Spica",     "chat"),
            ("notebook-outline", "Minhas Notas",      "notas"),
            ("calculator",       "Calculadora",       "chat"),
            ("translate",        "Tradutor",          "chat"),
            ("cog-outline",      "Configuracoes",     "configuracoes"),
        ]
        for icon, nome, destino in atalhos:
            grade.add_widget(self._criar_card_atalho(icon, nome, destino))
        container.add_widget(grade)
        return container

    def _criar_card_atalho(self, icon, nome, destino):
        card = MDCard(orientation="vertical", size_hint_y=None, height=dp(90),
                      padding=dp(12), spacing=dp(4), radius=[dp(12)], elevation=2,
                      ripple_behavior=True)
        card.bind(on_release=lambda x, d=destino: MDApp.get_running_app().navigate_to(d))
        card.add_widget(MDIconButton(icon=icon, pos_hint={"center_x": 0.5}, disabled=True))
        card.add_widget(MDLabel(text=nome, font_style="Caption", halign="center"))
        return card

    def _gerar_saudacao(self):
        hora = datetime.datetime.now().hour
        if 5 <= hora < 12:   return "Bom dia!"
        elif 12 <= hora < 18: return "Boa tarde!"
        else:                 return "Boa noite!"

    def _atualizar_saudacao(self, dt):
        self.label_saudacao.text = self._gerar_saudacao()

    def atualizar_status(self, mensagem, submensagem=""):
        self.label_status.text = mensagem
        self.label_status_sub.text = submensagem
