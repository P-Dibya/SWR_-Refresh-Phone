# app_manager.py
"""
screens/app_manager.py  —  SWR App Manager Screen
Lists installed apps, size, cache size, deep-links to Android system settings.
Uses Android PackageManager via pyjnius (jnius) when on-device.
"""
import os, threading
from kivy.clock        import Clock, mainthread
from kivy.lang         import Builder
from kivymd.uix.screen import MDScreen
from kivymd.uix.list   import ThreeLineIconListItem, IconLeftWidget
from kivymd.uix.button import MDIconButton

# ── Android helpers ──────────────────────────────────────────────
try:
    from jnius import autoclass
    PythonActivity   = autoclass("org.kivy.android.PythonActivity")
    PackageManager   = autoclass("android.content.pm.PackageManager")
    Intent           = autoclass("android.content.Intent")
    Uri              = autoclass("android.net.Uri")
    Settings         = autoclass("android.provider.Settings")
    Environment      = autoclass("android.os.Environment")
    StatFs           = autoclass("android.os.StatFs")
    ON_ANDROID       = True
except Exception:
    ON_ANDROID = False

Builder.load_string("""
<AppManagerScreen>:
    name: "apps"
    MDBoxLayout:
        orientation: "vertical"
        md_bg_color: app.theme_cls.bg_normal

        MDTopAppBar:
            title: "App Manager"
            elevation: 0
            left_action_items: [["menu", lambda x: app.root.ids.nav_drawer.set_state("open")]]
            right_action_items: [["refresh", lambda x: root.load_apps()]]

        MDTextField:
            id: search_field
            hint_text: "Search apps…"
            icon_right: "magnify"
            size_hint_y: None
            height: "56dp"
            on_text: root.filter_apps(self.text)

        MDLabel:
            id: summary_label
            text: "Loading…"
            halign: "center"
            size_hint_y: None
            height: "28dp"
            theme_text_color: "Secondary"
            font_style: "Caption"

        ScrollView:
            MDList:
                id: app_list
""")


class AppManagerScreen(MDScreen):
    _all_apps: list = []

    def on_enter(self, *args):
        if not self._all_apps:
            self.load_apps()

    # ── Load ─────────────────────────────────────────────────────
    def load_apps(self):
        self.ids.summary_label.text = "Scanning installed apps…"
        self.ids.app_list.clear_widgets()
        threading.Thread(target=self._fetch_apps, daemon=True).start()

    def _fetch_apps(self):
        apps = []
        if ON_ANDROID:
            ctx = PythonActivity.mActivity
            pm  = ctx.getPackageManager()
            pkgs = pm.getInstalledPackages(PackageManager.GET_META_DATA)
            it   = pkgs.iterator()
            while it.hasNext():
                pkg  = it.next()
                name = pkg.applicationInfo.loadLabel(pm).toString()
                pack = pkg.packageName

                # App size via installed app source directory
                try:
                    src_dir = pkg.applicationInfo.sourceDir
                    size_mb = os.path.getsize(src_dir) / (1024 * 1024)
                except Exception:
                    size_mb = 0.0

                # Cache dir size
                try:
                    cache_dir = pkg.applicationInfo.dataDir + "/cache"
                    cache_mb  = sum(
                        os.path.getsize(os.path.join(dp, f))
                        for dp, _, files in os.walk(cache_dir)
                        for f in files
                    ) / (1024 * 1024)
                except Exception:
                    cache_mb = 0.0

                apps.append({
                    "name":     name,
                    "package":  pack,
                    "size_mb":  size_mb,
                    "cache_mb": cache_mb,
                })
        else:
            # Desktop stub — show running processes via psutil
            try:
                import psutil
                seen = set()
                for proc in psutil.process_iter(["name", "memory_info"]):
                    try:
                        n = proc.info["name"]
                        if n and n not in seen:
                            seen.add(n)
                            mem_mb = (proc.info["memory_info"].rss or 0) / (1024 * 1024)
                            apps.append({
                                "name":     n,
                                "package":  n.lower().replace(" ", "."),
                                "size_mb":  0.0,
                                "cache_mb": mem_mb,
                            })
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
            except ImportError:
                pass

        apps.sort(key=lambda x: x["size_mb"] + x["cache_mb"], reverse=True)
        self._all_apps = apps
        self._render_apps(apps)

    @mainthread
    def _render_apps(self, apps):
        lst = self.ids.app_list
        lst.clear_widgets()
        total_size  = sum(a["size_mb"]  for a in apps)
        total_cache = sum(a["cache_mb"] for a in apps)
        self.ids.summary_label.text = (
            f"{len(apps)} apps  •  {total_size:.0f} MB total  •  "
            f"{total_cache:.0f} MB cached"
        )
        for app in apps[:200]:   # cap render for performance
            item = ThreeLineIconListItem(
                text=app["name"],
                secondary_text=f"App: {app['size_mb']:.1f} MB  •  Cache: {app['cache_mb']:.1f} MB",
                tertiary_text=app["package"],
            )
            item.add_widget(IconLeftWidget(icon="application-outline"))
            # Info button → opens Android app settings
            btn = MDIconButton(
                icon="information-outline",
                on_release=lambda x, p=app["package"]: self._open_app_settings(p),
            )
            item.add_widget(btn)
            lst.add_widget(item)

    # ── Filter ───────────────────────────────────────────────────
    def filter_apps(self, query):
        q = query.lower().strip()
        if not q:
            self._render_apps(self._all_apps)
            return
        filtered = [a for a in self._all_apps
                    if q in a["name"].lower() or q in a["package"].lower()]
        self._render_apps(filtered)

    # ── Open Android app info settings ───────────────────────────
    @staticmethod
    def _open_app_settings(package_name: str):
        if not ON_ANDROID:
            print(f"[SWR] Would open settings for: {package_name}")
            return
        ctx = PythonActivity.mActivity
        intent = Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS)
        intent.addCategory(Intent.CATEGORY_DEFAULT)
        intent.setData(Uri.parse(f"package:{package_name}"))
        intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        ctx.startActivity(intent)

