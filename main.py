from kivy.app import App
from kivy.uix.label import Label

class SpicaApp(App):
    def build(self):
        return Label(text="Spica - Interface Ativa", font_size='20sp')

if __name__ == '__main__':
    SpicaApp().run()
