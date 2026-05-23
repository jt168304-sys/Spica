from kivymd.app import MDApp
from kivy.uix.screenmanager import ScreenManager
from kivy.core.window import Window
from kivy.clock import Clock

from src.config.settings import Settings
from src.utils.logger import WindLogger
from src.utils.permissions import PermissionManager
from src.database.storage import Storage


class WindApp(MDApp):
    title = "WindIA"

    def build(self):
        self.logger = WindLogger()
        self.settings = Settings()
        self.storage = Storage()
        self._apply_theme()
        self.permission_manager = PermissionManager()
        self.permission_manager.request_all()
        self.screen_manager = ScreenManager()
        self._register_screens()
        Clock.schedule_once(self._create_bubble, 0.5)
        self.logger.info("Interface construída com sucesso!")
        return self.screen_manager

    def _apply_theme(self):
        self.theme_cls.primary_palette = "Blue"
        self.theme_cls.accent_palette = "Cyan"
        self.theme_cls.theme_style = self.settings.get("theme_mode", "Dark")
        self.logger.info(f"[Tema aplicado] {self.theme_cls.theme_style}")

    def _register_screens(self):
        from src.ui.screens.home_screen import HomeScreen
        from src.ui.screens.notes_screen import NotesScreen
        from src.ui.screens.chat_screen import ChatScreen
        from src.ui.screens.settings_screen import SettingsScreen

        for tela in [HomeScreen(name="home"), NotesScreen(name="notas"),
                     ChatScreen(name="chat"), SettingsScreen(name="configuracoes")]:
            self.screen_manager.add_widget(tela)
        self.screen_manager.current = "home"

    def _create_bubble(self, dt):
        try:
            from src.ui.bubble import FloatingBubble
            self.bubble = FloatingBubble()
        except Exception as e:
            self.logger.error(f"Erro na bolha: {e}")

    def navigate_to(self, screen_name):
        if screen_name in [s.name for s in self.screen_manager.screens]:
            self.screen_manager.current = screen_name

    def toggle_theme(self):
        novo = "Light" if self.theme_cls.theme_style == "Dark" else "Dark"
        self.theme_cls.theme_style = novo
        self.settings.set("theme_mode", novo)

    def on_pause(self):
        return True

    def on_stop(self):
        self.settings.save()
        self.storage.close()
