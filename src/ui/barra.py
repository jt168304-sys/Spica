# barra.py — Barra superior da Spica (logo + título + ícones), feita com widgets simples
import os
from kivy.metrics import dp
from kivy.uix.image import Image
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.button import MDIconButton
from src.ui import tema as T


def _caminho_logo():
    raiz = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(raiz, "assets", "logo.png")


def _botao(icone, callback, cor):
    btn = MDIconButton(icon=icone, pos_hint={"center_y": 0.5},
                       on_release=lambda x: callback())
    return T.icone(btn, cor)


def criar_barra(titulo, esquerda=None, direita=(), logo=False):
    """esquerda: (icone, callback) ou None | direita: [(icone, callback), ...]"""
    barra = MDBoxLayout(
        orientation="horizontal", size_hint_y=None, height=dp(56),
        padding=[dp(8), 0, dp(4), 0], spacing=dp(6),
    )
    T.estilizar(barra, md_bg_color=T.SUPERFICIE)

    if esquerda:
        barra.add_widget(_botao(esquerda[0], esquerda[1], T.CREME))

    if logo:
        try:
            barra.add_widget(Image(
                source=_caminho_logo(), size_hint=(None, None),
                size=(dp(32), dp(32)), pos_hint={"center_y": 0.5},
            ))
        except Exception as e:
            print(f"[Spica] logo da barra: {e}")

    lbl = MDLabel(text=titulo, font_style="H6", halign="left", valign="middle")
    T.estilizar(lbl, theme_text_color="Custom", text_color=T.CREME)
    lbl.bind(size=lambda i, s: setattr(i, "text_size", s))
    barra.add_widget(lbl)

    for icone, callback in direita:
        barra.add_widget(_botao(icone, callback, T.TEXTO_2))
    return barra
