# campo_nativo.py — campo de texto NATIVO do Android (teclado com corretor e sugestões), criado direto
# pelo Python com pyjnius, sem classe Java própria. Erros da criação (que acontece na thread de tela do
# Android) são guardados em .erro para o chat poder voltar ao campo comum.
from android.runnable import run_on_ui_thread
from jnius import PythonJavaClass, autoclass, cast, java_method


def _atividade():
    return autoclass("org.kivy.android.PythonActivity").mActivity


def _cs(texto):
    """Texto Python -> CharSequence do Java (o pyjnius não converte sozinho nesses métodos)."""
    return cast("java.lang.CharSequence", autoclass("java.lang.String")(str(texto)))


class _Ouvinte(PythonJavaClass):
    """Avisa o Python quando a pessoa toca em Enviar no teclado."""
    __javainterfaces__ = ["android/widget/TextView$OnEditorActionListener"]

    def __init__(self, fila):
        super().__init__()
        self._fila = fila

    @java_method("(Landroid/widget/TextView;ILandroid/view/KeyEvent;)Z")
    def onEditorAction(self, view, acao, evento):
        enter = evento is not None and evento.getKeyCode() == 66 and evento.getAction() == 0
        if acao in (4, 6) or enter:     # 4 = enviar, 6 = concluído
            texto = str(view.getText().toString()).strip()
            if texto:
                self._fila.append(texto)
                view.setText(_cs(""))
            return True
        return False


class CampoNativo:
    def __init__(self):
        self._campo = None
        self._quadro = None
        self._ouvinte = None
        self._enviados = []
        self.erro = ""

    def pronto(self):
        """True só quando o campo já foi criado e colocado na tela."""
        return self._campo is not None

    @run_on_ui_thread
    def _montar(self, x, y, w, h, dica):
        if self._campo is not None:
            return
        try:
            ato = _atividade()
            EditText = autoclass("android.widget.EditText")
            Color = autoclass("android.graphics.Color")
            Gradiente = autoclass("android.graphics.drawable.GradientDrawable")
            Quadro = autoclass("android.widget.FrameLayout")
            Params = autoclass("android.widget.FrameLayout$LayoutParams")   # classe interna: nome com $
            Gravidade = autoclass("android.view.Gravity")
            Tipo = autoclass("android.text.InputType")
            Editor = autoclass("android.view.inputmethod.EditorInfo")
            campo = EditText(ato)
            campo.setHint(_cs(dica))
            campo.setSingleLine(True)
            campo.setTextColor(Color.parseColor("#fef4ec"))
            campo.setHintTextColor(Color.parseColor("#a9aeb4"))
            campo.setTextSize(16.0)
            campo.setPadding(int(h // 2), 0, int(h // 2), 0)
            fundo = Gradiente()
            fundo.setCornerRadius(float(h) / 2.0)
            fundo.setColor(Color.parseColor("#1f2328"))
            fundo.setStroke(3, Color.parseColor("#a8c9bd"))
            campo.setBackground(fundo)
            campo.setInputType(Tipo.TYPE_CLASS_TEXT | Tipo.TYPE_TEXT_FLAG_AUTO_CORRECT | Tipo.TYPE_TEXT_FLAG_CAP_SENTENCES)
            campo.setImeOptions(Editor.IME_ACTION_SEND)
            self._ouvinte = _Ouvinte(self._enviados)      # guarda a referência: senão o Python o descarta
            campo.setOnEditorActionListener(self._ouvinte)
            quadro = Quadro(ato)
            quadro.addView(campo, Params(-1, -1))
            params = Params(int(w), int(h), Gravidade.TOP | Gravidade.LEFT)
            params.leftMargin = int(x)
            params.topMargin = int(y)
            ato.addContentView(quadro, params)
            self._campo = campo
            self._quadro = quadro
        except Exception as e:
            self.erro = f"{type(e).__name__}: {e}"

    @run_on_ui_thread
    def _mover(self, x, y, w, h):
        if self._quadro is None:
            return
        try:
            Params = autoclass("android.widget.FrameLayout$LayoutParams")
            Gravidade = autoclass("android.view.Gravity")
            params = Params(int(w), int(h), Gravidade.TOP | Gravidade.LEFT)
            params.leftMargin = int(x)
            params.topMargin = int(y)
            self._quadro.setLayoutParams(params)
        except Exception as e:
            self.erro = f"{type(e).__name__}: {e}"

    @run_on_ui_thread
    def _zerar(self):
        if self._campo is not None:
            self._campo.setText(_cs(""))

    def iniciar(self, x, y, w, h, dica="Mensagem..."):
        self._montar(x, y, w, h, dica)

    def atualizar(self, x, y, w, h):
        self._mover(x, y, w, h)

    def pegar_enviado(self):
        return self._enviados.pop(0) if self._enviados else ""

    def pegar_texto(self):
        return str(self._campo.getText().toString()) if self._campo is not None else ""

    def limpar(self):
        self._zerar()
