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

        scroll = ScrollView(do_scroll_x=False, do_scroll_y=True, bar_width=dp(4),
                            scroll_type=["bars", "content"], effect_cls="ScrollEffect")
        # BoxLayout com altura igual à soma dos cards (o MDList não se estica e travava a rolagem)
        lista = MDBoxLayout(orientation="vertical", size_hint_y=None, padding=dp(12), spacing=dp(14))
        lista.bind(minimum_height=lista.setter("height"))

        # Adicionando os cards
        lista.add_widget(self._card_api_key())
        lista.add_widget(self._card_cloudflare())
        lista.add_widget(self._card_memoria())
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

    def _card_cloudflare(self):
        app = MDApp.get_running_app()
        pronto = bool(app.settings.get("cf_account", "") and app.settings.get("cf_token", ""))
        card = MDCard(
            orientation="vertical", size_hint_y=None, height=dp(225),
            padding=dp(20), spacing=dp(10), radius=[dp(16)], elevation=0, md_bg_color=T.SUPERFICIE,
        )
        card.add_widget(self._titulo("Imagens (Cloudflare)"))
        card.add_widget(self._descricao(
            "Cria imagens com FLUX (cota diária grátis). " + ("Configurado." if pronto else "Falta configurar."), dp(44)))
        btn = MDRaisedButton(text="Configurar Cloudflare", size_hint_y=None, height=dp(40),
                             on_release=lambda x: self._dialogo_cloudflare())
        self._botao_principal(btn)
        card.add_widget(btn)
        btn_teste = MDFlatButton(text="Testar conexão", on_release=lambda x: self._testar_cloudflare())
        T.estilizar(btn_teste, theme_text_color="Custom", text_color=T.MENTA)
        card.add_widget(btn_teste)
        return card

    def _testar_cloudflare(self):
        """Gera uma imagem pequena de teste e mostra o resultado (ou o motivo da falha)."""
        import threading
        try:
            from kivymd.toast import toast
        except Exception:
            toast = print
        toast("Testando o Cloudflare (alguns segundos)...")

        def trabalho():
            try:
                from src.services.ferramentas import _imagem_cloudflare
                dados, erro = _imagem_cloudflare("a small red apple on a white table, simple illustration")
                msg = "Cloudflare OK: imagem de teste criada." if dados else str(erro)
            except Exception as e:
                msg = f"Erro no teste: {type(e).__name__}: {e}"
            Clock.schedule_once(lambda dt: toast(msg), 0)

        threading.Thread(target=trabalho, daemon=True).start()

    def _dialogo_cloudflare(self):
        from kivymd.uix.dialog import MDDialog
        from kivymd.uix.textfield import MDTextField

        app = MDApp.get_running_app()
        caixa = MDBoxLayout(orientation="vertical", spacing=dp(12), size_hint_y=None, height=dp(150))
        campo_conta = MDTextField(hint_text="Account ID (32 caracteres)",
                                  text=app.settings.get("cf_account", ""), mode="rectangle")
        campo_token = MDTextField(hint_text="API Token (Workers AI)",
                                  text=app.settings.get("cf_token", ""), mode="rectangle", password=True)
        for campo in (campo_conta, campo_token):
            T.estilizar(campo, line_color_normal=T.BORDA, line_color_focus=T.MENTA,
                        text_color_normal=T.CREME, text_color_focus=T.CREME,
                        hint_text_color_normal=T.TEXTO_2, hint_text_color_focus=T.MENTA)
            caixa.add_widget(campo)

        def salvar(*a):
            app.settings.set("cf_account", campo_conta.text.strip())
            app.settings.set("cf_token", campo_token.text.strip())
            dialogo.dismiss()
            self.clear_widgets()
            Clock.schedule_once(lambda dt: self._construir_layout(), 0.1)

        btn_cancelar = MDFlatButton(text="Cancelar")
        btn_salvar = MDFlatButton(text="Salvar")
        T.estilizar(btn_cancelar, theme_text_color="Custom", text_color=T.TEXTO_2)
        T.estilizar(btn_salvar, theme_text_color="Custom", text_color=T.MENTA)
        dialogo = MDDialog(title="Cloudflare (imagens)", type="custom", content_cls=caixa,
                           buttons=[btn_cancelar, btn_salvar])
        T.estilizar(dialogo, md_bg_color=T.SUPERFICIE, radius=[dp(20)] * 4)
        btn_cancelar.bind(on_release=lambda x: dialogo.dismiss())
        btn_salvar.bind(on_release=salvar)
        dialogo.open()

    def _card_memoria(self):
        try:
            from src.services import memoria
            n = len(memoria.listar_fatos(500))
        except Exception:
            memoria, n = None, 0
        card = MDCard(
            orientation="vertical", size_hint_y=None, height=dp(262),
            padding=dp(20), spacing=dp(6), radius=[dp(16)], elevation=0, md_bg_color=T.SUPERFICIE,
        )
        card.add_widget(self._titulo("Memória"))
        card.add_widget(self._descricao(
            f"{n} coisa{'s' if n != 1 else ''} guardada{'s' if n != 1 else ''} no aparelho. "
            "Diga: lembra que..., esquece..., ou: o que você sabe sobre mim?", dp(66)))
        btn = MDRaisedButton(text="Ver memória", on_release=lambda x: self._ver_memoria())
        self._botao_principal(btn)
        card.add_widget(btn)
        b2 = MDFlatButton(text="Exportar cópia (JSON)", on_release=lambda x: self._exportar_memoria())
        b3 = MDFlatButton(text="Apagar tudo", on_release=lambda x: self._confirmar_apagar_memoria())
        T.estilizar(b2, theme_text_color="Custom", text_color=T.MENTA)
        T.estilizar(b3, theme_text_color="Custom", text_color=T.ALERTA)
        card.add_widget(b2)
        card.add_widget(b3)
        return card

    def _toast(self, msg):
        try:
            from kivymd.toast import toast
            toast(msg)
        except Exception:
            print(msg)

    def _ver_memoria(self):
        from kivymd.uix.dialog import MDDialog
        try:
            from src.services import memoria
            fatos = memoria.listar_fatos(25)
        except Exception:
            fatos = []
        texto = "\n".join("• " + f for f in fatos) or "Ainda não guardei nada sobre você."
        dialogo = MDDialog(title="O que eu sei sobre você", text=texto,
                           buttons=[MDFlatButton(text="Fechar")])
        T.estilizar(dialogo, md_bg_color=T.SUPERFICIE, radius=[dp(20)] * 4)
        dialogo.buttons[0].bind(on_release=lambda x: dialogo.dismiss())
        dialogo.open()

    def _exportar_memoria(self):
        try:
            from src.services import memoria
            onde, n = memoria.exportar()
            self._toast(f"{n} itens salvos em {onde}")
        except Exception as e:
            self._toast(f"Não consegui exportar: {e}")

    def _confirmar_apagar_memoria(self):
        from kivymd.uix.dialog import MDDialog
        cancelar = MDFlatButton(text="Cancelar")
        apagar = MDFlatButton(text="Apagar")
        T.estilizar(apagar, theme_text_color="Custom", text_color=T.ALERTA)
        dialogo = MDDialog(title="Apagar a memória?", text="Isso apaga tudo que a Spica guardou sobre você.",
                           buttons=[cancelar, apagar])
        T.estilizar(dialogo, md_bg_color=T.SUPERFICIE, radius=[dp(20)] * 4)

        def confirmar(*a):
            try:
                from src.services import memoria
                memoria.apagar_tudo()
            except Exception as e:
                print(e)
            dialogo.dismiss()
            self.clear_widgets()
            Clock.schedule_once(lambda dt: self._construir_layout(), 0.1)
        cancelar.bind(on_release=lambda x: dialogo.dismiss())
        apagar.bind(on_release=confirmar)
        dialogo.open()

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
