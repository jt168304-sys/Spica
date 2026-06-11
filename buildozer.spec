[app]
title = Spica
package.name = spica
package.domain = com.spica
version = 1.0
source.dir = .
source.include_exts = py,png,jpg,json
source.main = main.py

# kivy, kivymd e android sao gerenciados pelo p4a via recipes
# nao colocar versao fixa em kivy/kivymd
requirements = python3,kivy,kivymd,requests,certifi,urllib3,plyer

orientation = portrait
fullscreen = 0

icon.filename = %(source.dir)s/Spica.png

android.permissions = INTERNET,RECORD_AUDIO,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE,VIBRATE,FOREGROUND_SERVICE,CAMERA,READ_MEDIA_IMAGES,SYSTEM_ALERT_WINDOW

android.add_src = android/src
android.accept_sdk_license = True
android.minapi = 24
android.sdk = 33
android.build_tools_version = 33.0.2
android.ndk = 25b
android.ndk_api = 24
android.archs = arm64-v8a
android.allow_backup = True

[buildozer]
log_level = 2
warn_on_root = 1
