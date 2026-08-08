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

requirements = python3, kivy, https://github.com/kivymd/KivyMD/archive/master.zip, https://github.com/T-Dynamos/materialyoucolor-python/archive/main.zip, asynckivy, requests, certifi, urllib3, plyer, pyjnius

# 6. ADICIONADO: forca o python-for-android a usar a branch master (estavel, Python <=3.12)

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
# 7. ADICIONADO: android.api eh a chave que de fato controla qual API o buildozer pede ao SDK Manager
# (diferente de android.sdk, que sozinho nao faz isso) - sem ela, usava um default (API 31) nao
# instalado no runner do GitHub Actions, causando "Requested API target 31 is not available".
android.api = 33
android.sdk = 33
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
