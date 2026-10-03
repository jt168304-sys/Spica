from kivy.app import App
from kivy.uix.label import Label
from src.services.overlay import aplicar_flags_overlay

class SpicaApp(App):
    def build(self):
        aplicar_flags_overlay()
        return Label(text="Spica - Escuta Contínua Ativa", font_size='20sp')

if __name__ == '__main__':
    SpicaApp().run()
