[app]
title = Spica
package.name = spica
package.domain = com.spica
version = 1.0
source.dir = .
# 1. ADICIONADO: Garantindo que a extensão .kv (se houver) e os atlas entrem no APK
source.include_exts = py,png,jpg,json,kv,atlas
source.main = main.py

requirements = python3, kivy, https://github.com/kivymd/KivyMD/archive/master.zip, materialyoucolor, asynckivy, requests, certifi, urllib3, plyer, pyjnius

orientation = portrait
fullscreen = 0

icon.filename = %(source.dir)s/Spica.png

# 2. ATUALIZADO: Adicionado FOREGROUND_SERVICE_SPECIAL_USE para compatibilidade com Android 14+
android.permissions = INTERNET,RECORD_AUDIO,VIBRATE,FOREGROUND_SERVICE,FOREGROUND_SERVICE_SPECIAL_USE,CAMERA,READ_MEDIA_IMAGES,SYSTEM_ALERT_WINDOW

# 3. ATUALIZADO E ATIVADO: Apontando corretamente para o arquivo que criamos na raiz do projeto
android.services = Spicaservice:service.py

android.accept_sdk_license = True
android.minapi = 24
android.sdk = 33
android.build_tools_version = 33.0.2
android.ndk = 25b
android.ndk_api = 24
android.archs = arm64-v8a
android.allow_backup = True

# 4. ADICIONADO: Adiciona a tag no manifesto para liberar o recurso especial de segundo plano
android.manifest.application_meta = android.image_picker_v2=true

[buildozer]
log_level = 2
warn_on_root = 1
