# settings_screen.py — Spica v14 (Otimizado para KivyMD 1.2.0)
from kivy.metrics import dp
from kivy.uix.scrollview import ScrollView
from kivy.uix.switch import Switch
from kivy.clock import Clock
from kivymd.uix.screen import MDScreen
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel
from kivymd.uix.button import MDRaisedButton, MDFlatButton, MDIconButton
from kivymd.uix.list import MDList, TwoLineIconListItem, IconLeftWidget
from kivymd.uix.toolbar import MDTopAppBar
from kivymd.app import MDApp


class SettingsScreen(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._construir_layout()

    def _construir_layout(self):
        raiz = MDBoxLayout(orientation="vertical")

        # Barra de ferramentas KivyMD 1.2.0
        barra_superior = MDTopAppBar(title="Configurações", left_action_items=[["arrow-left", lambda x: MDApp.get_running_app().navigate_to("chat")]])
        raiz.add_widget(barra_superior)

        scroll = ScrollView(do_scroll_x=False, do_scroll_y=True)
        lista = MDList(padding=dp(8), spacing=dp(14))

        # Adicionando os cards
        lista.add_widget(self._card_api_key())
        lista.add_widget(self._card_voz())
        lista.add_widget(self._card_bolha())

        # Item "Sobre o Spica"
        item_sobre = TwoLineIconListItem(
            text="Sobre o Spica", 
            secondary_text="VTuber-IA • Python + KivyMD + Groq"
        )
        icone_sobre = IconLeftWidget(icon="information-outline")
        item_sobre.add_widget(icone_sobre)
        lista.add_widget(item_sobre)

        scroll.add_widget(lista)
        raiz.add_widget(scroll)
        self.add_widget(raiz)

    def _card_api_key(self):
        card = MDCard(
            orientation="vertical", size_hint_y=None, height=dp(110),
            padding=dp(20), spacing=dp(10), radius=[dp(12)], elevation=4,
        )
        card.add_widget(MDLabel(
            text="Groq API Key",
            font_style="H6", halign="left",
        ))
        btn = MDRaisedButton(
            text="Configurar Chave API",
            size_hint_y=None, height=dp(40),
            on_release=lambda x: self._dialogo_api_key()
        )
        card.add_widget(btn)
        return card

    def _card_voz(self):
        card = MDCard(
            orientation="vertical", size_hint_y=None, height=dp(160),
            padding=dp(20), spacing=dp(10), radius=[dp(12)], elevation=4,
        )
        card.add_widget(MDLabel(
            text="Sistema de Voz",
            font_style="H6", halign="left",
        ))
        card.add_widget(MDLabel(
            text="Use o microfone no chat para falar com a Spica.\nEla ouve e responde automaticamente.",
            font_style="Body2", theme_text_color="Secondary",
            size_hint_y=None, height=dp(48),
        ))
        btn = MDRaisedButton(
            text='Testar Microfone',
            size_hint_y=None, height=dp(36),
            on_release=lambda x: self._testar_mic(),
        )
        card.add_widget(btn)
        return card

    def _testar_mic(self):
        try:
            app = MDApp.get_running_app()
            chat = app.screen_manager.get_screen("chat")
            app.navigate_to("chat")
            Clock.schedule_once(lambda dt: chat._iniciar_mic(), 0.3)
        except Exception as e:
            print(f"[Spica] testar_mic: {e}")

    def _card_bolha(self):
        card = MDCard(
            orientation="vertical", size_hint_y=None, height=dp(180),
            padding=dp(20), spacing=dp(10), radius=[dp(12)], elevation=4,
        )
        card.add_widget(MDLabel(
            text="Bolha Flutuante",
            font_style="H6", halign="left",
        ))
        card.add_widget(MDLabel(
            text="Aparece sobre outros apps.\nToque na bolha para abrir o menu de voz.",
            font_style="Body2", theme_text_color="Secondary",
            size_hint_y=None, height=dp(40),
        ))

        btn_ativar = MDRaisedButton(
            text='Ativar Bolha',
            size_hint_y=None, height=dp(36),
            on_release=lambda x: self._ativar_bolha(),
        )
        btn_permissao = MDFlatButton(
            text="Permissão de Sobreposição",
            size_hint_y=None, height=dp(30),
            on_release=lambda x: self._pedir_permissao_overlay(),
        )
        card.add_widget(btn_ativar)
        card.add_widget(btn_permissao)
        return card

    def _ativar_bolha(self):
        try:
            from src.services.overlay import SpicaOverlay, tem_permissao_overlay, pedir_permissao_overlay
            if not tem_permissao_overlay():
                print("[Spica] Permissão de sobreposição não concedida. Abrindo tela de permissão...")
                pedir_permissao_overlay()
                return
            app = MDApp.get_running_app()
            if not (hasattr(app, "bubble") and app.bubble):
                app.bubble = SpicaOverlay()
            app.bubble.ligar_bolha()
        except Exception as e:
            print(f"[Spica] ativar_bolha: {e}")

    def _pedir_permissao_overlay(self):
        try:
            from kivy.utils import platform
            if platform != "android": return
            from jnius import autoclass
            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            Settings       = autoclass("android.provider.Settings")
            Intent         = autoclass("android.content.Intent")
            Uri            = autoclass("android.net.Uri")
            ctx = PythonActivity.mActivity
            ctx.startActivity(Intent(
                Settings.ACTION_MANAGE_OVERLAY_PERMISSION,
                Uri.parse(f"package:{ctx.getPackageName()}"),
            ))
        except Exception as e:
            print(f"[Spica] overlay permissao: {e}")

    def _item_switch(self, cfg):
        app = MDApp.get_running_app()
        atual  = app.settings.get(cfg["chave"], cfg["valor_on"])
        ligado = (atual == cfg["valor_on"]) if isinstance(cfg["valor_on"], str) else bool(atual)

        item = TwoLineIconListItem(text=cfg["titulo"], secondary_text=cfg["sub"])
        icone = IconLeftWidget(icon=cfg["icone"])

        item.add_widget(icone)

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

    def _dialogo_api_key(self):
        from kivymd.uix.dialog import MDDialog
        from kivymd.uix.textfield import MDTextField

        app = MDApp.get_running_app()

        campo = MDTextField(
            hint_text="Cole sua Groq API key aqui",
            text=app.settings.get("api_key", ""),
            mode="rectangle",
        )

        def salvar(*a):
            app.settings.set("api_key", campo.text.strip())
            dialogo.dismiss()
            self.clear_widgets()
            Clock.schedule_once(lambda dt: self._construir_layout(), 0.1)

        btn_cancelar = MDFlatButton(text="Cancelar")
        btn_salvar = MDFlatButton(text="Salvar")

        dialogo = MDDialog(
            title="Groq API Key",
            type="custom",
            content_cls=campo,
            buttons=[btn_cancelar, btn_salvar],
        )
        btn_cancelar.bind(on_release=lambda x: dialogo.dismiss())
        btn_salvar.bind(on_release=salvar)
        dialogo.open()
