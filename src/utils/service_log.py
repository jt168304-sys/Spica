# service_log.py — Log em arquivo que funciona em QUALQUER processo (Activity
# ou service.py), gravando na pasta pública Download.
#
# Por que Download e não Android/data/.../files: a partir do Android 11, a
# pasta Android/data/<pacote>/ fica bloqueada até pra gerenciadores de
# arquivo comuns navegarem (só ADB/root/o próprio app conseguem entrar).
# A pasta Download é pública e acessível por qualquer app de arquivos sem
# permissão especial — por isso usamos a API MediaStore (necessária desde o
# Android 10 pra escrever em pastas públicas de forma correta) pra gravar lá.
import time

_uri_cache = None


def _obter_uri():
    """Cria (uma vez por execução do processo) o registro do arquivo de log
    na coleção pública de Downloads, e reaproveita a mesma Uri depois."""
    global _uri_cache
    if _uri_cache is not None:
        return _uri_cache
    from jnius import autoclass
    ContentValues = autoclass('android.content.ContentValues')
    MediaStoreDownloads = autoclass('android.provider.MediaStore$Downloads')
    PythonActivity = autoclass('org.kivy.android.PythonActivity')
    ctx = PythonActivity.mActivity
    resolver = ctx.getContentResolver()

    values = ContentValues()
    values.put('_display_name', 'spica_service_log.txt')
    values.put('mime_type', 'text/plain')

    uri = resolver.insert(MediaStoreDownloads.EXTERNAL_CONTENT_URI, values)
    _uri_cache = uri
    return uri


def _gravar_via_mediastore(linha):
    from jnius import autoclass
    PythonActivity = autoclass('org.kivy.android.PythonActivity')
    ctx = PythonActivity.mActivity
    resolver = ctx.getContentResolver()
    uri = _obter_uri()
    # "wa" = write + append, pra não sobrescrever o que já foi gravado antes
    stream = resolver.openOutputStream(uri, "wa")
    dados = (linha + "\n").encode("utf-8")
    stream.write(dados)
    stream.flush()
    stream.close()


def _gravar_fallback_antigo(linha):
    """Fallback pra Android <10 (onde MediaStore.Downloads não existe) —
    grava em Android/data/.../files, mesmo sendo mais difícil de acessar."""
    import os
    from jnius import autoclass
    PythonActivity = autoclass("org.kivy.android.PythonActivity")
    ext_dir = PythonActivity.mActivity.getExternalFilesDir(None).getAbsolutePath()
    os.makedirs(ext_dir, exist_ok=True)
    caminho = os.path.join(ext_dir, "spica_service_log.txt")
    with open(caminho, "a", encoding="utf-8") as f:
        f.write(linha + "\n")


def slog(msg):
    """Grava uma linha de log com timestamp — funciona tanto no processo da
    Activity quanto no processo do service.py. Nunca lança exceção pra fora."""
    linha = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(f"[Spica/SLOG] {linha}")
    try:
        _gravar_via_mediastore(linha)
    except Exception as e1:
        try:
            _gravar_fallback_antigo(linha)
        except Exception as e2:
            print(f"[Spica/SLOG] Falha ao gravar log (mediastore: {e1} | fallback: {e2})")
