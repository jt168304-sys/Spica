import time

_uri_cache = None

def _obter_contexto():
    try:
        from jnius import autoclass
        PythonActivity = autoclass('org.kivy.android.PythonActivity')
        if PythonActivity.mActivity is not None:
            return PythonActivity.mActivity
    except Exception:
        pass
    try:
        from jnius import autoclass
        PythonService = autoclass('org.kivy.android.PythonService')
        if PythonService.mService is not None:
            return PythonService.mService
    except Exception:
        pass
    return None

def _obter_uri():
    global _uri_cache
    if _uri_cache is not None:
        return _uri_cache
    from jnius import autoclass
    ContentValues = autoclass('android.content.ContentValues')
    MediaStoreDownloads = autoclass('android.provider.MediaStore$Downloads')
    ctx = _obter_contexto()
    if ctx is None:
        raise RuntimeError("Nenhum contexto Android disponivel")
    resolver = ctx.getContentResolver()

    values = ContentValues()
    values.put('_display_name', 'spica_service_log.txt')
    values.put('mime_type', 'text/plain')

    uri = resolver.insert(MediaStoreDownloads.EXTERNAL_CONTENT_URI, values)
    _uri_cache = uri
    return uri

def _gravar_via_mediastore(linha):
    from jnius import autoclass
    ctx = _obter_contexto()
    if ctx is None:
        raise RuntimeError("Nenhum contexto Android disponivel")
    resolver = ctx.getContentResolver()
    uri = _obter_uri()
    stream = resolver.openOutputStream(uri, "wa")
    dados = (linha + "\n").encode("utf-8")
    stream.write(dados)
    stream.flush()
    stream.close()

def _gravar_fallback_antigo(linha):
    import os
    from jnius import autoclass
    ctx = _obter_contexto()
    if ctx is None:
        raise RuntimeError("Nenhum contexto Android disponivel")
    ext_dir = ctx.getExternalFilesDir(None).getAbsolutePath()
    os.makedirs(ext_dir, exist_ok=True)
    caminho = os.path.join(ext_dir, "spica_service_log.txt")
    with open(caminho, "a", encoding="utf-8") as f:
        f.write(linha + "\n")

def slog(msg):
    linha = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(f"[Spica/SLOG] {linha}")
    try:
        _gravar_via_mediastore(linha)
    except Exception as e1:
        try:
            _gravar_fallback_antigo(linha)
        except Exception as e2:
            print(f"[Spica/SLOG] Falha ao gravar log (mediastore: {e1} | fallback: {e2})")
