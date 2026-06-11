# storage_analyzer.py
"""
screens/storage_analyzer.py  —  SWR Storage Cleaner Screen
Scans: Downloads, large files, duplicate files, unused APKs.
User reviews and confirms before any deletion.
"""

import os, hashlib, threading
from pathlib import Path

from kivy.clock        import Clock, mainthread
from kivy.lang         import Builder
from kivy.properties   import StringProperty, BooleanProperty, ListProperty
from kivymd.uix.screen import MDScreen
from kivymd.uix.list   import TwoLineIconListItem, IconLeftWidget
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDFlatButton, MDRaisedButton
from kivymd.uix.selectioncontrol import MDCheckbox

# ── Android path helpers ─────────────────────────────────────────
try:
    from android.storage import primary_external_storage_path
    EXTERNAL = primary_external_storage_path()
except Exception:
    EXTERNAL = os.path.expanduser("~")   # desktop fallback

SCAN_PATHS = {
    "downloads": [
        os.path.join(EXTERNAL, "Download"),
        os.path.join(EXTERNAL, "Downloads"),
    ],
    "all": [EXTERNAL],
}

# Thresholds
LARGE_FILE_MB   = 50     # files >= 50 MB are flagged as "large"
MAX_SCAN_FILES  = 5_000  # safety cap

Builder.load_string("""
<StorageAnalyzerScreen>:
    name: "storage"
    MDBoxLayout:
        orientation: "vertical"
        md_bg_color: app.theme_cls.bg_normal

        MDTopAppBar:
            title: "Storage Cleaner"
            elevation: 0
            left_action_items: [["menu", lambda x: app.root.ids.nav_drawer.set_state("open")]]
            right_action_items: [["refresh", lambda x: root.start_scan()]]

        MDBoxLayout:
            orientation: "horizontal"
            padding: "12dp"
            spacing: "8dp"
            size_hint_y: None
            height: "56dp"

            MDRaisedButton:
                text: "Scan Downloads"
                on_release: root.start_scan("downloads")
            MDRaisedButton:
                text: "Full Scan"
                md_bg_color: app.theme_cls.accent_color
                on_release: root.start_scan("all")

        MDLabel:
            id: status_label
            text: "Tap Scan to begin."
            halign: "center"
            size_hint_y: None
            height: "32dp"
            theme_text_color: "Secondary"

        ScrollView:
            MDList:
                id: results_list

        MDBoxLayout:
            orientation: "horizontal"
            padding: "12dp"
            spacing: "8dp"
            size_hint_y: None
            height: "60dp"

            MDRaisedButton:
                id: delete_btn
                text: "Delete Selected"
                disabled: True
                md_bg_color: 0.94, 0.27, 0.22, 1
                on_release: root.confirm_delete()
            MDFlatButton:
                text: "Clear Selection"
                on_release: root.clear_selection()
""")


