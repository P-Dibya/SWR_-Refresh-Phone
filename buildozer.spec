[app]
# (str) Title of your application
title = SWR Cleaner

# (str) Package name
package.name = swr_cleaner

# (str) Package domain (needed for android packaging)
package.domain = org.example

# (str) Source code where the main.py is located
source.dir = .

# (str) Supported source file extensions
source.include_exts = py,kv,png,jpg,kvlang

# (str) Application versioning
version = 1.0.0

# (list) Application requirements
# Keep versions minimal; buildozer / p4a will install these via pip.
requirements = python3,kivy,kivymd

# (str) Orientation
orientation = portrait

# (int) Fullscreen (0 = windowed, 1 = fullscreen)
fullscreen = 0

# (list) Permissions
android.permissions = INTERNET,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE

# (str) Presplash image (optional)
# presplash.filename = %(source.dir)s/data/presplash.png

[buildozer]
log_level = 2
warn_on_root = 1

[app]

# ── Identity ───────────────────────────────────────────────────
title        = SWR Cleaner
package.name = swr
package.domain = org.swr

# ── Source ────────────────────────────────────────────────────
source.dir      = .
source.include_exts = py,png,jpg,kv,atlas,db,ttf,otf
source.include_patterns = assets/*,screens/*,assets/kv/*
source.exclude_dirs = tests,bin,.buildozer,__pycache__,.git

# ── Version ───────────────────────────────────────────────────
version = 1.0.0

# ── Entry point ───────────────────────────────────────────────
entrypoint = main.py

# ── Requirements ─────────────────────────────────────────────
# kivymd must match your kivy version exactly
requirements = python3,kivy==2.3.0,kivymd==1.2.0,pillow,plyer,psutil,sqlite3

# ── Orientation ───────────────────────────────────────────────
orientation = portrait

# ── Fullscreen ────────────────────────────────────────────────
fullscreen = 0

# ── Android permissions (only what is needed) ─────────────────
android.permissions = \\
    READ_EXTERNAL_STORAGE, \\
    WRITE_EXTERNAL_STORAGE, \\
    POST_NOTIFICATIONS, \\
    QUERY_ALL_PACKAGES, \\
    FOREGROUND_SERVICE

# Note: READ_EXTERNAL_STORAGE + WRITE_EXTERNAL_STORAGE are scoped
# on Android 10+ — app only accesses its own Downloads folder
# and paths the user grants via Storage Access Framework.

# ── Android API levels ────────────────────────────────────────
android.minapi     = 26
android.api        = 33
android.ndk        = 25b
android.sdk        = 33

# ── NDK & build tools ─────────────────────────────────────────
android.ndk_api    = 26
android.ndk_path   =
android.sdk_path   =
android.accept_sdk_license = True

# ── Architecture ──────────────────────────────────────────────
android.archs = arm64-v8a, armeabi-v7a

# ── Icon & splash ─────────────────────────────────────────────
android.icon.filename          = %(source.dir)s/assets/icon.png
android.presplash.filename     = %(source.dir)s/assets/presplash.png
android.presplash_color        = #1D1D20

# ── Google Play compliance ───────────────────────────────────
# Target SDK 33 satisfies current Play Store requirements.
# Declare QUERY_ALL_PACKAGES in the Play Store declaration
# with justification: read-only permission audit, no data exfiltration.

# ── Gradle extras ─────────────────────────────────────────────
android.gradle_dependencies = com.google.android.material:material:1.9.0

# ── Build backend ─────────────────────────────────────────────
p4a.branch = master

[buildozer]
log_level = 2
warn_on_root = 1
build_dir  = ./.buildozer
bin_dir    = ./bin