# campo_nativo.py — campo de texto NATIVO do Android (teclado com corretor e sugestões), criado direto
# pelo Python com pyjnius. SEM callback do Android para o Python (isso derrubava o app): todo acesso ao campo
# acontece dentro da thread de tela do Android, e o Python só lê variáveis comuns.
# Enter envia: o campo aceita linha nova e o texto que termina em Enter vai para a fila de envio.
from android.runnable import run_on_ui_thread
from jnius import autoclass, cast


def _atividade():
    return autoclass("org.kivy.android.PythonActivity").mActivity


def _cs(texto):
    """Texto Python -> CharSequence do Java (o pyjnius não converte sozinho nesses métodos)."""
    return cast("java.lang.CharSequence", autoclass("java.lang.String")(str(texto)))


class CampoNativo:
    def __init__(self):
        self._campo = None
        self._quadro = None
        self._enviados = []
        self._texto_atual = ""
        self._visivel = True
        self.erro = ""
        self.erro_teclado = ""
        self.teclado_px = 0

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
            campo = EditText(ato)
            campo.setHint(_cs(dica))
            campo.setTextColor(Color.parseColor("#fef4ec"))
            campo.setHintTextColor(Color.parseColor("#a9aeb4"))
            campo.setTextSize(16.0)
            campo.setGravity(16 | 3)   # CENTER_VERTICAL | LEFT
            campo.setPadding(int(h // 2), 0, int(h // 2), 0)
            fundo = Gradiente()
            fundo.setCornerRadius(float(h) / 2.0)
            fundo.setColor(Color.parseColor("#1f2328"))
            fundo.setStroke(3, Color.parseColor("#a8c9bd"))
            campo.setBackground(fundo)
            campo.setInputType(Tipo.TYPE_CLASS_TEXT | Tipo.TYPE_TEXT_FLAG_AUTO_CORRECT
                               | Tipo.TYPE_TEXT_FLAG_CAP_SENTENCES | Tipo.TYPE_TEXT_FLAG_MULTI_LINE)
            campo.setMaxLines(2)
            quadro = Quadro(ato)
            quadro.addView(campo, Params(-1, -1))
            params = Params(int(w), int(h), Gravidade.TOP | Gravidade.LEFT)
            params.leftMargin = int(x)
            params.topMargin = int(y)
            ato.addContentView(quadro, params)
            quadro.setVisibility(0 if self._visivel else 8)
            self._campo = campo
            self._quadro = quadro
            try:
                ato.getWindow().setSoftInputMode(48)    # SOFT_INPUT_ADJUST_NOTHING: não empurra a tela
            except Exception as e_modo:
                self.erro_teclado = f"modo do teclado: {type(e_modo).__name__}: {e_modo}"
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
    def _sondar(self):
        """Roda na thread de tela: lê o texto, detecta o Enter e guarda tudo em variáveis comuns."""
        if self._campo is None:
            return
        try:
            texto = str(self._campo.getText())
            if texto.endswith("\n") and texto.strip():
                self._enviados.append(texto.strip())
                self._campo.setText(_cs(""))
                self._texto_atual = ""
            else:
                self._texto_atual = texto
            self._medir_teclado()
        except Exception as e:
            self.erro = f"{type(e).__name__}: {e}"

    def _medir_teclado(self):
        """Altura do teclado acima da barra de navegação (px). Roda na thread de tela."""
        try:
            decor = _atividade().getWindow().getDecorView()
            insets = decor.getRootWindowInsets()
            if insets is None:
                return
            Tipo = autoclass("android.view.WindowInsets$Type")
            ime = int(insets.getInsets(Tipo.ime()).bottom)
            nav = int(insets.getInsets(Tipo.navigationBars()).bottom)
            self.teclado_px = max(0, ime - nav) if ime > 0 else 0
        except Exception as e:
            self.erro_teclado = f"{type(e).__name__}: {e}"
            self.teclado_px = 0

    @run_on_ui_thread
    def _zerar(self):
        if self._campo is not None:
            self._campo.setText(_cs(""))

    @run_on_ui_thread
    def _aplicar_visibilidade(self, visivel):
        if self._quadro is not None:
            self._quadro.setVisibility(0 if visivel else 8)     # 0 = VISIBLE, 8 = GONE

    def iniciar(self, x, y, w, h, dica="Mensagem..."):
        self._montar(x, y, w, h, dica)

    def atualizar(self, x, y, w, h):
        self._mover(x, y, w, h)

    def sondar(self):
        if self._campo is not None:
            self._sondar()

    def visivel(self, mostrar):
        if mostrar != self._visivel:
            self._visivel = mostrar
            self._aplicar_visibilidade(mostrar)

    def pegar_enviado(self):
        return self._enviados.pop(0) if self._enviados else ""

    def pegar_texto(self):
        """Lê o texto direto do campo (sem cache): o envio pelo botão nunca pega um valor atrasado."""
        if self._campo is None:
            return self._texto_atual
        try:
            return str(self._campo.getText())
        except Exception:
            return self._texto_atual

    def limpar(self):
        self._texto_atual = ""
        self._zerar()
