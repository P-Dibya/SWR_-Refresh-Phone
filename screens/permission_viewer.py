# permission_viewer.py
"""
screens/permission_viewer.py  —  SWR Permission Viewer Screen
Audits which apps hold Camera / Microphone / Location permissions.
Read-only: no permissions are granted or revoked — user is directed to
system settings to manage them manually.
"""

import threading
from kivy.clock        import Clock, mainthread
from kivy.lang         import Builder
from kivymd.uix.screen import MDScreen
from kivymd.uix.list   import TwoLineIconListItem, IconLeftWidget
from kivymd.uix.button import MDIconButton

try:
    from jnius import autoclass
    PythonActivity = autoclass("org.kivy.android.PythonActivity")
    PackageManager = autoclass("android.content.pm.PackageManager")
    Intent         = autoclass("android.content.Intent")
    Uri            = autoclass("android.net.Uri")
    Settings       = autoclass("android.provider.Settings")
    Manifest       = autoclass("android.Manifest$permission")
    ON_ANDROID = True
except Exception:
    ON_ANDROID = False

# Permissions to audit
AUDIT_PERMISSIONS = {
    "Camera":      "android.permission.CAMERA",
    "Microphone":  "android.permission.RECORD_AUDIO",
    "Location":    "android.permission.ACCESS_FINE_LOCATION",
    "Contacts":    "android.permission.READ_CONTACTS",    # read-only audit
    "Phone":       "android.permission.READ_PHONE_STATE",
    "Storage R":   "android.permission.READ_EXTERNAL_STORAGE",
    "Storage W":   "android.permission.WRITE_EXTERNAL_STORAGE",
}

PERM_ICONS = {
    "Camera":     "camera",
    "Microphone": "microphone",
    "Location":   "map-marker",
    "Contacts":   "contacts",
    "Phone":      "phone",
    "Storage R":  "folder-open",
    "Storage W":  "folder-edit",
}
PERM_RISK = {
    "Camera": "high", "Microphone": "high", "Location": "high",
    "Contacts": "medium", "Phone": "medium",
    "Storage R": "low", "Storage W": "low",
}
RISK_COLOR = {
    "high":   [0.94, 0.27, 0.22, 1],   # red
    "medium": [1.00, 0.71, 0.51, 1],   # orange
    "low":    [0.55, 0.90, 0.63, 1],   # green
}

Builder.load_string("""
<PermissionViewerScreen>:
    name: "permissions"
    MDBoxLayout:
        orientation: "vertical"
        md_bg_color: app.theme_cls.bg_normal

        MDTopAppBar:
            title: "Permission Audit"
            elevation: 0
            left_action_items: [["menu", lambda x: app.root.ids.nav_drawer.set_state("open")]]
            right_action_items: [["refresh", lambda x: root.load_audit()]]

        MDBoxLayout:
            orientation: "horizontal"
            padding: "12dp"
            spacing: "6dp"
            size_hint_y: None
            height: "52dp"

            MDRaisedButton:
                text: "All"
                on_release: root.set_filter(None)
            MDRaisedButton:
                text: "Camera"
                on_release: root.set_filter("Camera")
            MDRaisedButton:
                text: "Mic"
                on_release: root.set_filter("Microphone")
            MDRaisedButton:
                text: "Location"
                on_release: root.set_filter("Location")

        MDLabel:
            id: summary_label
            text: "Tap Refresh to audit permissions."
            halign: "center"
            size_hint_y: None
            height: "28dp"
            theme_text_color: "Secondary"
            font_style: "Caption"

        ScrollView:
            MDList:
                id: perm_list
""")


class PermissionViewerScreen(MDScreen):
    _audit_results: list = []
    _active_filter = None

    def on_enter(self, *args):
        if not self._audit_results:
            self.load_audit()

    def set_filter(self, perm_name):
        self._active_filter = perm_name
        self._render(self._audit_results)

    def load_audit(self):
        self.ids.summary_label.text = "Auditing…"
        self.ids.perm_list.clear_widgets()
        threading.Thread(target=self._fetch_audit, daemon=True).start()

    def _fetch_audit(self):
        results = []

        if ON_ANDROID:
            ctx = PythonActivity.mActivity
            pm  = ctx.getPackageManager()
            pkgs = pm.getInstalledPackages(PackageManager.GET_PERMISSIONS)
            it   = pkgs.iterator()

            while it.hasNext():
                pkg  = it.next()
                name = pkg.applicationInfo.loadLabel(pm).toString()
                pack = pkg.packageName
                declared = pkg.requestedPermissions
                if not declared:
                    continue
                perm_list_java = list(declared)

                granted_labels = []
                for label, perm_str in AUDIT_PERMISSIONS.items():
                    if perm_str in perm_list_java:
                        # Check if actually granted (Android 6+)
                        g = pm.checkPermission(perm_str, pack)
                        if g == PackageManager.PERMISSION_GRANTED:
                            granted_labels.append(label)

                if granted_labels:
                    results.append({
                        "name":    name,
                        "package": pack,
                        "perms":   granted_labels,
                    })
        else:
            # Desktop stub
            results = [
                {"name": "Example App A", "package": "com.example.a",
                 "perms": ["Camera", "Microphone"]},
                {"name": "Example App B", "package": "com.example.b",
                 "perms": ["Location", "Storage R"]},
                {"name": "Example App C", "package": "com.example.c",
                 "perms": ["Camera", "Location", "Contacts"]},
            ]

        results.sort(key=lambda x: (
            sum(1 for p in x["perms"] if PERM_RISK.get(p) == "high") * -1
        ))
        self._audit_results = results
        self._render(results)

    @mainthread
    def _render(self, results):
        lst = self.ids.perm_list
        lst.clear_widgets()

        filtered = [
            r for r in results
            if self._active_filter is None or self._active_filter in r["perms"]
        ]

        high_risk = sum(
            1 for r in filtered
            if any(PERM_RISK.get(p) == "high" for p in r["perms"])
        )
        self.ids.summary_label.text = (
            f"{len(filtered)} apps  •  {high_risk} with high-risk permissions"
        )

        for app in filtered:
            perms_str = ", ".join(app["perms"])
            # Determine highest risk colour
            max_risk = "low"
            for p in app["perms"]:
                r = PERM_RISK.get(p, "low")
                if r == "high":
                    max_risk = "high"; break
                elif r == "medium":
                    max_risk = "medium"
            color = RISK_COLOR[max_risk]

            icon = PERM_ICONS.get(app["perms"][0], "shield-alert-outline")
            item = TwoLineIconListItem(
                text=app["name"],
                secondary_text=perms_str,
            )
            icon_widget = IconLeftWidget(icon=icon)
            icon_widget.icon_color = color
            item.add_widget(icon_widget)

            # Settings deep-link button
            btn = MDIconButton(
                icon="open-in-new",
                on_release=lambda x, p=app["package"]: self._open_settings(p),
            )
            item.add_widget(btn)
            lst.add_widget(item)

    @staticmethod
    def _open_settings(package_name: str):
        if not ON_ANDROID:
            print(f"[SWR] Would open app settings for: {package_name}")
            return
        ctx    = PythonActivity.mActivity
        intent = Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS)
        intent.setData(Uri.parse(f"package:{package_name}"))
        intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        ctx.startActivity(intent)
