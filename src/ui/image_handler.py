# image_handler.py — Seletor de imagens robusto para Android (v16 Estável)
"""
Módulo para seleção e cópia segura de imagens no Android.
Trata múltiplos tipos de erro e fornece fallback inteligente.
"""

import os
import time
from kivy.clock import Clock


def abrir_seletor_seguro(callback):
    """
    Abre seletor de imagens com tratamento robusto de erros.
    """
    try:
        from jnius import autoclass
        from android.activity import bind as ab, unbind as ub
        
        Intent = autoclass("android.content.Intent")
        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        
        activity = PythonActivity.mActivity
        intent = Intent(Intent.ACTION_OPEN_DOCUMENT)
        intent.setType("image/*")
        intent.addCategory(Intent.CATEGORY_OPENABLE)
        
        context = {'callback': callback, 'unbind_func': None}
        
        def on_activity_result(request_code, result_code, data):
            """Callback chamado quando usuário retorna do seletor."""
            # CORREÇÃO: Garante que só vai processar e desvincular se for o NOSSO seletor (103)
            if request_code != 103:
                return
                
            if context['unbind_func']:
                try:
                    context['unbind_func'](on_activity_result=on_activity_result)
                except:
                    pass
            
            # -1 = RESULT_OK
            if result_code == -1 and data:
                try:
                    uri = data.getData()
                    if uri:
                        uri_str = uri.toString()
                        try:
                            activity.getContentResolver().takePersistableUriPermission(
                                uri, Intent.FLAG_GRANT_READ_URI_PERMISSION
                            )
                        except:
                            pass
                        
                        # Copiar imagem com delay estável para a UI Thread
                        Clock.schedule_once(
                            lambda dt: _copiar_imagem_robusta(
                                uri_str, context['callback']
                            ),
                            0.15
                        )
                    else:
                        callback(None)
                except Exception as e:
                    print(f"[Spica/Image] Erro ao processar URI: {e}")
                    callback(None)
            else:
                callback(None)
        
        # Vincular callback de resultado
        ab(on_activity_result=on_activity_result)
        context['unbind_func'] = ub
        
        # Iniciar seletor nativo
        activity.startActivityForResult(intent, 103)
        print("[Spica/Image] Seletor de imagens aberto com ID 103")
        
    except Exception as e:
        print(f"[Spica/Image] Erro ao abrir seletor: {e}")
        Clock.schedule_once(lambda dt: callback(None), 0)


def _copiar_imagem_robusta(uri_str, callback):
    """
    Copia imagem usando transferência nativa de Streams (NIO) e compactação de emergência.
    """
    try:
        from jnius import autoclass
        
        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        Uri = autoclass("android.net.Uri")
        
        activity = PythonActivity.mActivity
        resolver = activity.getContentResolver()
        
        try:
            uri = Uri.parse(uri_str)
        except Exception as e:
            print(f"[Spica/Image] URI inválida: {e}")
            callback(None)
            return
        
        # Determinar pasta de destino estável
        pasta = pasta_imagens()
        destino = os.path.join(pasta, f"img_{int(time.time())}.jpg")
        
        # ESTRATÉGIA 1: Java NIO Channels (Alta performance, evita pontes de arrays no Python)
        print(f"[Spica/Image] Tentando cópia de canal nativo via Java NIO...")
        try:
            Files = autoclass("java.nio.file.Files")
            Paths = autoclass("java.nio.file.Paths")
            StandardCopyOption = autoclass("java.nio.file.StandardCopyOption")
            
            input_stream = resolver.openInputStream(uri)
            if input_stream:
                target_path = Paths.get(destino)
                # Passa a opção de substituir o arquivo caso ele já exista
                options = [StandardCopyOption.REPLACE_EXISTING]
                
                # O próprio Android gerencia o tráfego de bytes em baixo nível
                Files.copy(input_stream, target_path, options)
                input_stream.close()
                
                if os.path.exists(destino) and os.path.getsize(destino) > 0:
                    print(f"[Spica/Image] ✅ Sucesso total via NIO: {os.path.getsize(destino)} bytes")
                    callback(destino)
                    return
        except Exception as e_nio:
            print(f"[Spica/Image] Falha no método NIO: {e_nio}")
            try: os.remove(destino)
            except: pass

        # ESTRATÉGIA 2: Fallback via Decodificação de Hardware (Bitmap Compression)
        print(f"[Spica/Image] Iniciando fallback de compressão via BitmapFactory...")
        try:
            BF = autoclass("android.graphics.BitmapFactory")
            CF = autoclass("android.graphics.Bitmap$CompressFormat")
            FO = autoclass("java.io.FileOutputStream")
            
            s = resolver.openInputStream(uri)
            bm = BF.decodeStream(s)
            s.close()
            
            if bm:
                fos = FO(destino)
                # Renderiza direto em JPEG comprimido para poupar tráfego na API da Groq
                bm.compress(CF.JPEG, 85, fos)
                fos.flush()
                fos.close()
                bm.recycle()
                
                if os.path.exists(destino) and os.path.getsize(destino) > 0:
                    print(f"[Spica/Image] ✅ Sucesso via compressão nativa: {os.path.getsize(destino)} bytes")
                    callback(destino)
                    return
        except Exception as e_bmp:
            print(f"[Spica/Image] Fallback de hardware também falhou: {e_bmp}")
            try: os.remove(destino)
            except: pass

        print("[Spica/Image] ❌ Nenhuma estratégia de extração de mídia funcionou.")
        callback(None)
        
    except Exception as e:
        print(f"[Spica/Image] Erro geral no manipulador de imagem: {e}")
        callback(None)


def pasta_imagens():
    """Retorna caminho seguro da pasta de imagens."""
    try:
        from android.storage import app_storage_path
        p = os.path.join(app_storage_path(), "imagens")
    except:
        p = os.path.join(os.path.expanduser("~"), "imagens")
    
    os.makedirs(p, exist_ok=True)
    return p
