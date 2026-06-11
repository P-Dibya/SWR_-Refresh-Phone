"""
main.py  —  SWR Android Cleaner App
Entry point: KivyMD app shell, ScreenManager, Navigation Drawer, Theme.
"""
import os
os.environ.setdefault("KIVY_NO_ENV_CONFIG", "1")

from kivymd.app import MDApp
from kivymd.uix.navigationdrawer import MDNavigationDrawer, MDNavigationDrawerMenu
from kivymd.uix.list import MDList, OneLineIconListItem
from kivymd.uix.screen import MDScreen
from kivymd.uix.screenmanager import MDScreenManager
from kivy.lang import Builder

# ── Screen imports ──────────────────────────────────────────────
from screens.dashboard        import DashboardScreen
from screens.storage_analyzer import StorageAnalyzerScreen
from screens.app_manager      import AppManagerScreen
from screens.battery_monitor  import BatteryMonitorScreen
from screens.permission_viewer import PermissionViewerScreen
from database import SWRDatabase

# ── KV root layout ───────────────────────────────────────────────
KV = """
<SWRRoot>:
    MDNavigationLayout:
        MDScreenManager:
            id: screen_manager
        MDNavigationDrawer:
            id: nav_drawer
            radius: 0, 16, 16, 0
            MDNavigationDrawerMenu:
                id: nav_menu
"""

class SWRRoot(MDScreen):
    pass

class SWRApp(MDApp):
    title = "SWR Cleaner"
    version = "1.0.0"

    # Navigation entries: (icon, label, screen_name)
    NAV_ITEMS = [
        ("view-dashboard-outline", "Dashboard",        "dashboard"),
        ("broom",                  "Storage Cleaner",  "storage"),
        ("apps",                   "App Manager",      "apps"),
        ("battery-charging",       "Battery Monitor",  "battery"),
        ("shield-check-outline",   "Permissions",      "permissions"),
        ("cog-outline",            "Settings",         "settings"),
    ]

    def build(self):
        # ── Theme ───────────────────────────────────────────────
        self.theme_cls.theme_style   = "Dark"
        self.theme_cls.primary_palette = "Blue"
        self.theme_cls.accent_palette  = "Cyan"
        self.theme_cls.material_style  = "M3"

        Builder.load_string(KV)
        root = SWRRoot()
        sm   = root.ids.screen_manager
        nav  = root.ids.nav_drawer

        # ── Register screens ────────────────────────────────────
        screens = {
            "dashboard":   DashboardScreen(name="dashboard"),
            "storage":     StorageAnalyzerScreen(name="storage"),
            "apps":        AppManagerScreen(name="apps"),
            "battery":     BatteryMonitorScreen(name="battery"),
            "permissions": PermissionViewerScreen(name="permissions"),
        }
        for s in screens.values():
            sm.add_widget(s)

        # ── Build nav drawer items ───────────────────────────────
        nav_list = MDList()
        for icon, label, screen_name in self.NAV_ITEMS:
            item = OneLineIconListItem(
                text=label,
                on_release=lambda x, sn=screen_name, nd=nav, m=sm: (
                    setattr(m, "current", sn),
                    nd.set_state("close"),
                ),
            )
            nav_list.add_widget(item)
        # MDNavigationDrawerMenu is a ScrollView with an internal container.
        # Add the MDList into that container if present, otherwise add directly.
        menu = root.ids.nav_menu
        if menu.children:
            try:
                menu.children[0].add_widget(nav_list)
            except Exception:
                menu.add_widget(nav_list)
        else:
            menu.add_widget(nav_list)

        sm.current = "dashboard"
        return root

    def on_start(self):
        self.db = SWRDatabase()
        self.db.init_db()

    def on_stop(self):
        if hasattr(self, "db"):
            self.db.close()


if __name__ == "__main__":
    SWRApp().run()
