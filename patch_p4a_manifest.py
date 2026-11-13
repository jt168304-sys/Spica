# patch_p4a_manifest.py — roda no GitHub Actions ANTES do buildozer, sobre o p4a clonado.
# 1) foregroundServiceType="microphone" no <service> do serviço (Android 14 precisa).
# 2) Registra o receptor SpicaLembreteReceiver (lembrete do TikTok) dentro de <application>.
import pathlib
import sys

raiz = pathlib.Path(sys.argv[1])
ATTR = 'android:foregroundServiceType="microphone"'
ALVO = 'android:process=":service_{{ name }}"'
RECEPTOR = (
    '    <receiver android:name="com.spica.spica.SpicaLembreteReceiver" android:exported="false">\n'
    '        <intent-filter>\n'
    '            <action android:name="com.spica.spica.LEMBRETE_TIKTOK"/>\n'
    '        </intent-filter>\n'
    '    </receiver>\n'
)

alterados = 0
receptor_ok = 0
for tpl in raiz.rglob("AndroidManifest.tmpl.xml"):
    txt = tpl.read_text(encoding="utf-8")
    novo = txt
    if ALVO in novo and ATTR not in novo:
        novo = novo.replace(ALVO, ALVO + "\n         " + ATTR)
    if "SpicaLembreteReceiver" not in novo and "</application>" in novo:
        novo = novo.replace("</application>", RECEPTOR + "</application>", 1)
        receptor_ok += 1
    if novo != txt:
        tpl.write_text(novo, encoding="utf-8")
        print(f"[patch] OK: {tpl}")
        alterados += 1
    else:
        print(f"[patch] sem alteracao: {tpl}")

if alterados == 0:
    print("[patch] ERRO: nenhum template foi alterado")
    sys.exit(1)
if receptor_ok == 0:
    print("[patch] AVISO: </application> não encontrado; o receptor do TikTok não foi registrado")
