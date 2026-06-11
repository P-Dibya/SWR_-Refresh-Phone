# battery_monitor.py
"""
screens/battery_monitor.py  —  SWR Battery Monitor Screen
Real-time battery: level, health, temperature, voltage, charging status.
On Android uses BatteryManager broadcast; desktop falls back to psutil/plyer.
"""


import threading
from kivy.clock        import Clock, mainthread
from kivy.lang         import Builder
from kivy.properties   import StringProperty
from kivymd.uix.screen import MDScreen
from kivymd.uix.card   import MDCard
from kivymd.uix.label  import MDLabel
from kivymd.uix.boxlayout import MDBoxLayout

# ── Android helpers ──────────────────────────────────────────────
try:
    from jnius import autoclass
    PythonActivity    = autoclass("org.kivy.android.PythonActivity")
    BatteryManager    = autoclass("android.os.BatteryManager")
    IntentFilter      = autoclass("android.content.IntentFilter")
    Intent            = autoclass("android.content.Intent")
    ON_ANDROID = True
except Exception:
    ON_ANDROID = False

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

Builder.load_string("""
<BatteryStatRow>:
    orientation: "horizontal"
    size_hint_y: None
    height: "44dp"
    padding: "16dp", "4dp"

    MDLabel:
        id: stat_key
        text: root.key
        theme_text_color: "Secondary"
        font_style: "Body1"

    MDLabel:
        id: stat_val
        text: root.value
        halign: "right"
        theme_text_color: "Primary"
        font_style: "Body1"

<BatteryMonitorScreen>:
    name: "battery"
    MDBoxLayout:
        orientation: "vertical"
        md_bg_color: app.theme_cls.bg_normal

        MDTopAppBar:
            title: "Battery Monitor"
            elevation: 0
            left_action_items: [["menu", lambda x: app.root.ids.nav_drawer.set_state("open")]]
            right_action_items: [["refresh", lambda x: root.refresh()]]

        ScrollView:
            MDBoxLayout:
                orientation: "vertical"
                padding: "16dp"
                spacing: "12dp"
                adaptive_height: True

                MDCard:
                    id: level_card
                    padding: "16dp"
                    radius: [16]
                    md_bg_color: app.theme_cls.bg_dark
                    size_hint_y: None
                    height: "120dp"
                    MDBoxLayout:
                        orientation: "vertical"
                        MDLabel:
                            id: level_label
                            text: "--%"
                            font_style: "H3"
                            halign: "center"
                        MDLabel:
                            id: status_label
                            text: "Checking…"
                            font_style: "Body1"
                            halign: "center"
                            theme_text_color: "Secondary"

                MDCard:
                    id: detail_card
                    padding: "8dp"
                    radius: [12]
                    md_bg_color: app.theme_cls.bg_dark
                    size_hint_y: None
                    height: "280dp"
                    MDList:
                        id: detail_list

                MDCard:
                    padding: "16dp"
                    radius: [12]
                    md_bg_color: app.theme_cls.bg_dark
                    size_hint_y: None
                    height: "120dp"
                    MDBoxLayout:
                        orientation: "vertical"
                        MDLabel:
                            text: "Tips"
                            font_style: "H6"
                        MDLabel:
                            id: tips_label
                            text: "Loading tips…"
                            font_style: "Caption"
                            theme_text_color: "Secondary"
""")


class BatteryStatRow(MDBoxLayout):
    key   = StringProperty("")
    value = StringProperty("")


