# Build APK (Docker & Buildozer)

This repository includes a `buildozer.spec` and `requirements.txt` to build an Android APK using Buildozer.

Options:

1) Docker (recommended on Windows)

- Install Docker Desktop.
- From project root run (PowerShell):

```bash
# mount current dir and run buildozer inside the official image
docker run --rm -v ${PWD}:/home/user/hostcwd -w /home/user/hostcwd kivy/buildozer:latest \
    buildozer -v android debug
```

- When finished the unsigned debug APK will be in `bin/` (e.g. `bin/swr_cleaner-1.0.0-debug.apk`).

2) WSL2 (Ubuntu) / Native Linux

```bash
# install system deps (Ubuntu example)
sudo apt update && sudo apt install -y python3-pip build-essential git openjdk-11-jdk zip unzip ccache libffi-dev libssl-dev
pip install --user buildozer
# ensure ~/.local/bin is on PATH, then run:
buildozer android debug
```

3) Signing a release APK

- For a distributable release, follow Buildozer docs to set `android.release = True` and configure `key.store`, `key.alias`, etc. See: https://buildozer.readthedocs.io/

Notes:
- Buildozer will download Android SDK/NDK and other toolchains; first run can be long.
- If the build fails, paste the build log (use `buildozer -v android debug`) and I can help diagnose.
