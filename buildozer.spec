[app]
title = WindIA
package.name = windia
package.domain = com.windia
version = 1.0
source.dir = .
source.include_exts = py,png,jpg,json
source.main = main.py

# Dependências
requirements = python3==3.11.0,hostpython3==3.11.0,kivy==2.3.0,kivymd==1.2.0,requests,certifi,urllib3

# Orientação e tela
orientation = portrait
fullscreen = 0

# Permissões necessárias
android.permissions = INTERNET,RECORD_AUDIO,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE,VIBRATE,FOREGROUND_SERVICE

# Android SDK - usar SDK do sistema
android.sdk_path = /usr/local/lib/android/sdk
android.ndk_path = /usr/local/lib/android/sdk/ndk/27.3.13750724
android.skip_update = True
android.accept_sdk_license = True

android.minapi = 24
android.sdk = 33
android.build_tools_version = 33.0.2
android.ndk = 25b
android.ndk_api = 21
android.archs = arm64-v8a

android.allow_backup = True

[buildozer]
log_level = 2
warn_on_root = 1
