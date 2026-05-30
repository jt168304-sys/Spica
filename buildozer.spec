[app]
title = Spica
package.name = spica
package.domain = com.spica
version = 1.0
source.dir = .
source.include_exts = py,png,jpg,json
source.main = main.py

requirements = python3==3.11.9,hostpython3==3.11.9,kivy==2.3.0,kivymd==1.2.0,requests,certifi,urllib3

orientation = portrait
fullscreen = 0

icon.filename = %(source.dir)s/Spica.png

android.permissions = INTERNET,RECORD_AUDIO,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE,VIBRATE,FOREGROUND_SERVICE,CAMERA,READ_MEDIA_IMAGES,READ_MEDIA_VIDEO

android.sdk_path = /usr/local/lib/android/sdk
android.ndk_path = /usr/local/lib/android/sdk/ndk/25.2.9519653
android.skip_update = True
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
