[app]
title = WindIA
package.name = windia
package.domain = com.windia
version = 1.0
source.dir = .
source.include_exts = py,png,jpg,json
source.main = main.py

# Fixado em python3==3.11 para evitar conflito com versões alpha (ex: 3.14) no GitHub Actions
requirements = python3==3.11,kivy==2.3.0,kivymd==1.2.0,requests,certifi,urllib3

orientation = portrait
fullscreen = 0

android.permissions = INTERNET,RECORD_AUDIO,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE,VIBRATE,FOREGROUND_SERVICE

android.minapi = 24
android.sdk = 33
android.ndk = 25b
android.ndk_api = 21
android.archs = arm64-v8a
android.allow_backup = True

[buildozer]
log_level = 2
warn_on_root = 1
