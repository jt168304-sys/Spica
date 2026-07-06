# history_screen.py — Historico de conversas
import os
import sqlite3
from kivy.metrics import dp
from kivy.uix.scrollview import ScrollView
from kivymd.uix.screen import MDScreen
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel
from kivymd.uix.toolbar import MDTopAppBar
from kivymd.uix.button import MDRaisedButton
from kivymd.app import MDApp


def _get_db_path():
    try:
        from android.storage import app_storage_path
        base = app_storage_path()
    except Exception:
        base = os.path.expanduser("~")
    return os.path.join(base, "spica_historico.db")


class HistoryScreen(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._construir_layout()

    def _construir_layout(self):
        raiz = MDBoxLayout(orientation="vertical")
        raiz.add_widget(MDTopAppBar(
            title="Conversas Anteriores",
            left_action_items=[["arrow-left", lambda x: MDApp.get_running_app().navigate_to("home")]],
            right_action_items=[["delete-sweep", lambda x: self._confirmar_limpeza()]],
        ))

        # Botão novo chat no topo
        topo = MDBoxLayout(size_hint_y=None, height=dp(56), padding=[dp(12), dp(8)])
        topo.add_widget(MDRaisedButton(
            text="+ Novo Chat",
            size_hint_x=1,
            on_release=lambda x: self._novo_chat()
        ))
        raiz.add_widget(topo)

        self.scroll = ScrollView(always_overscroll=False, do_scroll_x=False)
        self.lista = MDBoxLayout(
            orientation="vertical",
            size_hint_y=None,
            padding=dp(12),
            spacing=dp(8)
        )
        self.lista.bind(minimum_height=self.lista.setter("height"))
        self.scroll.add_widget(self.lista)
        raiz.add_widget(self.scroll)
        self.add_widget(raiz)

    def on_enter(self):
        self._carregar_sessoes()

    def _novo_chat(self):
        app = MDApp.get_running_app()
        chat = app.screen_manager.get_screen("chat")
        chat._limpar_chat()
        app.navigate_to("chat")

    def _carregar_sessoes(self):
        self.lista.clear_widgets()
        db_path = _get_db_path()
        if not os.path.exists(db_path):
            self._sem_dados("Nenhuma conversa salva ainda.")
            return
        try:
            con = sqlite3.connect(db_path)
            sessoes = con.execute(
                "SELECT sessao, COUNT(*) as total, MIN(ts) as inicio, MAX(ts) as fim "
                "FROM chats GROUP BY sessao ORDER BY inicio DESC LIMIT 50"
            ).fetchall()
            con.close()

            if not sessoes:
                self._sem_dados("Nenhuma conversa salva ainda.")
                return

            for sessao, total, inicio, fim in sessoes:
                data = inicio[:10] if inicio else "?"
                hora_i = inicio[11:16] if inicio else "?"
                hora_f = fim[11:16] if fim else "?"

                card = MDCard(
                    orientation="vertical",
                    size_hint_y=None, height=dp(80),
                    padding=[dp(16), dp(10)],
                    radius=[dp(12)], elevation=2,
                    ripple_behavior=True
                )
                linha1 = MDBoxLayout(size_hint_y=None, height=dp(28))
                linha1.add_widget(MDLabel(
                    text=f"{data}   {hora_i} - {hora_f}",
                    font_style="Subtitle2"
                ))
                linha2 = MDLabel(
                    text=f"{total} mensagens",
                    font_style="Caption",
                    theme_text_color="Secondary",
                    size_hint_y=None, height=dp(22)
                )
                card.add_widget(linha1)
                card.add_widget(linha2)
                card.bind(on_release=lambda x, s=sessao: self._abrir_sessao(s))
                self.lista.add_widget(card)

        except Exception as e:
            self._sem_dados(f"Erro: {e}")

    def _sem_dados(self, msg):
        self.lista.add_widget(MDLabel(
            text=msg, halign="center",
            size_hint_y=None, height=dp(60)
        ))

    def _abrir_sessao(self, sessao_id):
        app = MDApp.get_running_app()
        chat = app.screen_manager.get_screen("chat")
        chat.carregar_sessao(sessao_id)
        app.navigate_to("chat")

    def _confirmar_limpeza(self):
        from kivymd.uix.dialog import MDDialog
        from kivymd.uix.button import MDFlatButton
        dialogo = MDDialog(
            title="Apagar historico?",
            text="Todas as conversas serao removidas permanentemente.",
            buttons=[
                MDFlatButton(text="Cancelar", on_release=lambda x: dialogo.dismiss()),
                MDFlatButton(text="Apagar", on_release=lambda x: (dialogo.dismiss(), self._limpar_historico())),
            ]
        )
        dialogo.open()

    def _limpar_historico(self):
        try:
            con = sqlite3.connect(_get_db_path())
            con.execute("DELETE FROM chats")
            con.commit()
            con.close()
        except Exception:
            pass
        self._carregar_sessoes()
