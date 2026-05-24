# chat_screen.py — Chat com WindIA: comandos locais + IA Groq Visão
import os
from kivy.metrics import dp
from kivy.clock import Clock
from kivy.uix.scrollview import ScrollView
from kivymd.uix.screen import MDScreen
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel
from kivymd.uix.textfield import MDTextField
from kivymd.uix.button import MDIconButton
from kivymd.uix.toolbar import MDTopAppBar
from kivymd.uix.filemanager import MDFileManager
from kivymd.app import MDApp
from src.modules.commands import CommandProcessor
from src.utils.logger import WindLogger


class ChatScreen(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.logger = WindLogger()
        self.processor = CommandProcessor.get_instance()
        self._bolha_digitando = None
        self.caminho_imagem_selecionada = None
        
        # Inicializa o gerenciador de arquivos do KivyMD
        self.file_manager = MDFileManager(
            exit_manager=self._fechar_gerenciador,
            select_path=self._imagem_selecionada,
            preview=True
        )
        
        self._construir_layout()

    def _construir_layout(self):
        raiz = MDBoxLayout(orientation="vertical")

        raiz.add_widget(MDTopAppBar(
            title="WindIA",
            left_action_items=[["arrow-left", lambda x: MDApp.get_running_app().navigate_to("home")]],
            right_action_items=[
                ["delete-sweep", lambda x: self._limpar_chat()],
                ["microphone",   lambda x: self._ativar_voz()],
            ],
        ))

        self.scroll = ScrollView()
        self.msgs = MDBoxLayout(orientation="vertical", size_hint_y=None, padding=dp(12), spacing=dp(8))
        self.msgs.bind(minimum_height=self.msgs.setter("height"))
        self.scroll.add_widget(self.msgs)
        raiz.add_widget(self.scroll)

        # Entrada de texto com botão de anexo embutido na barra inferior
        entrada = MDBoxLayout(size_hint_y=None, height=dp(60), padding=[dp(8), dp(4)], spacing=dp(4))
        
        self.btn_anexo = MDIconButton(icon="paperclip", on_release=self._abrir_gerenciador)
        entrada.add_widget(self.btn_anexo)

        self.campo = MDTextField(hint_text="Mensagem...", mode="round", multiline=False)
        self.campo.bind(on_text_validate=self._enviar)
        entrada.add_widget(self.campo)
        
        entrada.add_widget(MDIconButton(icon="send", on_release=self._enviar))
        raiz.add_widget(entrada)

        self.add_widget(raiz)
        Clock.schedule_once(self._boas_vindas, 0.5)

    def _abrir_gerenciador(self, *args):
        """Abre o seletor na memória interna do Android ou na pasta Home do PC"""
        pasta_inicial = "/sdcard" if os.path.exists("/sdcard") else os.path.expanduser("~")
        self.file_manager.show(pasta_inicial)

    def _fechar_gerenciador(self, *args):
        self.file_manager.close()

    def _imagem_selecionada(self, caminho_arquivo):
        self._fechar_gerenciador()
        extensao = os.path.splitext(caminho_arquivo)[1].lower()
        
        if extensao in ['.png', '.jpg', '.jpeg']:
            self.caminho_imagem_selecionada = caminho_arquivo
            self.btn_anexo.icon = "image-check"
            self.campo.hint_text = "Imagem pronta! Faça sua pergunta..."
        else:
            self.campo.hint_text = "Formato inválido! Escolha JPG ou PNG."

    def _boas_vindas(self, dt):
        from src.services.groq_service import GroqService
        tem_key = GroqService.get_instance().disponivel
        if tem_key:
            self._wind("Ola! Sou o WindIA, pronta para ajudar.\nAgora você pode anexar fotos pelo clipe de papel!")
        else:
            self._wind("Ola! Sou o WindIA.\n\nPara respostas inteligentes, va em Configuracoes e insira sua API key da Groq.")

    def _enviar(self, *args):
        texto = self.campo.text.strip()
        imagem = self.caminho_imagem_selecionada
        
        if not texto and not imagem:
            return
            
        self.campo.text = ""
        self.caminho_imagem_selecionada = None
        self.btn_anexo.icon = "paperclip"
        self.campo.hint_text = "Mensagem..."

        if imagem:
            nome_foto = os.path.basename(imagem)
            self._usuario(f"📸 [Imagem: {nome_foto}]\n{texto}")
            self._mostrar_digitando()
            
            # Ignora comandos locais se houver imagem e joga direto para o serviço de visão do Groq
            from src.services.groq_service import GroqService
            GroqService.get_instance().perguntar(texto, self._receber_resposta, caminho_imagem=imagem)
        else:
            self._usuario(texto)
            self._mostrar_digitando()
            self.processor.processar(texto, callback=self._receber_resposta)

    def _receber_resposta(self, resposta: str):
        self._remover_digitando()
        self._wind(resposta)

    def _usuario(self, texto):
        self.msgs.add_widget(Bolha(texto=texto, autor="usuario"))
        self._scroll_baixo()

    def _wind(self, texto):
        self.msgs.add_widget(Bolha(texto=texto, autor="wind"))
        self._scroll_baixo()

    def _mostrar_digitando(self):
        self._bolha_digitando = Bolha(texto="...", autor="wind")
        self.msgs.add_widget(self._bolha_digitando)
        self._scroll_baixo()

    def _remover_digitando(self):
        if self._bolha_digitando and self._bolha_digitando in self.msgs.children:
            self.msgs.remove_widget(self._bolha_digitando)
        self._bolha_digitando = None

    def _limpar_chat(self):
        self.msgs.clear_widgets()
        from src.services.groq_service import GroqService
        GroqService.get_instance().limpar_historico()
        self._wind("Chat limpo! Como posso ajudar?")

    def _scroll_baixo(self):
        Clock.schedule_once(lambda dt: setattr(self.scroll, "scroll_y", 0), 0.1)

    def _ativar_voz(self):
        from src.services.voice_service import VoiceService
        app = MDApp.get_running_app()
        if hasattr(app, "bubble"):
            app.bubble.pulsar()
        VoiceService.get_instance().ouvir(callback=lambda t: (self._usuario(t), self._mostrar_digitando(),
                                                               self.processor.processar(t, self._receber_resposta)))


class Bolha(MDBoxLayout):
    def __init__(self, texto, autor, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "horizontal"
        self.size_hint_y = None
        self.padding = [dp(4), dp(2)]

        e_usuario = (autor == "usuario")
        card = MDCard(
            size_hint=(0.78, None), padding=dp(12), elevation=2,
            radius=[dp(16), dp(16), dp(4 if e_usuario else 16), dp(16 if e_usuario else 4)],
        )
        label = MDLabel(text=texto, size_hint_y=None, font_style="Body2")
        label.bind(texture_size=lambda i, v: setattr(i, "height", v[1] + dp(8)))
        card.bind(minimum_height=card.setter("height"))
        card.add_widget(label)

        espaco = MDBoxLayout(size_hint_x=0.22)
        self.add_widget(espaco if e_usuario else card)
        self.add_widget(card if e_usuario else espaco)
        self.bind(minimum_height=self.setter("height"))
