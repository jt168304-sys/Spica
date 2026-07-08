# app_manager.py — Gerenciador principal do Spica (KivyMD 2.0 Estável)
from kivymd.app import MDApp
from kivy.uix.screenmanager import ScreenManager
from kivy.core.window import Window
from kivy.clock import Clock
from src.config.settings import Settings
from src.utils.logger import WindLogger
from src.utils.permissions import PermissionManager
from src.database.storage import Storage

class WindApp(MDApp):
    title = "Spica"

    def build(self):
        self.logger = WindLogger()
        self.settings = Settings()
        self.storage = Storage()
        self.bubble = None
        
        # O tema precisa ser aplicado antes de instanciar as telas no MD3
        self._apply_theme()
        
        # Instancia o gerenciador de permissões
        self.permission_manager = PermissionManager()
        
        # Agenda a solicitação de permissões de forma segura em background
        Clock.schedule_once(self._pedir_permissoes_com_atraso, 0.5)
        
        self.screen_manager = ScreenManager()
        self._register_screens()
        return self.screen_manager

    def _pedir_permissoes_com_atraso(self, dt):
        try:
            self.logger.info("Solicitando permissões em background seguro...")
            self.permission_manager.request_all()
        except Exception as e:
            self.logger.error(f"Erro ao pedir permissões: {e}")

    def _apply_theme(self):
        # Correção KivyMD 2.0 / Material 3: Paletas de cores e temas agora usam strings específicas
        self.theme_cls.primary_palette = "Purple"
        
        # Obtém o modo salvo. KivyMD exige "Light" ou "Dark" (capitalizado), não minúsculo.
        modo_salvo = self.settings.get("theme_mode", "Dark").strip().capitalize()
        if modo_salvo not in ["Dark", "Light"]:
            modo_salvo = "Dark"

        self.theme_cls.theme_style = modo_salvo

    def _register_screens(self):
        from src.ui.screens.chat_screen import ChatScreen
        from src.ui.screens.settings_screen import SettingsScreen
        
        # Instancia e adiciona as telas controladamente
        for tela in [
            ChatScreen(name="chat"),
            SettingsScreen(name="configuracoes"),
        ]:
            self.screen_manager.add_widget(tela)
        self.screen_manager.current = "chat"

    def navigate_to(self, screen_name):
        telas = [s.name for s in self.screen_manager.screens]
        if screen_name in telas:
            self.screen_manager.current = screen_name

    def toggle_theme(self):
        # KivyMD exige "Light"/"Dark" capitalizado, não minúsculo.
        novo = "Light" if self.theme_cls.theme_style == "Dark" else "Dark"
        self.theme_cls.theme_style = novo
        self.settings.set("theme_mode", novo)
        self.settings.save()

    def on_pause(self):
        return True

    def on_resume(self):
        if self.bubble and hasattr(self.bubble, 'on_resume'):
            self.bubble.on_resume()

    def on_stop(self):
        """Encerramento seguro com limpeza de recursos."""
        try:
            self.logger.info("Iniciando shutdown seguro...")
            
            # 1. Parar TTS e liberar recursos
            try:
                from src.services.tts_service import TtsService
                tts = TtsService.get_instance()
                if tts and hasattr(tts, 'destruir'):
                    tts.destruir()
                    self.logger.info("TtsService destruído")
            except Exception as e:
                self.logger.error(f"Erro ao destruir TTS: {e}")
            
            # 2. Parar Voice Service e liberar hardware nativo
            try:
                from src.services.voice_service import VoiceService
                voice = VoiceService.get_instance()
                if voice and hasattr(voice, 'destruir'):
                    voice.destruir()
                    self.logger.info("VoiceService destruído")
            except Exception as e:
                self.logger.error(f"Erro ao destruir Voice: {e}")
            
            # 3. Fechar overlay/bolha flutuante
            try:
                if self.bubble and hasattr(self.bubble, 'desligar_bolha'):
                    self.bubble.desligar_bolha()
                    self.logger.info("Overlay desligado")
            except Exception as e:
                self.logger.error(f"Erro ao desligar overlay: {e}")
            
            # 4. Salvar configurações
            self.settings.save()
            self.logger.info("Configurações salvas")
            
            # 5. Fechar conexão de banco de dados
            if hasattr(self.storage, 'close'):
                self.storage.close()
                self.logger.info("Storage fechado")
            
            self.logger.info("👋 Spica encerrada corretamente")
            
        except Exception as e:
            self.logger.error(f"[CRÍTICO] Erro ao encerrar ciclo de vida: {e}")
