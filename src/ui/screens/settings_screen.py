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
from src.ui import tema as T
from src.ui.barra import criar_barra


class SettingsScreen(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._construir_layout()

    def _construir_layout(self):
        raiz = MDBoxLayout(orientation="vertical")
        T.estilizar(raiz, md_bg_color=T.FUNDO)

        raiz.add_widget(criar_barra(
            "Configurações",
            esquerda=("arrow-left", lambda: MDApp.get_running_app().navigate_to("chat")),
        ))

        scroll = ScrollView(do_scroll_x=False, do_scroll_y=True)
        lista = MDList(padding=dp(12), spacing=dp(14))

        # Adicionando os cards
        lista.add_widget(self._card_api_key())
        lista.add_widget(self._card_bolha())

        lista.add_widget(self._card_sobre())

        scroll.add_widget(lista)
        raiz.add_widget(scroll)
        self.add_widget(raiz)

    def _titulo(self, texto):
        lbl = MDLabel(text=texto, font_style="H6", halign="left")
        return T.estilizar(lbl, theme_text_color="Custom", text_color=T.CREME)

    def _descricao(self, texto, altura):
        lbl = MDLabel(text=texto, font_style="Body2", size_hint_y=None, height=altura)
        return T.estilizar(lbl, theme_text_color="Custom", text_color=T.TEXTO_2)

    def _botao_principal(self, btn):
        return T.estilizar(btn, md_bg_color=T.MENTA, theme_text_color="Custom",
                           text_color=T.FUNDO, radius=[dp(20)] * 4)

    def _card_sobre(self):
        card = MDCard(
            orientation="vertical", size_hint_y=None, height=dp(88),
            padding=dp(20), spacing=dp(4), radius=[dp(16)], elevation=0,
            md_bg_color=T.SUPERFICIE,
        )
        card.add_widget(self._titulo("Sobre o Spica"))
        card.add_widget(self._descricao("VTuber-IA • Python + KivyMD + Groq", dp(22)))
        return card

    def _card_api_key(self):
        card = MDCard(
            orientation="vertical", size_hint_y=None, height=dp(124),
            padding=dp(20), spacing=dp(10), radius=[dp(16)], elevation=0, md_bg_color=T.SUPERFICIE,
        )
        card.add_widget(self._titulo("Groq API Key"))
        btn = MDRaisedButton(
            text="Configurar Chave API",
            size_hint_y=None, height=dp(40),
            on_release=lambda x: self._dialogo_api_key()
        )
        self._botao_principal(btn)
        card.add_widget(btn)
        return card

    def _card_bolha(self):
        card = MDCard(
            orientation="vertical", size_hint_y=None, height=dp(218),
            padding=dp(20), spacing=dp(10), radius=[dp(16)], elevation=0, md_bg_color=T.SUPERFICIE,
        )
        card.add_widget(self._titulo("Bolha Flutuante"))
        card.add_widget(self._descricao(
            "Aparece sobre outros apps.\nToque na bolha para abrir o menu de voz.", dp(44)))

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
        self._botao_principal(btn_ativar)
        T.estilizar(btn_permissao, theme_text_color="Custom", text_color=T.MENTA)
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
            try:
                from android.permissions import check_permission, request_permissions, Permission
                faltando = []
                for nome in ("RECORD_AUDIO", "POST_NOTIFICATIONS"):
                    perm = getattr(Permission, nome, None)
                    if perm is not None and not check_permission(perm):
                        faltando.append(perm)
                if faltando:
                    def _apos(perms, grants):
                        if grants and all(grants):
                            Clock.schedule_once(lambda dt: self._ativar_bolha(), 0.3)
                    request_permissions(faltando, _apos)
                    return
            except Exception as e:
                print(f"[Spica] perms bolha: {e}")
            from src.utils.keepalive import (
                ignorando_otimizacao_bateria,
                pedir_ignorar_otimizacao_bateria,
                minimizar_app,
            )
            if not ignorando_otimizacao_bateria():
                print("[Spica] Pedindo isenção de otimização de bateria...")
                pedir_ignorar_otimizacao_bateria()
                return
            from src.services.fg_service import iniciar_servico
            iniciar_servico("escuta")
            app = MDApp.get_running_app()
            if not (hasattr(app, "bubble") and app.bubble):
                app.bubble = SpicaOverlay()
            app.bubble.ligar_bolha()
            # Dá tempo da bolha entrar no WindowManager e minimiza o app
            Clock.schedule_once(lambda dt: minimizar_app(), 0.8)
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
            password=True,
        )
        T.estilizar(campo, line_color_normal=T.BORDA, line_color_focus=T.MENTA,
                    text_color_normal=T.CREME, text_color_focus=T.CREME,
                    hint_text_color_normal=T.TEXTO_2, hint_text_color_focus=T.MENTA)

        def salvar(*a):
            app.settings.set("api_key", campo.text.strip())
            dialogo.dismiss()
            self.clear_widgets()
            Clock.schedule_once(lambda dt: self._construir_layout(), 0.1)

        btn_cancelar = MDFlatButton(text="Cancelar")
        btn_salvar = MDFlatButton(text="Salvar")
        T.estilizar(btn_cancelar, theme_text_color="Custom", text_color=T.TEXTO_2)
        T.estilizar(btn_salvar, theme_text_color="Custom", text_color=T.MENTA)

        dialogo = MDDialog(
            title="Groq API Key",
            type="custom",
            content_cls=campo,
            buttons=[btn_cancelar, btn_salvar],
        )
        T.estilizar(dialogo, md_bg_color=T.SUPERFICIE, radius=[dp(20)] * 4)  # MDDialog exige 4 valores
        btn_cancelar.bind(on_release=lambda x: dialogo.dismiss())
        btn_salvar.bind(on_release=salvar)
        dialogo.open()
