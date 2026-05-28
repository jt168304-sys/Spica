# history_screen.py — Tela de histórico de conversas
import os
import sqlite3
from kivy.metrics import dp
from kivy.clock import Clock
from kivy.uix.scrollview import ScrollView
from kivymd.uix.screen import MDScreen
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel
from kivymd.uix.toolbar import MDTopAppBar
from kivymd.uix.button import MDIconButton
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
            title="Historico de Chats",
            left_action_items=[["arrow-left", lambda x: MDApp.get_running_app().navigate_to("home")]],
            right_action_items=[["delete-sweep", lambda x: self._limpar_historico()]],
        ))

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

    def _carregar_sessoes(self):
        self.lista.clear_widgets()
        db_path = _get_db_path()
        if not os.path.exists(db_path):
            self.lista.add_widget(MDLabel(
                text="Nenhum historico encontrado.",
                halign="center", size_hint_y=None, height=dp(50)
            ))
            return
        try:
            con = sqlite3.connect(db_path)
            sessoes = con.execute(
                "SELECT sessao, COUNT(*) as total, MIN(ts) as inicio FROM chats GROUP BY sessao ORDER BY inicio DESC LIMIT 50"
            ).fetchall()
            con.close()

            if not sessoes:
                self.lista.add_widget(MDLabel(
                    text="Nenhuma conversa salva ainda.",
                    halign="center", size_hint_y=None, height=dp(50)
                ))
                return

            for sessao, total, inicio in sessoes:
                data = inicio[:10] if inicio else "?"
                hora = inicio[11:16] if inicio else "?"
                card = MDCard(
                    orientation="vertical",
                    size_hint_y=None, height=dp(70),
                    padding=dp(12), radius=[dp(12)], elevation=2,
                    ripple_behavior=True
                )
                card.add_widget(MDLabel(
                    text=f"Conversa de {data} as {hora}",
                    font_style="Subtitle2", size_hint_y=None, height=dp(30)
                ))
                card.add_widget(MDLabel(
                    text=f"{total} mensagens",
                    font_style="Caption", theme_text_color="Secondary",
                    size_hint_y=None, height=dp(20)
                ))
                card.bind(on_release=lambda x, s=sessao: self._abrir_sessao(s))
                self.lista.add_widget(card)
        except Exception as e:
            self.lista.add_widget(MDLabel(
                text=f"Erro ao carregar: {e}",
                halign="center", size_hint_y=None, height=dp(50)
            ))

    def _abrir_sessao(self, sessao_id):
        # Navega para o chat com o histórico da sessão carregado
        app = MDApp.get_running_app()
        chat = app.screen_manager.get_screen("chat")
        chat.carregar_sessao(sessao_id)
        app.navigate_to("chat")

    def _limpar_historico(self):
        db_path = _get_db_path()
        try:
            con = sqlite3.connect(db_path)
            con.execute("DELETE FROM chats")
            con.commit()
            con.close()
            self._carregar_sessoes()
        except Exception as e:
            pass
