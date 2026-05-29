# voice_screen.py — Assistente de Voz
from kivy.metrics import dp
from kivy.clock import Clock
from kivymd.uix.screen import MDScreen
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.button import MDIconButton, MDRaisedButton
from kivymd.uix.toolbar import MDTopAppBar
from kivymd.uix.card import MDCard
from kivymd.app import MDApp


class VoiceScreen(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._construir_layout()

    def _construir_layout(self):
        raiz = MDBoxLayout(orientation="vertical")
        raiz.add_widget(MDTopAppBar(
            title="Assistente de Voz",
            left_action_items=[["arrow-left", lambda x: MDApp.get_running_app().navigate_to("home")]],
        ))

        corpo = MDBoxLayout(orientation="vertical", padding=dp(24), spacing=dp(16))

        self.label_status = MDLabel(
            text="Toque no microfone para falar",
            font_style="H6", halign="center",
            size_hint_y=None, height=dp(60)
        )
        corpo.add_widget(self.label_status)

        # Botão grande de microfone
        btn_mic = MDCard(
            size_hint=(None, None), size=(dp(120), dp(120)),
            radius=[dp(60)], elevation=8,
            pos_hint={"center_x": 0.5},
            ripple_behavior=True
        )
        btn_mic.add_widget(MDIconButton(
            icon="microphone",
            icon_size=dp(60),
            pos_hint={"center_x": 0.5, "center_y": 0.5},
            on_release=self._ativar_voz
        ))
        corpo.add_widget(btn_mic)

        self.label_resultado = MDLabel(
            text="",
            font_style="Body1", halign="center",
            size_hint_y=None, height=dp(100)
        )
        corpo.add_widget(self.label_resultado)

        raiz.add_widget(corpo)
        self.add_widget(raiz)

    def _ativar_voz(self, *args):
        self.label_status.text = "Ouvindo..."
        from src.services.voice_service import VoiceService
        VoiceService.get_instance().ouvir(callback=self._receber_texto)

    def _receber_texto(self, texto):
        self.label_resultado.text = f'Voce disse:\n"{texto}"'
        self.label_status.text = "Processando..."
        from src.modules.commands import CommandProcessor
        CommandProcessor.get_instance().processar(texto, callback=self._receber_resposta)

    def _receber_resposta(self, resposta):
        self.label_resultado.text = f"Spica:\n{resposta}"
        self.label_status.text = "Toque no microfone para falar"
