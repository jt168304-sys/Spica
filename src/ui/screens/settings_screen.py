# settings_screen.py — Configuracoes do Spica
from kivy.metrics import dp
from kivy.uix.scrollview import ScrollView
from kivy.uix.switch import Switch
from kivymd.uix.screen import MDScreen
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel
from kivymd.uix.list import MDList, TwoLineIconListItem, IconLeftWidget
from kivymd.uix.toolbar import MDTopAppBar
from kivymd.app import MDApp


class SettingsScreen(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._construir_layout()

    def _construir_layout(self):
        raiz = MDBoxLayout(orientation="vertical")
        raiz.add_widget(MDTopAppBar(
            title="Configuracoes",
            left_action_items=[["arrow-left", lambda x: MDApp.get_running_app().navigate_to("chat")]],
        ))
        scroll = ScrollView()
        lista = MDList(padding=dp(8))

        lista.add_widget(self._card_api_key())
        lista.add_widget(self._card_overlay())

        for cfg in [
            {"icone": "theme-light-dark", "titulo": "Modo Escuro",
             "sub": "Alternar tema claro/escuro", "chave": "theme_mode", "valor_on": "Dark"},
        ]:
            lista.add_widget(self._item_switch(cfg))

        item_sobre = TwoLineIconListItem(
            text="Sobre o Spica",
            secondary_text="VTuber-IA • Python + KivyMD + Groq",
        )
        item_sobre.add_widget(IconLeftWidget(icon="information-outline"))
        lista.add_widget(item_sobre)

        scroll.add_widget(lista)
        raiz.add_widget(scroll)
        self.add_widget(raiz)

    # ── Cards ─────────────────────────────────────────────────────────────────

    def _card_api_key(self):
        app = MDApp.get_running_app()
        tem_key = bool(app.settings.get("api_key", "").strip())

        card = MDCard(
            orientation="vertical",
            size_hint_y=None, height=dp(130),
            padding=dp(16), spacing=dp(8),
            radius=[dp(12)], elevation=4,
            md_bg_color=([0.07, 0.35, 0.07, 1] if tem_key else [0.35, 0.07, 0.07, 1]),
        )
        status = "Conectada ✓" if tem_key else "Nao configurada"
        card.add_widget(MDLabel(
            text=f"Groq API Key — {status}",
            font_style="Subtitle1", halign="left",
        ))
        card.add_widget(MDLabel(
            text="console.groq.com (gratuito)" if not tem_key else "IA respondendo normalmente",
            font_style="Caption", theme_text_color="Secondary",
        ))
        from kivymd.uix.button import MDRaisedButton
        card.add_widget(MDRaisedButton(
            text="Inserir chave" if not tem_key else "Alterar chave",
            size_hint_y=None, height=dp(36),
            on_release=lambda x: self._dialogo_api_key(),
        ))
        return card

    def _card_overlay(self):
        from kivy.utils import platform
        card = MDCard(
            orientation="vertical",
            size_hint_y=None, height=dp(110),
            padding=dp(16), spacing=dp(8),
            radius=[dp(12)], elevation=4,
        )
        card.add_widget(MDLabel(
            text="Sobreposicao de Apps",
            font_style="Subtitle1", halign="left",
        ))
        card.add_widget(MDLabel(
            text="Permite a bolha flutuar sobre outros aplicativos",
            font_style="Caption", theme_text_color="Secondary",
        ))
        from kivymd.uix.button import MDRaisedButton
        card.add_widget(MDRaisedButton(
            text="Ativar permissao de sobreposicao",
            size_hint_y=None, height=dp(36),
            on_release=lambda x: MDApp.get_running_app().permission_manager.pedir_overlay(),
        ))
        return card

    # ── Switch ────────────────────────────────────────────────────────────────

    def _item_switch(self, cfg):
        app = MDApp.get_running_app()
        atual  = app.settings.get(cfg["chave"], cfg["valor_on"])
        ligado = (atual == cfg["valor_on"]) if isinstance(cfg["valor_on"], str) else bool(atual)

        item = TwoLineIconListItem(text=cfg["titulo"], secondary_text=cfg["sub"])
        item.add_widget(IconLeftWidget(icon=cfg["icone"]))
        sw = Switch(active=ligado, size_hint=(None, None), size=(dp(60), dp(30)),
                    pos_hint={"center_y": 0.5})
        sw.bind(active=lambda inst, val, c=cfg: self._salvar_switch(c, val))
        item.add_widget(sw)
        return item

    def _salvar_switch(self, cfg, ativo):
        app = MDApp.get_running_app()
        if isinstance(cfg["valor_on"], str):
            valor = cfg["valor_on"] if ativo else ("Light" if cfg["valor_on"] == "Dark" else "")
        else:
            valor = ativo
        app.settings.set(cfg["chave"], valor)
        if cfg["chave"] == "theme_mode":
            MDApp.get_running_app().toggle_theme()

    # ── Dialogo API Key ───────────────────────────────────────────────────────

    def _dialogo_api_key(self):
        from kivymd.uix.dialog import MDDialog
        from kivymd.uix.textfield import MDTextField
        from kivymd.uix.button import MDFlatButton

        app = MDApp.get_running_app()
        campo = MDTextField(
            hint_text="Cole sua Groq API key aqui",
            text=app.settings.get("api_key", ""),
            mode="round",
        )
        instrucoes = MDLabel(
            text="1. Acesse console.groq.com\n2. Crie conta gratuita\n3. Gere uma API Key\n4. Cole aqui",
            font_style="Caption", theme_text_color="Secondary",
            size_hint_y=None, height=dp(70),
        )
        corpo = MDBoxLayout(
            orientation="vertical", spacing=dp(8),
            size_hint_y=None, height=dp(150), padding=dp(8),
        )
        corpo.add_widget(instrucoes)
        corpo.add_widget(campo)

        def salvar(*a):
            app.settings.set("api_key", campo.text.strip())
            dialogo.dismiss()
            self.clear_widgets()
            self._construir_layout()

        dialogo = MDDialog(
            title="Groq API Key",
            type="custom",
            content_cls=corpo,
            buttons=[
                MDFlatButton(text="Cancelar", on_release=lambda x: dialogo.dismiss()),
                MDFlatButton(text="Salvar",   on_release=salvar),
            ],
        )
        dialogo.open()
