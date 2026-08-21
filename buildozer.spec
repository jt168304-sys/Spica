[app]
title = Spica
package.name = spica
package.domain = com.spica
version = 1.0
source.dir = .
# 1. ADICIONADO: Garantindo que a extensão .kv (se houver) e os atlas entrem no APK
source.include_exts = py,png,jpg,json,kv,atlas,moc3,html,js
source.main = main.py

# 5. ADICIONADO: bloco <queries> obrigatório desde o Android 11 (package visibility) para
# o SpeechRecognizer e o TextToSpeech conseguirem enxergar/vincular os serviços do sistema.
# Sem isso, a escuta falha rapidamente em ciclos curtos no Android 11+ (funciona no 10 e antes).
android.extra_manifest_xml = extra_manifest.xml

requirements = python3==3.11.6, hostpython3==3.11.6, kivy, https://github.com/kivymd/KivyMD/archive/master.zip, https://github.com/T-Dynamos/materialyoucolor-python/archive/main.zip, asynckivy, requests, certifi, urllib3, plyer, pyjnius, materialshapes

# 6. HISTÓRICO: o crash nativo (Segmentation Fault no on_draw do Kivy) que já
# tivemos veio da combinação instável Python 3.14 + Kivy. Tentamos resolver
# com "p4a.branch = master" aqui, mas essa chave só funciona quando o p4a vem
# de um clone git controlado (p4a.source_dir) — não é o nosso caso (pip).
# A fixação de verdade agora é no workflow do GitHub Actions
# (.github/workflows/build.yml, "pip3 install python-for-android==2024.1.21").

orientation = portrait
fullscreen = 0

icon.filename = %(source.dir)s/Spica.png

# 2. ATUALIZADO: FOREGROUND_SERVICE_MICROPHONE (obrigatório Android 14 p/ mic em foreground service) e WAKE_LOCK (faltava — sem ela, service.py crasha ao adquirir o wake_lock)
android.permissions = INTERNET,RECORD_AUDIO,VIBRATE,FOREGROUND_SERVICE,FOREGROUND_SERVICE_MICROPHONE,WAKE_LOCK,CAMERA,READ_MEDIA_IMAGES,SYSTEM_ALERT_WINDOW

# 3. CORRIGIDO: faltava ":foreground" — sem isso o Android NUNCA chamava startForeground() de verdade,
# então o serviço rodava como service comum e era morto em minutos pelo limite de segundo plano.
# ":foregroundServiceType=microphone" declara o tipo exigido pelo Android 14 para uso de microfone em foreground.
android.services = Spicaservice:service.py:foreground:foregroundServiceType=microphone

android.accept_sdk_license = True
android.minapi = 24
# 7. ADICIONADO: android.api é a chave que de fato controla qual API o
# buildozer pede ao SDK Manager (diferente de android.sdk, que não faz
# isso sozinho) — sem ela, o buildozer usava um default (API 31) que não
# está pré-instalado no runner do GitHub Actions, causando o erro
# "Requested API target 31 is not available".
android.api = 33
android.sdk = 33
# 8. ADICIONADO: aponta pro SDK Android JÁ PRÉ-INSTALADO no runner do GitHub
# Actions, em vez de deixar o buildozer baixar um do zero — o SDK baixado do
# zero vem completamente vazio (sem nenhuma plataforma instalada), e o p4a
# 2024.1.21 não instala automaticamente a plataforma que falta (só dá erro
# "Requested API target XX is not available"). O caminho abaixo é confirmado
# pela variável ANDROID_SDK_ROOT que já vem definida nesse runner.
android.sdk_path = /usr/local/lib/android/sdk
android.build_tools_version = 33.0.2
android.ndk = 25b
android.ndk_api = 24
android.archs = arm64-v8a
android.allow_backup = True

# 4. REMOVIDO: PROPERTY_SPECIAL_USE_FGS_SUBTYPE não é mais necessária — o serviço agora
# declara o tipo "microphone" (item 3 acima), que é o tipo correto para o que ele realmente faz.

[buildozer]
log_level = 2
warn_on_root = 1

# pip travado - versoes novas quebram import interno do p4a 2024.1.21
