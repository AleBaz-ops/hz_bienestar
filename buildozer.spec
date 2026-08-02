[app]

title = Hz Bienestar Mental
package.name = hzbienestarmental
package.domain = org.alejandro

source.dir = .
source.include_exts = py,png,jpg,kv,atlas,ttf,wav

version = 0.1

# numpy y scipy son necesarios por generar_chunk() (ruido rosa usa scipy.signal.lfilter)
# pyjnius es necesario para el streaming de audio nativo (AudioTrack) en _loop_android()
requirements = python3,kivy,numpy,scipy,pyjnius

orientation = portrait
fullscreen = 0

# No se necesitan permisos especiales: solo reproducimos audio (STREAM_MUSIC),
# no grabamos ni accedemos a almacenamiento externo.
android.permissions =

android.api = 33
android.minapi = 21
android.ndk = 25b
android.archs = arm64-v8a, armeabi-v7a

android.allow_backup = True

[buildozer]

log_level = 2
warn_on_root = 1