class BatteryMonitorScreen(MDScreen):

    def on_enter(self, *args):
        self.refresh()
        self._timer = Clock.schedule_interval(lambda dt: self.refresh(), 10)

    def on_leave(self, *args):
        if hasattr(self, "_timer"):
            self._timer.cancel()

    def refresh(self):
        threading.Thread(target=self._fetch, daemon=True).start()

    def _fetch(self):
        data = {}

        if ON_ANDROID:
            ctx  = PythonActivity.mActivity
            filt = IntentFilter(Intent.ACTION_BATTERY_CHANGED)
            bi   = ctx.registerReceiver(None, filt)

            level   = bi.getIntExtra(BatteryManager.EXTRA_LEVEL,  -1)
            scale   = bi.getIntExtra(BatteryManager.EXTRA_SCALE,  100)
            plugged = bi.getIntExtra(BatteryManager.EXTRA_PLUGGED, 0)
            status  = bi.getIntExtra(BatteryManager.EXTRA_STATUS, -1)
            health  = bi.getIntExtra(BatteryManager.EXTRA_HEALTH, -1)
            temp_raw= bi.getIntExtra(BatteryManager.EXTRA_TEMPERATURE, -1)
            voltage = bi.getIntExtra(BatteryManager.EXTRA_VOLTAGE, -1)
            tech    = bi.getStringExtra(BatteryManager.EXTRA_TECHNOLOGY) or "?"

            pct = int(level * 100 / scale) if scale > 0 else 0

            status_map = {
                BatteryManager.BATTERY_STATUS_CHARGING:     "⚡ Charging",
                BatteryManager.BATTERY_STATUS_DISCHARGING:  "🔋 Discharging",
                BatteryManager.BATTERY_STATUS_FULL:         "✅ Full",
                BatteryManager.BATTERY_STATUS_NOT_CHARGING: "⏸ Not Charging",
            }
            health_map = {
                BatteryManager.BATTERY_HEALTH_GOOD:         "Good",
                BatteryManager.BATTERY_HEALTH_OVERHEAT:     "⚠ Overheat",
                BatteryManager.BATTERY_HEALTH_DEAD:         "❌ Dead",
                BatteryManager.BATTERY_HEALTH_OVER_VOLTAGE: "⚠ Over Voltage",
                BatteryManager.BATTERY_HEALTH_COLD:         "❄ Cold",
            }
            plug_map = {1: "AC", 2: "USB", 4: "Wireless"}

            data = {
                "Level":       f"{pct}%",
                "Status":      status_map.get(status, "Unknown"),
                "Health":      health_map.get(health, "Unknown"),
                "Temperature": f"{temp_raw / 10:.1f} °C" if temp_raw >= 0 else "N/A",
                "Voltage":     f"{voltage} mV" if voltage > 0 else "N/A",
                "Technology":  tech,
                "Plug":        plug_map.get(plugged, "Unplugged"),
                "_pct":        pct,
                "_status":     status_map.get(status, ""),
            }

        elif HAS_PSUTIL:
            b = psutil.sensors_battery()
            if b:
                pct     = int(b.percent)
                charging = b.power_plugged
                secs    = b.secsleft
                hrs     = f"{secs // 3600}h {(secs % 3600) // 60}m" if secs > 0 else "—"
                data = {
                    "Level":       f"{pct}%",
                    "Status":      "⚡ Charging" if charging else "🔋 Discharging",
                    "Time Left":   hrs,
                    "Technology":  "Li-Ion (estimated)",
                    "_pct":        pct,
                    "_status":     "⚡ Charging" if charging else "🔋 Discharging",
                }
            else:
                data = {"Level": "N/A", "_pct": 0, "_status": "Not available"}
        else:
            data = {"Level": "N/A", "_pct": 0, "_status": "psutil not installed"}

        self._update_ui(data)

    @mainthread
    def _update_ui(self, data):
        pct    = data.get("_pct", 0)
        status = data.get("_status", "")

        # Level card colour
        if pct >= 60:
            color = [0.55, 0.90, 0.63, 1]   # green
        elif pct >= 20:
            color = [1.00, 0.71, 0.51, 1]   # orange
        else:
            color = [0.94, 0.27, 0.22, 1]   # red

        self.ids.level_label.text       = data.get("Level", "--")
        self.ids.level_label.text_color = color
        self.ids.level_label.theme_text_color = "Custom"
        self.ids.status_label.text      = status

        # Detail rows
        lst = self.ids.detail_list
        lst.clear_widgets()
        skip = {"_pct", "_status"}
        from kivymd.uix.list import OneLineListItem
        for key, val in data.items():
            if key in skip:
                continue
            row = OneLineListItem(text=f"{key}:  {val}")
            lst.add_widget(row)

        # Tips
        if pct < 20:
            tip = "⚠ Battery critically low — plug in soon."
        elif pct < 40:
            tip = "Consider charging. Avoid heavy apps."
        elif "Overheat" in data.get("Health", ""):
            tip = "⚠ Battery overheating — remove case, cool device."
        elif "⚡" in status:
            tip = "Charging. Avoid full charge cycles for longevity."
        else:
            tip = "Battery is in good condition. Keep screen brightness moderate."
        self.ids.tips_label.text = tip

