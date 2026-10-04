# patch_p4a_manifest.py — roda no GitHub Actions ANTES do buildozer.
# O p4a 2024.01.21 gera o <service> sem android:foregroundServiceType, e no
# Android 14 isso faz o mic gravar silêncio em segundo plano. Aqui inserimos
# foregroundServiceType="microphone" nos templates de manifest do p4a.
import sys, pathlib

raiz = pathlib.Path(sys.argv[1])
ATTR = 'android:foregroundServiceType="microphone"'
ALVO = 'android:process=":service_{{ name }}"'

alterados = 0
for tpl in raiz.rglob("AndroidManifest.tmpl.xml"):
    txt = tpl.read_text(encoding="utf-8")
    if ALVO in txt and ATTR not in txt:
        tpl.write_text(txt.replace(ALVO, ALVO + "\n         " + ATTR), encoding="utf-8")
        print(f"[patch] OK: {tpl}")
        alterados += 1
    elif ATTR in txt:
        print(f"[patch] ja tinha atributo: {tpl}")
        alterados += 1
    else:
        print(f"[patch] sem trecho alvo (ignorado): {tpl}")

if alterados == 0:
    print("[patch] ERRO: nenhum template foi alterado — o build NÃO vai ter o tipo microphone")
    sys.exit(1)
