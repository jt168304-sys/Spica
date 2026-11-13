# campo_nativo.py — ponte para o campo de texto nativo do Android (corretor de verdade).
# Se algo falhar, o chat volta a usar o campo do Kivy automaticamente.
def _actividade():
    from jnius import autoclass
    return autoclass("org.kivy.android.PythonActivity").mActivity


class CampoNativo:
    def __init__(self):
        from jnius import autoclass
        self._classe = autoclass("com.spica.spica.SpicaCampoTexto")

    def iniciar(self, x, y, w, h, dica="Mensagem..."):
        self._classe.mostrar(_actividade(), int(x), int(y), int(w), int(h), dica)

    def atualizar(self, x, y, w, h):
        self._classe.atualizar(_actividade(), int(x), int(y), int(w), int(h))

    def pegar_enviado(self):
        t = self._classe.pegarEnviado()
        return str(t) if t else ""

    def pegar_texto(self):
        return str(self._classe.pegarTexto() or "")

    def limpar(self):
        self._classe.limpar(_actividade())
