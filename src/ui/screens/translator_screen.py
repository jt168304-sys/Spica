# translator_screen.py — Tradutor com suporte a imagens
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


IDIOMAS = [
    "Inglês", "Espanhol", "Francês", "Alemão", "Italiano",
    "Japonês", "Coreano", "Chinês", "Russo", "Árabe",
    "Português de Portugal", "Hindi"
]


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
        ))

        scroll = ScrollView(always_overscroll=False)
        corpo = MDBoxLayout(
            orientation="vertical",
            size_hint_y=None,
            padding=dp(16),
            spacing=dp(12)
        )
        corpo.bind(minimum_height=corpo.setter("height"))

        # Campo de texto entrada
        corpo.add_widget(MDLabel(
            text="Texto ou imagem para traduzir:",
            font_style="Subtitle2",
            size_hint_y=None, height=dp(28)
        ))

        self.campo_entrada = MDTextField(
            hint_text="Digite o texto aqui...",
            mode="rectangle",
            multiline=True,
            size_hint_y=None,
            height=dp(120),
        )
        corpo.add_widget(self.campo_entrada)

        # Botões de imagem
        linha_img = MDBoxLayout(size_hint_y=None, height=dp(50), spacing=dp(8))
        linha_img.add_widget(MDRaisedButton(
            text="📷 Câmera",
            size_hint_x=1,
            on_release=self._abrir_camera
        ))
        linha_img.add_widget(MDRaisedButton(
            text="🖼️ Galeria",
            size_hint_x=1,
            on_release=self._abrir_galeria
        ))
        corpo.add_widget(linha_img)

        # Preview da imagem selecionada
        self.label_imagem = MDLabel(
            text="",
            font_style="Caption",
            theme_text_color="Secondary",
            size_hint_y=None, height=dp(24)
        )
        corpo.add_widget(self.label_imagem)

        # Seleção de idioma
        corpo.add_widget(MDLabel(
            text="Traduzir para:",
            font_style="Subtitle2",
            size_hint_y=None, height=dp(28)
        ))

        self.campo_idioma = MDTextField(
            hint_text="Ex: inglês, japonês, espanhol...",
            mode="round",
            size_hint_y=None,
            height=dp(50),
        )
        self.campo_idioma.text = "Inglês"
        corpo.add_widget(self.campo_idioma)

        # Atalhos de idioma
        grade_idiomas = MDBoxLayout(
            orientation="horizontal",
            size_hint_y=None, height=dp(42),
            spacing=dp(6)
        )
        for idioma in ["Inglês", "Espanhol", "Japonês", "Francês"]:
            grade_idiomas.add_widget(MDFlatButton(
                text=idioma,
                size_hint_x=1,
                on_release=lambda x, i=idioma: setattr(self.campo_idioma, "text", i)
            ))
        corpo.add_widget(grade_idiomas)

        # Botão traduzir
        corpo.add_widget(MDRaisedButton(
            text="Traduzir",
            size_hint_y=None, height=dp(50),
            on_release=self._traduzir
        ))

        # Resultado
        self.card_resultado = MDCard(
            orientation="vertical",
            size_hint_y=None, height=dp(160),
            padding=dp(16), radius=[dp(12)], elevation=2
        )
        cabecalho = MDBoxLayout(size_hint_y=None, height=dp(30))
        cabecalho.add_widget(MDLabel(
            text="Tradução:", font_style="Subtitle2",
            size_hint_y=None, height=dp(30)
        ))
        self.btn_copiar = MDIconButton(
            icon="content-copy",
            size_hint=(None, None), size=(dp(36), dp(36)),
            on_release=self._copiar_resultado
        )
        cabecalho.add_widget(self.btn_copiar)
        self.card_resultado.add_widget(cabecalho)

        self.label_resultado = MDLabel(
            text="O resultado aparecerá aqui...",
            font_style="Body1",
        )
        self.card_resultado.add_widget(self.label_resultado)
        corpo.add_widget(self.card_resultado)

        scroll.add_widget(corpo)
        raiz.add_widget(scroll)
        self.add_widget(raiz)

    def _abrir_camera(self, *args):
        from src.ui.image_picker import ImagePicker
        ImagePicker(on_image=self._imagem_selecionada).open()

    def _abrir_galeria(self, *args):
        from src.ui.image_picker import ImagePicker
        p = ImagePicker(on_image=self._imagem_selecionada)
        p._abrir_galeria()

    def _imagem_selecionada(self, caminho):
        if not caminho:
            return
        self.caminho_imagem = caminho
        nome = os.path.basename(caminho)
        self.label_imagem.text = f"📸 Imagem: {nome}"
        self.campo_entrada.hint_text = "Opcional: instrução adicional para a tradução"

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
            prompt = f"Leia todo o texto visível nesta imagem e traduza para {idioma}. {instrucao}\nResponda APENAS com a tradução, sem explicações."
            GroqService.get_instance().perguntar(prompt, self._receber_traducao, caminho_imagem=imagem)
        else:
            prompt = f"Traduza para {idioma}. Responda APENAS com a tradução:\n\n{texto}"
            GroqService.get_instance().perguntar(prompt, self._receber_traducao)

    def _receber_traducao(self, resultado):
        self.label_resultado.text = resultado
        self.card_resultado.height = dp(max(160, len(resultado) // 2 + 80))

    def _copiar_resultado(self, *args):
        from kivy.core.clipboard import Clipboard
        Clipboard.copy(self.label_resultado.text)
