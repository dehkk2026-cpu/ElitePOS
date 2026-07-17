[app]
title = ElitePOS
package.name = elitepos
package.domain = org.enterprise
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json,ttf
version = 1.0
requirements = python3, kivy==2.3.0, kivymd, pillow, arabic-reshaper, python-bidi, jnius
orientation = landscape
fullscreen = 1
android.permissions = BLUETOOTH,BLUETOOTH_ADMIN,BLUETOOTH_CONNECT,BLUETOOTH_SCAN,ACCESS_FINE_LOCATION,ACCESS_COARSE_LOCATION,INTERNET
android.api = 33
android.minapi = 21
android.logcat_filters = *:S python:D
android.private_storage = True
​[buildozer]
log_level = 2
warn_on_root = 1