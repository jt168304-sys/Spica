import os

caminho = "src/ui/screens/chat_screen.py"
if not os.path.exists(caminho):
    print("Erro: arquivo nao encontrado!")
    exit(1)

codigo_antigo = open(caminho, "r", encoding="utf-8").read()

# Procura onde as funcoes antigas comecam e onde a classe ChatScreen comeca
inicio_alvo = codigo_antigo.find("def _get_temp_dir():")
fim_alvo = codigo_antigo.find("class ChatScreen(MDScreen):")

if inicio_alvo == -1 or fim_alvo == -1:
    print("Erro: Nao foi possivel localizar as funcoes antigas no arquivo.")
    exit(1)

bloco_novo = """def _get_temp_dir():
    try:
        from android.storage import app_storage_path
        pasta = os.path.join(app_storage_path(), "imagens")
    except Exception:
        pasta = os.path.join(os.path.expanduser("~"), "imagens")
    os.makedirs(pasta, exist_ok=True)
    return pasta


def _copiar_da_uri(uri_java):
    import time
    try:
        from jnius import autoclass
        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        ctx = PythonActivity.mActivity
        pasta = _get_temp_dir()
        destino = os.path.join(pasta, f"img_{int(time.time())}.jpg")
        stream = ctx.getContentResolver().openInputStream(uri_java)
        with open(destino, "wb") as f:
            buf = bytearray(8192)
            while True:
                n = stream.read(buf)
                if n <= 0:
                    break
                f.write(buf[:n])
        stream.close()
        if os.path.exists(destino) and os.path.getsize(destino) > 0:
            return destino
    except Exception as e:
        print(f"Erro ao copiar URI: {e}")
    return None


def _abrir_camera(callback):
    import time
    from kivy.clock import Clock
    try:
        from android.permissions import request_permissions, check_permission, Permission
        from jnius import autoclass
        from android.activity import bind as ab, unbind as aub

        if not check_permission(Permission.CAMERA):
            def _apos(perms, results):
                if results and results[0]:
                    Clock.schedule_once(lambda dt: _abrir_camera(callback), 0.5)
                else:
                    Clock.schedule_once(lambda dt: callback(None), 0)
            request_permissions([Permission.CAMERA], _apos)
            return

        Intent = autoclass("android.content.Intent")
        MediaStore = autoclass("android.provider.MediaStore")
        ContentValues = autoclass("android.content.ContentValues")
        PythonActivity = autoclass("org.kivy.android.PythonActivity")

        ctx = PythonActivity.mActivity
        resolver = ctx.getContentResolver()

        values = ContentValues()
        values.put(MediaStore.Images.Media.DISPLAY_NAME, f"spica_foto_{int(time.time())}.jpg")
        values.put(MediaStore.Images.Media.MIME_TYPE, "image/jpeg")
        image_uri = resolver.insert(MediaStore.Images.Media.EXTERNAL_CONTENT_URI, values)

        intent = Intent(MediaStore.ACTION_IMAGE_CAPTURE)
        intent.putExtra(MediaStore.EXTRA_OUTPUT, image_uri)

        def on_result(req, res, data):
            aub(on_activity_result=on_result)
            if res == -1:
                caminho_local = _copiar_da_uri(image_uri)
                Clock.schedule_once(lambda dt: callback(caminho_local), 0.3)
            else:
                try:
                    resolver.delete(image_uri, None, None)
                except Exception:
                    pass
                Clock.schedule_once(lambda dt: callback(None), 0)

        ab(on_activity_result=on_result)
        ctx.startActivityForResult(intent, 102)
    except Exception:
        Clock.schedule_once(lambda dt: callback(None), 0)


def _abrir_seletor(callback):
    from kivy.clock import Clock
    try:
        from jnius import autoclass
        from android.activity import bind as ab, unbind as aub
        Intent = autoclass("android.content.Intent")
        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        ctx = PythonActivity.mActivity

        intent = Intent(Intent.ACTION_GET_CONTENT)
        intent.setType("image/*")

        def on_result(req, res, data):
            aub(on_activity_result=on_result)
            if res == -1 and data is not None:
                uri = data.getData()
                if uri:
                    caminho = _copiar_da_uri(uri)
                    Clock.schedule_once(lambda dt: callback(caminho), 0.2)
                    return
            Clock.schedule_once(lambda dt: callback(None), 0.2)

        ab(on_activity_result=on_result)
        ctx.startActivityForResult(intent, 103)
    except Exception:
        Clock.schedule_once(lambda dt: callback(None), 0)


"""

# Junta as partes remontando o arquivo com o bloco atualizado
codigo_final = codigo_antigo[:inicio_alvo] + bloco_novo + codigo_antigo[fim_alvo:]
open(caminho, "w", encoding="utf-8").write(codigo_final)
print("Sucesso! Arquivo modificado localmente.")
