# dashboard.py
"""
screens/dashboard.py  —  SWR Dashboard Screen
Device Health Score, Storage/RAM/Battery/CPU cards.
"""
import os, math
from kivy.clock       import Clock
from kivy.lang        import Builder
from kivy.properties  import NumericProperty, StringProperty, ListProperty
from kivymd.uix.screen import MDScreen
from kivymd.uix.card   import MDCard
from kivymd.uix.label  import MDLabel
from kivymd.uix.boxlayout import MDBoxLayout

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

# ── Try Android battery API (pyjnius / plyer) ─────────────────────
try:
    from plyer import battery as plyer_battery
    HAS_PLYER = True
except Exception:
    HAS_PLYER = False

Builder.load_string("""
<StatCard>:
    orientation: "vertical"
    padding: "12dp"
    spacing: "4dp"
    radius: [12]
    md_bg_color: app.theme_cls.bg_dark
    size_hint_y: None
    height: "120dp"

    MDLabel:
        id: card_value
        text: root.value_text
        font_style: "H5"
        halign: "center"
        theme_text_color: "Custom"
        text_color: root.value_color

    MDLabel:
        id: card_title
        text: root.title_text
        font_style: "Caption"
        halign: "center"
        theme_text_color: "Secondary"

    MDLabel:
        id: card_sub
        text: root.sub_text
        font_style: "Overline"
        halign: "center"
        theme_text_color: "Secondary"

<DashboardScreen>:
    name: "dashboard"
    MDBoxLayout:
        orientation: "vertical"
        padding: "16dp"
        spacing: "12dp"
        md_bg_color: app.theme_cls.bg_normal

        MDTopAppBar:
            title: "SWR — Dashboard"
            elevation: 0
            left_action_items: [["menu", lambda x: app.root.ids.nav_drawer.set_state("open")]]

        MDLabel:
            id: health_label
            text: "Health Score: --"
            font_style: "H4"
            halign: "center"
            size_hint_y: None
            height: "56dp"

        MDGridLayout:
            id: stat_grid
            cols: 2
            spacing: "8dp"
            size_hint_y: None
            height: "256dp"
            adaptive_height: True

        MDLabel:
            text: "Tap a card to open that screen for details."
            font_style: "Caption"
            halign: "center"
            theme_text_color: "Secondary"
""")


class StatCard(MDCard):
    value_text  = StringProperty("--")
    title_text  = StringProperty("Stat")
    sub_text    = StringProperty("")
    value_color = ListProperty([0.63, 0.79, 0.95, 1])   # #A1C9F4


class DashboardScreen(MDScreen):
    health_score = NumericProperty(0)

    def on_enter(self, *args):
        self._refresh()
        self._timer = Clock.schedule_interval(lambda dt: self._refresh(), 5)

    def on_leave(self, *args):
        if hasattr(self, "_timer"):
            self._timer.cancel()

    # ── Helpers ─────────────────────────────────────────────────
    @staticmethod
    def _pct_color(pct):
        """Green < 60, Orange 60-80, Red > 80."""
        if pct < 60:
            return [0.55, 0.90, 0.63, 1]   # green  #8DE5A1
        if pct < 80:
            return [1.00, 0.71, 0.51, 1]   # orange #FFB482
        return    [0.94, 0.27, 0.22, 1]    # red    #F04438

    @staticmethod
    def _fmt_bytes(b):
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if b < 1024:
                return f"{b:.1f} {unit}"
            b /= 1024
        return f"{b:.1f} PB"

    def _refresh(self):
        grid = self.ids.stat_grid
        grid.clear_widgets()

        scores = []

        # ── Storage ─────────────────────────────────────────────
        if HAS_PSUTIL:
            disk  = psutil.disk_usage("/")
            d_pct = disk.percent
            scores.append(100 - d_pct)
            card = StatCard(
                value_text  = f"{d_pct:.0f}%",
                title_text  = "Storage Used",
                sub_text    = f"Free: {self._fmt_bytes(disk.free)}",
                value_color = self._pct_color(d_pct),
            )
        else:
            card = StatCard(value_text="N/A", title_text="Storage", sub_text="psutil not available")
        grid.add_widget(card)

        # ── RAM ─────────────────────────────────────────────────
        if HAS_PSUTIL:
            mem   = psutil.virtual_memory()
            m_pct = mem.percent
            scores.append(100 - m_pct)
            card = StatCard(
                value_text  = f"{m_pct:.0f}%",
                title_text  = "RAM Used",
                sub_text    = f"Free: {self._fmt_bytes(mem.available)}",
                value_color = self._pct_color(m_pct),
            )
        else:
            card = StatCard(value_text="N/A", title_text="RAM", sub_text="")
        grid.add_widget(card)

        # ── CPU ──────────────────────────────────────────────────
        if HAS_PSUTIL:
            cpu   = psutil.cpu_percent(interval=0.3)
            scores.append(100 - cpu)
            card = StatCard(
                value_text  = f"{cpu:.0f}%",
                title_text  = "CPU Usage",
                sub_text    = f"{psutil.cpu_count()} cores",
                value_color = self._pct_color(cpu),
            )
        else:
            card = StatCard(value_text="N/A", title_text="CPU", sub_text="")
        grid.add_widget(card)

        # ── Battery ──────────────────────────────────────────────
        batt_pct = None
        batt_sub = ""
        if HAS_PLYER:
            try:
                b = plyer_battery.status
                batt_pct = b.get("percentage", None)
                charging = b.get("isCharging", False)
                batt_sub = "⚡ Charging" if charging else "On battery"
            except Exception:
                pass
        elif HAS_PSUTIL:
            b = psutil.sensors_battery()
            if b:
                batt_pct = b.percent
                batt_sub = "⚡ Charging" if b.power_plugged else "On battery"

        if batt_pct is not None:
            scores.append(batt_pct)
            card = StatCard(
                value_text  = f"{batt_pct:.0f}%",
                title_text  = "Battery",
                sub_text    = batt_sub,
                value_color = self._pct_color(100 - batt_pct),
            )
        else:
            card = StatCard(value_text="N/A", title_text="Battery", sub_text=batt_sub)
        grid.add_widget(card)

        # ── Health Score ─────────────────────────────────────────
        if scores:
            hs = math.floor(sum(scores) / len(scores))
        else:
            hs = 0
        self.ids.health_label.text = f"Health Score: {hs}/100"
        if hs >= 70:
            self.ids.health_label.theme_text_color = "Custom"
            self.ids.health_label.text_color = [0.55, 0.90, 0.63, 1]
        elif hs >= 40:
            self.ids.health_label.theme_text_color = "Custom"
            self.ids.health_label.text_color = [1.00, 0.71, 0.51, 1]
        else:
            self.ids.health_label.theme_text_color = "Custom"
            self.ids.health_label.text_color = [0.94, 0.27, 0.22, 1]
