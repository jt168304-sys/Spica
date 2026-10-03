from kivy.core.window import Window
from kivy.utils import platform

def aplicar_flags_overlay():
    # Define o fundo do Kivy como transparente antes de renderizar os widgets
    Window.clearcolor = (0, 0, 0, 0)
    
    if platform == 'android':
        try:
            from jnius import autoclass
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            WindowManager = autoclass('android.view.WindowManager$LayoutParams')
            
            activity = PythonActivity.mActivity
            window = activity.getWindow()
            
            # Aplica fundo transparente nativo na janela Android (android.R.color.transparent)
            window.setBackgroundDrawableResource(17170445)
            
            # Flags para permitir interagir com a tela atras, mantendo a Activity viva
            flags = (
                WindowManager.FLAG_NOT_FOCUSABLE |
                WindowManager.FLAG_NOT_TOUCH_MODAL |
                WindowManager.FLAG_LAYOUT_IN_SCREEN
            )
            window.addFlags(flags)
            print('Overlay e transparencia de primeiro plano ativados!')
        except Exception as e:
            print(f'Erro ao aplicar flags de overlay no Android: {e}')
