# menu_texto.py — Menu de recortar/copiar/colar dos campos de texto, em português.
# O balão do Kivy vem em inglês e mostra "Select All" mesmo com o campo vazio. Aqui traduzimos
# os botões e escondemos "Selecionar tudo" quando não há texto. Tudo protegido: se algo mudar
# numa versão do Kivy, o menu volta ao normal em vez de quebrar o app.
from kivy.metrics import dp

try:
    from kivy.uix import textinput as _ti

    _Bolha = _ti.TextInputCutCopyPaste
    _original_on_parent = _Bolha.on_parent

    def _on_parent_pt(self, instance, value):
        try:
            if value:
                self.but_cut.text = "Recortar"
                self.but_copy.text = "Copiar"
                self.but_paste.text = "Colar"
                self.but_selectall.text = "Selecionar tudo"
        except Exception:
            pass
        resultado = _original_on_parent(self, instance, value)
        try:
            if value:
                campo = self.textinput
                if self.but_selectall.parent is not None and not (campo.text or "").strip():
                    self.but_selectall.parent.remove_widget(self.but_selectall)   # nada para selecionar
                n = max(len(self.content.children), 1)
                self.width = dp(112) * n
                self.height = dp(44)
        except Exception:
            pass
        return resultado

    _Bolha.on_parent = _on_parent_pt
except Exception as _e:
    print(f"[Spica] menu_texto: não foi possível traduzir o menu ({_e})")
