# notes_screen.py — Tela de criação e listagem de notas
from kivy.metrics import dp
from kivy.clock import Clock
from kivy.uix.scrollview import ScrollView
from kivy.uix.floatlayout import FloatLayout
from kivymd.uix.screen import MDScreen
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel
from kivymd.uix.button import MDIconButton, MDFloatingActionButton
from kivymd.uix.toolbar import MDTopAppBar
from kivymd.uix.dialog import MDDialog
from kivymd.uix.textfield import MDTextField
from kivymd.uix.button import MDFlatButton
from kivymd.app import MDApp
from src.modules.notes import NotesManager
from src.utils.logger import WindLogger


class NotesScreen(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.logger = WindLogger()
        self.notas_m = NotesManager.get_instance()
        self.dialogo = None
        self._construir_layout()

    def _construir_layout(self):
        raiz = MDBoxLayout(orientation="vertical")
        raiz.add_widget(MDTopAppBar(
            title="Minhas Notas",
            left_action_items=[["arrow-left", lambda x: MDApp.get_running_app().navigate_to("home")]],
        ))

        self.scroll = ScrollView()
        self.lista = MDBoxLayout(orientation="vertical", size_hint_y=None, padding=dp(12), spacing=dp(8))
        self.lista.bind(minimum_height=self.lista.setter("height"))
        self.scroll.add_widget(self.lista)
        raiz.add_widget(self.scroll)

        fab = MDFloatingActionButton(icon="plus", pos_hint={"right": 0.95, "y": 0.02},
                                     on_release=self._nova_nota)
        container = FloatLayout()
        container.add_widget(raiz)
        container.add_widget(fab)
        self.add_widget(container)
        Clock.schedule_once(self._carregar_notas, 0.3)

    def _carregar_notas(self, dt=None):
        self.lista.clear_widgets()
        notas = self.notas_m.listar_todas()
        if not notas:
            self.lista.add_widget(MDLabel(text="Nenhuma nota.\nToque em + para criar!",
                                         halign="center", theme_text_color="Secondary"))
            return
        for nota in notas:
            self.lista.add_widget(self._criar_card_nota(nota))

    def _criar_card_nota(self, nota):
        card = MDCard(orientation="vertical", size_hint_y=None, height=dp(90),
                      padding=dp(12), radius=[dp(12)], elevation=2, ripple_behavior=True)
        card.add_widget(MDLabel(text=nota.get("titulo", "Sem titulo"), font_style="Subtitle1",
                                size_hint_y=None, height=dp(30)))
        preview = nota.get("conteudo", "")[:80] + ("..." if len(nota.get("conteudo", "")) > 80 else "")
        card.add_widget(MDLabel(text=preview, font_style="Caption", theme_text_color="Secondary"))
        card.bind(on_release=lambda x, n=nota: self._editar_nota(n))
        return card

    def _nova_nota(self, *args):
        self._abrir_dialogo_nota(None)

    def _editar_nota(self, nota):
        self._abrir_dialogo_nota(nota)

    def _abrir_dialogo_nota(self, nota):
        e_nova = nota is None
        campo_titulo = MDTextField(hint_text="Titulo", text="" if e_nova else nota.get("titulo", ""), mode="outlined")
        campo_conteudo = MDTextField(hint_text="Conteudo...", text="" if e_nova else nota.get("conteudo", ""),
                                     multiline=True, mode="outlined")
        corpo = MDBoxLayout(orientation="vertical", spacing=dp(12),
                            size_hint_y=None, height=dp(180), padding=dp(16))
        corpo.add_widget(campo_titulo)
        corpo.add_widget(campo_conteudo)

        def salvar(*a):
            titulo = campo_titulo.text.strip()
            if not titulo: return
            if e_nova: self.notas_m.criar(titulo, campo_conteudo.text.strip())
            else: self.notas_m.atualizar(nota["id"], titulo, campo_conteudo.text.strip())
            self.dialogo.dismiss()
            self._carregar_notas()

        def excluir(*a):
            if not e_nova: self.notas_m.deletar(nota["id"])
            self.dialogo.dismiss()
            self._carregar_notas()

        botoes = [MDFlatButton(text="Cancelar", on_release=lambda x: self.dialogo.dismiss())]
        if not e_nova:
            botoes.append(MDFlatButton(text="Excluir", on_release=excluir))
        botoes.append(MDFlatButton(text="Salvar", on_release=salvar))

        self.dialogo = MDDialog(title="Nova Nota" if e_nova else "Editar Nota",
                                type="custom", content_cls=corpo, buttons=botoes)
        self.dialogo.open()
