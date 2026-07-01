# translator_screen.py — Tradutor com câmera e arquivos
import os
from kivy.metrics import dp
from kivy.clock import Clock
from kivy.uix.scrollview import ScrollView
from kivymd.uix.screen import MDScreen
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.textfield import MDTextField
from kivymd.uix.button import MDRaisedButton, MDIconButton, MDFlatButton
from kivymd.uix.toolbar import MDTopAppBar
from kivymd.uix.card import MDCard
from kivymd.app import MDApp


class TranslatorScreen(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.caminho_imagem = None
        self._construir_layout()

    def _construir_layout(self):
        raiz = MDBoxLayout(orientation="vertical")

        raiz.add_widget(MDTopAppBar(
            title="Tradutor",
            left_action_items=[["arrow-left", lambda x: MDApp.get_running_app().navigate_to("home")]],
            right_action_items=[["content-copy", lambda x: self._copiar_resultado()]],
        ))

        scroll = ScrollView(always_overscroll=False, do_scroll_x=False)
        corpo = MDBoxLayout(
            orientation="vertical",
            size_hint_y=None,
            padding=dp(16),
            spacing=dp(14)
        )
        corpo.bind(minimum_height=corpo.setter("height"))

        # --- Campo de entrada ---
        self.campo_entrada = MDTextField(
            hint_text="Digite o texto para traduzir...",
            mode="outlined",
            multiline=True,
            size_hint_y=None,
            height=dp(130),
        )
        corpo.add_widget(self.campo_entrada)

        # --- Botão de imagem (único, abre popup) ---
        self.btn_imagem = MDRaisedButton(
            text="📎  Adicionar imagem",
            size_hint_y=None, height=dp(46),
            on_release=self._abrir_opcoes_imagem
        )
        corpo.add_widget(self.btn_imagem)

        # Preview nome da imagem
        self.label_imagem = MDLabel(
            text="",
            font_style="Caption",
            theme_text_color="Secondary",
            size_hint_y=None, height=dp(20)
        )
        corpo.add_widget(self.label_imagem)

        # --- Idioma destino ---
        corpo.add_widget(MDLabel(
            text="Traduzir para:",
            font_style="Subtitle2",
            size_hint_y=None, height=dp(26)
        ))

        self.campo_idioma = MDTextField(
            hint_text="Ex: inglês, japonês...",
            mode="outlined",
            size_hint_y=None,
            height=dp(48),
        )
        self.campo_idioma.text = "Inglês"
        corpo.add_widget(self.campo_idioma)

        # Atalhos de idioma
        atalhos = MDBoxLayout(
            orientation="horizontal",
            size_hint_y=None, height=dp(40),
            spacing=dp(4)
        )
        for idioma in ["Inglês", "Espanhol", "Japonês", "Francês"]:
            atalhos.add_widget(MDFlatButton(
                text=idioma,
                size_hint_x=1,
                on_release=lambda x, i=idioma: setattr(self.campo_idioma, "text", i)
            ))
        corpo.add_widget(atalhos)

        # --- Botão traduzir ---
        corpo.add_widget(MDRaisedButton(
            text="Traduzir",
            size_hint_y=None, height=dp(50),
            on_release=self._traduzir
        ))

        # --- Card resultado ---
        self.card_resultado = MDCard(
            orientation="vertical",
            size_hint_y=None, height=dp(160),
            padding=dp(14), radius=[dp(12)], elevation=2
        )
        topo_card = MDBoxLayout(size_hint_y=None, height=dp(32))
        topo_card.add_widget(MDLabel(
            text="Tradução:",
            font_style="Subtitle2",
        ))
        topo_card.add_widget(MDIconButton(
            icon="content-copy",
            size_hint=(None, None), size=(dp(36), dp(36)),
            on_release=lambda x: self._copiar_resultado()
        ))
        self.card_resultado.add_widget(topo_card)

        self.label_resultado = MDLabel(
            text="O resultado aparecerá aqui...",
            font_style="Body1",
        )
        self.card_resultado.add_widget(self.label_resultado)
        corpo.add_widget(self.card_resultado)

        scroll.add_widget(corpo)
        raiz.add_widget(scroll)
        self.add_widget(raiz)

    def _abrir_opcoes_imagem(self, *args):
        from kivymd.uix.dialog import MDDialog
        from kivymd.uix.button import MDFlatButton

        self._dialogo = MDDialog(
            title="Adicionar imagem",
            text="Escolha a origem:",
            buttons=[
                MDFlatButton(
                    text="📷  Câmera",
                    on_release=lambda x: (
                        self._dialogo.dismiss(),
                        Clock.schedule_once(lambda dt: self._usar_camera(), 0.3)
                    )
                ),
                MDFlatButton(
                    text="📁  Arquivos",
                    on_release=lambda x: (
                        self._dialogo.dismiss(),
                        Clock.schedule_once(lambda dt: self._usar_arquivos(), 0.3)
                    )
                ),
            ]
        )
        self._dialogo.open()

    def _usar_camera(self):
        pass  # _abrir_camera removida
        self._imagem_selecionada(None)  # camera nao disponivel

    def _usar_arquivos(self):
        from src.ui.screens.chat_screen import _abrir_seletor
        _abrir_seletor(self._imagem_selecionada)

    def _imagem_selecionada(self, caminho):
        if not caminho:
            self.label_imagem.text = "Nenhuma imagem selecionada."
            return
        self.caminho_imagem = caminho
        nome = os.path.basename(caminho)
        self.label_imagem.text = f"✅ {nome}"
        self.btn_imagem.text = "📎  Trocar imagem"

    def _traduzir(self, *args):
        texto = self.campo_entrada.text.strip()
        idioma = self.campo_idioma.text.strip() or "inglês"
        imagem = self.caminho_imagem

        if not texto and not imagem:
            self.label_resultado.text = "Digite um texto ou selecione uma imagem."
            return

        self.label_resultado.text = "Traduzindo..."

        from src.services.groq_service import GroqService

        if imagem:
            instrucao = texto or ""
            prompt = (
                f"Leia todo o texto visível nesta imagem e traduza para {idioma}."
                f" {instrucao}\nResponda APENAS com a tradução, sem explicações."
            )
            GroqService.get_instance().perguntar(
                prompt, self._receber_traducao, caminho_imagem=imagem
            )
        else:
            prompt = f"Traduza para {idioma}. Responda APENAS com a tradução:\n\n{texto}"
            GroqService.get_instance().perguntar(prompt, self._receber_traducao)

    def _receber_traducao(self, resultado):
        self.label_resultado.text = resultado
        # Ajusta altura do card conforme tamanho do texto
        linhas = max(3, resultado.count('\n') + len(resultado) // 40)
        self.card_resultado.height = dp(60 + linhas * 22)

    def _copiar_resultado(self):
        from kivy.core.clipboard import Clipboard
        if self.label_resultado.text and "aparecerá" not in self.label_resultado.text:
            Clipboard.copy(self.label_resultado.text)