class StorageAnalyzerScreen(MDScreen):
    selected_files: list = []

    def on_enter(self, *args):
        self.selected_files = []

    # ── Scan ─────────────────────────────────────────────────────
    def start_scan(self, mode="downloads"):
        self.ids.status_label.text = "Scanning…"
        self.ids.results_list.clear_widgets()
        self.selected_files = []
        self.ids.delete_btn.disabled = True
        threading.Thread(
            target=self._scan_worker, args=(mode,), daemon=True
        ).start()

    def _scan_worker(self, mode):
        results = []
        seen_hashes: dict = {}          # md5 -> first path (duplicates)
        paths = SCAN_PATHS.get(mode, SCAN_PATHS["downloads"])
        scanned = 0

        for base in paths:
            if not os.path.isdir(base):
                continue
            for root_dir, dirs, files in os.walk(base):
                # skip hidden dirs
                dirs[:] = [d for d in dirs if not d.startswith(".")]
                for fname in files:
                    if scanned >= MAX_SCAN_FILES:
                        break
                    fpath = os.path.join(root_dir, fname)
                    try:
                        size = os.path.getsize(fpath)
                    except OSError:
                        continue
                    scanned += 1
                    ext   = Path(fname).suffix.lower()
                    tags  = []

                    if ext == ".apk":
                        tags.append("Unused APK")
                    if size >= LARGE_FILE_MB * 1024 * 1024:
                        tags.append(f"Large ({size // (1024*1024)} MB)")
                    if ext in (".mp4", ".mkv", ".avi", ".mov"):
                        tags.append("Video")

                    # Duplicate check (hash only files < 200 MB for speed)
                    if size < 200 * 1024 * 1024:
                        try:
                            h = hashlib.md5(open(fpath, "rb").read(65536)).hexdigest()
                            if h in seen_hashes:
                                tags.append("Duplicate")
                            else:
                                seen_hashes[h] = fpath
                        except OSError:
                            pass

                    if tags:
                        results.append({
                            "path": fpath,
                            "size": size,
                            "tags": tags,
                            "name": fname,
                        })

        results.sort(key=lambda x: x["size"], reverse=True)
        self._update_ui(results, scanned)

    @mainthread
    def _update_ui(self, results, scanned):
        lst = self.ids.results_list
        lst.clear_widgets()
        if not results:
            self.ids.status_label.text = f"✅ Clean! Scanned {scanned} files — nothing to remove."
            return

        total_mb = sum(r["size"] for r in results) / (1024 * 1024)
        self.ids.status_label.text = (
            f"Found {len(results)} items  •  ~{total_mb:.1f} MB  •  Select to delete"
        )

        for item in results:
            icon = (
                "file-document-outline" if ".apk" in item["name"].lower()
                else "file-video-outline" if item["name"].lower().endswith(
                    (".mp4", ".mkv", ".avi", ".mov"))
                else "content-copy" if "Duplicate" in item["tags"]
                else "file-alert-outline"
            )
            tag_str = ", ".join(item["tags"])
            size_mb = item["size"] / (1024 * 1024)
            row = TwoLineIconListItem(
                text=item["name"],
                secondary_text=f"{tag_str}  •  {size_mb:.1f} MB",
            )
            row.add_widget(IconLeftWidget(icon=icon))

            # Checkbox for selection
            chk = MDCheckbox(size_hint=(None, None), size=("48dp", "48dp"))
            _path = item["path"]
            chk.bind(active=lambda w, val, p=_path: self._toggle_select(p, val))
            row.add_widget(chk)
            lst.add_widget(row)

    # ── Selection ────────────────────────────────────────────────
    def _toggle_select(self, path, active):
        if active and path not in self.selected_files:
            self.selected_files.append(path)
        elif not active and path in self.selected_files:
            self.selected_files.remove(path)
        self.ids.delete_btn.disabled = len(self.selected_files) == 0

    def clear_selection(self):
        self.selected_files = []
        self.ids.delete_btn.disabled = True
        self.ids.results_list.clear_widgets()

    # ── Confirm & Delete ─────────────────────────────────────────
    def confirm_delete(self):
        n  = len(self.selected_files)
        mb = sum(os.path.getsize(f) for f in self.selected_files
                 if os.path.exists(f)) / (1024 * 1024)

        self._dialog = MDDialog(
            title="Confirm Deletion",
            text=(
                f"You are about to permanently delete {n} file(s) "
                f"({mb:.1f} MB).\\nThis cannot be undone."
            ),
            buttons=[
                MDFlatButton(
                    text="CANCEL",
                    on_release=lambda x: self._dialog.dismiss(),
                ),
                MDRaisedButton(
                    text="DELETE",
                    md_bg_color=[0.94, 0.27, 0.22, 1],
                    on_release=lambda x: (self._dialog.dismiss(), self._do_delete()),
                ),
            ],
        )
        self._dialog.open()

    def _do_delete(self):
        deleted, failed = 0, 0
        for path in list(self.selected_files):
            try:
                os.remove(path)
                deleted += 1
            except OSError:
                failed += 1
        self.selected_files = []
        self.ids.delete_btn.disabled = True
        msg = f"✅ Deleted {deleted} file(s)."
        if failed:
            msg += f"  ⚠ {failed} could not be removed."
        self.ids.status_label.text = msg
        self.ids.results_list.clear_widgets()
