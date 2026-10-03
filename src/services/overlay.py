from kivy.core.window import Window
from kivy.utils import platform

def aplicar_flags_overlay():
    Window.clearcolor = (0, 0, 0, 0)

    if platform == 'android':
        try:
            from jnius import autoclass, PythonJavaClass, java_method

            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            Context = autoclass('android.content.Context')
            WindowManager = autoclass('android.view.WindowManager')
            LayoutParams = autoclass('android.view.WindowManager$LayoutParams')
            PixelFormat = autoclass('android.graphics.PixelFormat')
            Gravity = autoclass('android.view.Gravity')
            VERSION = autoclass('android.os.Build$VERSION')
            Intent = autoclass('android.content.Intent')
            Settings = autoclass('android.provider.Settings')
            Uri = autoclass('android.net.Uri')

            activity = PythonActivity.mActivity
            window = activity.getWindow()
            window.setBackgroundDrawableResource(17170445)

            # Valida permissão de sobreposição no Android (evita BadTokenException)
            if not Settings.canDrawOverlays(activity):
                intent = Intent(
                    Settings.ACTION_MANAGE_OVERLAY_PERMISSION,
                    Uri.parse(f"package:{activity.getPackageName()}")
                )
                intent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                activity.startActivity(intent)
                print("Solicitada permissão de sobreposição ao usuário.")
                return

            flags = (
                WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE |
                WindowManager.LayoutParams.FLAG_NOT_TOUCH_MODAL |
                WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN
            )
            window.addFlags(flags)

            window_manager = activity.getSystemService(Context.WINDOW_SERVICE)
            layout_flag = LayoutParams.TYPE_APPLICATION_OVERLAY if VERSION.SDK_INT >= 26 else LayoutParams.TYPE_PHONE

            params = LayoutParams(
                160, 160,
                layout_flag,
                LayoutParams.FLAG_NOT_FOCUSABLE | LayoutParams.FLAG_WATCH_OUTSIDE_TOUCH,
                PixelFormat.TRANSLUCENT
            )
            params.gravity = Gravity.TOP | Gravity.START
            params.x = 50
            params.y = 200

            class BubbleRunnable(PythonJavaClass):
                __javainterfaces__ = ['java/lang/Runnable']
                __javacontext__ = 'app'

                def __init__(self, act, wm, p):
                    super().__init__()
                    self.act = act
                    self.wm = wm
                    self.p = p

                @java_method('()V')
                def run(self):
                    try:
                        Button = autoclass('android.widget.Button')
                        Color = autoclass('android.graphics.Color')

                        btn = Button(self.act)
                        btn.setText("Spica")
                        btn.setBackgroundColor(Color.parseColor("#FF6200EE"))
                        btn.setTextColor(Color.WHITE)
                        self.wm.addView(btn, self.p)

                        # Minimização para a tela Home do Android
                        home_intent = Intent(Intent.ACTION_MAIN)
                        home_intent.addCategory(Intent.CATEGORY_HOME)
                        home_intent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                        self.act.startActivity(home_intent)

                        print("Bolha criada e app minimizado para a Home com sucesso!")
                    except Exception as ex:
                        print(f"Erro na thread da interface: {ex}")

            activity.runOnUiThread(BubbleRunnable(activity, window_manager, params))

        except Exception as e:
            print(f"Erro no overlay Android: {e}")
