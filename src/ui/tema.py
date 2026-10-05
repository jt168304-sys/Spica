# tema.py — Paleta e helpers de estilo da Spica (1.2)
# Cores tiradas do modelo da personagem (menta, pêssego, creme, ardósia).
# Para mudar o visual do app inteiro, edite SÓ este arquivo.
from kivy.utils import get_color_from_hex


def _c(hexa, alfa=1):
    r, g, b, _ = get_color_from_hex(hexa)
    return [r, g, b, alfa]


FUNDO = _c("#1f2328")        # fundo das telas
SUPERFICIE = _c("#2a2f35")   # barras e cards
BORDA = _c("#3a4148")        # divisores e contornos
BALAO_IA = _c("#343a40")     # balão da Spica
MENTA = _c("#a8c9bd")        # cor principal (balão do usuário, botões)
PESSEGO = _c("#fabc8c")      # destaque (enviar, microfone ativo)
CREME = _c("#fef4ec")        # texto principal
TEXTO_2 = _c("#a9aeb4")      # texto secundário e ícones neutros
ALERTA = _c("#e59081")       # erro/alerta


def estilizar(widget, **props):
    """Aplica propriedades de estilo SEM derrubar o app se alguma não existir
    nesta versão do KivyMD (só avisa no log)."""
    for nome, valor in props.items():
        try:
            setattr(widget, nome, valor)
        except Exception as e:
            print(f"[Spica/Tema] {type(widget).__name__}.{nome}: {e}")
    return widget


def icone(widget, cor=None):
    """Deixa um MDIconButton com cor personalizada (padrão: texto secundário)."""
    return estilizar(widget, theme_icon_color="Custom", icon_color=cor or TEXTO_2)
