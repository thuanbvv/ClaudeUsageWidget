"""StatusNotifierItem + dbusmenu indicator."""
import os
import sys
import threading
import time

import gi
gi.require_version("Gio", "2.0")
from gi.repository import Gio, GLib

from .api import fetch_usage
from .dbus_xml import MENU_XML, SNI_XML
from .icon import ICON_SIZE, render_icon
from .settings import INTERVALS, load_settings, save_settings
from .view import build_view


class Indicator:
    SNI_PATH, MENU_PATH = "/StatusNotifierItem", "/MenuBar"

    def __init__(self, loop):
        self.loop, self.conn = loop, None
        self.session = self.weekly = None
        self.label, self.tooltip, self.error = "…", "Claude usage: loading", None
        self.rows = [("item", "Loading…")]
        self.layout_rev = 1
        self.icon = render_icon(None)
        self.settings = load_settings()
        self.timer = None
        self.last_fetch = 0.0
        self.nodes = {}

    # -- D-Bus plumbing --
    def start(self):
        self.conn = Gio.bus_get_sync(Gio.BusType.SESSION)
        self.sni_info = Gio.DBusNodeInfo.new_for_xml(SNI_XML).interfaces[0]
        self.menu_info = Gio.DBusNodeInfo.new_for_xml(MENU_XML).interfaces[0]
        self.conn.register_object(self.SNI_PATH, self.sni_info, self.on_sni_call, self.on_sni_get, None)
        self.conn.register_object(self.MENU_PATH, self.menu_info, self.on_menu_call, self.on_menu_get, None)
        self.name = f"org.kde.StatusNotifierItem-{os.getpid()}-1"
        Gio.bus_own_name_on_connection(self.conn, self.name, Gio.BusNameOwnerFlags.NONE, self.on_name, None)
        # Re-register if the shell/watcher restarts.
        Gio.bus_watch_name_on_connection(self.conn, "org.kde.StatusNotifierWatcher",
                                         Gio.BusNameWatcherFlags.NONE, lambda *a: self.register(), None)
        self.rebuild()
        self.refresh(force=True)
        self.schedule()

    def schedule(self):
        if self.timer:
            GLib.source_remove(self.timer)
        self.timer = GLib.timeout_add_seconds(self.settings["interval"], lambda: (self.refresh(), True)[1])

    def on_name(self, conn, name):
        self.register()

    def register(self):
        self.conn.call("org.kde.StatusNotifierWatcher", "/StatusNotifierWatcher",
                       "org.kde.StatusNotifierWatcher", "RegisterStatusNotifierItem",
                       GLib.Variant("(s)", (self.name,)), None, Gio.DBusCallFlags.NONE, -1, None,
                       lambda c, r: self._reg_done(c, r))

    def _reg_done(self, c, r):
        try:
            c.call_finish(r)
        except Exception as e:
            print("StatusNotifierWatcher registration failed:", e, file=sys.stderr)

    def emit(self, path, iface, sig, params=None):
        self.conn.emit_signal(None, path, iface, sig, params)

    # -- SNI --
    def on_sni_get(self, conn, sender, path, iface, prop):
        pix = GLib.Variant("a(iiay)", [(ICON_SIZE, ICON_SIZE, self.icon)])
        v = {
            "Category": GLib.Variant("s", "ApplicationStatus"),
            "Id": GLib.Variant("s", "claude-usage-indicator"),
            "Title": GLib.Variant("s", "Claude Usage"),
            "Status": GLib.Variant("s", "Active"),
            "WindowId": GLib.Variant("i", 0),
            "IconName": GLib.Variant("s", ""),
            "IconPixmap": pix,
            "OverlayIconName": GLib.Variant("s", ""),
            "AttentionIconName": GLib.Variant("s", ""),
            "ToolTip": GLib.Variant("(sa(iiay)ss)", ("", [], "Claude Usage", self.tooltip)),
            "ItemIsMenu": GLib.Variant("b", True),
            "Menu": GLib.Variant("o", self.MENU_PATH),
            "XAyatanaLabel": GLib.Variant("s", self.label),
            "XAyatanaLabelGuide": GLib.Variant("s", "100% · 100%"),
        }
        return v.get(prop)

    def on_sni_call(self, conn, sender, path, iface, method, params, inv):
        if method in ("Activate", "SecondaryActivate"):
            self.refresh()
        inv.return_value(None)

    # -- dbusmenu --
    def on_menu_get(self, conn, sender, path, iface, prop):
        return {"Version": GLib.Variant("u", 3), "TextDirection": GLib.Variant("s", "ltr"),
                "Status": GLib.Variant("s", "normal"), "IconThemePath": GLib.Variant("as", [])}.get(prop)

    def build_nodes(self):
        """Flatten self.rows + static entries into {id: node}; node 0 is the root."""
        # Ids are stable per role: the shell caches properties by id, so an id must never
        # switch between separator / label / radio across rebuilds.
        nodes = {}

        def add(parent, nid, label=None, enabled=True, sep=False, action=None, radio=None, submenu=False):
            nodes[nid] = dict(id=nid, label=label, enabled=enabled, sep=sep, action=action,
                              radio=radio, submenu=submenu, children=[])
            nodes[parent]["children"].append(nid)

        nodes[0] = dict(id=0, children=[], submenu=True)
        n_item = n_sep = 0
        for kind, text in self.rows:
            if kind == "sep":
                n_sep += 1
                add(0, 100 + n_sep, sep=True)
            else:
                n_item += 1
                add(0, n_item, text, enabled=False)
        add(0, 900, "⚙  Refresh interval", submenu=True)
        for k, (secs, name) in enumerate(INTERVALS):
            add(900, 910 + k, name, radio=(secs == self.settings["interval"]),
                action=lambda s=secs: self.set_interval(s))
        add(0, 990, sep=True)
        add(0, 991, "Quit", action=self.loop.quit)
        return nodes

    def set_interval(self, secs):
        self.settings["interval"] = secs
        save_settings(self.settings)
        self.schedule()
        self.rebuild()

    def item_props(self, n):
        if n["id"] == 0:
            return {"children-display": GLib.Variant("s", "submenu")}
        if n["sep"]:
            return {"type": GLib.Variant("s", "separator")}
        p = {"label": GLib.Variant("s", n["label"]), "enabled": GLib.Variant("b", n["enabled"])}
        if n["submenu"]:
            p["children-display"] = GLib.Variant("s", "submenu")
        if n["radio"] is not None:
            p["toggle-type"] = GLib.Variant("s", "radio")
            p["toggle-state"] = GLib.Variant("i", 1 if n["radio"] else 0)
        return p

    def layout(self, i, depth):
        n = self.nodes[i]
        kids = []
        if depth != 0:
            kids = [GLib.Variant("(ia{sv}av)", self.layout(c, depth - 1)) for c in n["children"]]
        return (i, self.item_props(n), kids)

    def on_menu_call(self, conn, sender, path, iface, method, params, inv):
        if method == "GetLayout":
            parent, depth = params.unpack()[:2]
            inv.return_value(GLib.Variant("(u(ia{sv}av))", (self.layout_rev, self.layout(parent if parent in self.nodes else 0, depth))))
        elif method == "GetGroupProperties":
            ids = params.unpack()[0] or list(self.nodes)
            inv.return_value(GLib.Variant("(a(ia{sv}))", ([(i, self.item_props(self.nodes[i])) for i in ids if i in self.nodes],)))
        elif method == "GetProperty":
            i, name = params.unpack()
            props = self.item_props(self.nodes[i]) if i in self.nodes else {}
            inv.return_value(GLib.Variant("(v)", (props.get(name, GLib.Variant("s", "")),)))
        elif method == "Event":
            i, event = params.unpack()[:2]
            if event == "clicked":
                self.activate(i)
            inv.return_value(None)
        elif method == "EventGroup":
            for i, event, _, _ in params.unpack()[0]:
                if event == "clicked":
                    self.activate(i)
            inv.return_value(GLib.Variant("(ai)", ([],)))
        elif method == "AboutToShow":
            self.refresh()  # keep countdowns current when the menu opens (throttled)
            inv.return_value(GLib.Variant("(b)", (False,)))
        elif method == "AboutToShowGroup":
            inv.return_value(GLib.Variant("(aiai)", ([], [])))
        else:
            inv.return_value(None)

    def activate(self, i):
        action = self.nodes.get(i, {}).get("action")
        if action:
            action()

    def rebuild(self):
        self.nodes = self.build_nodes()
        self.layout_rev += 1
        self.emit(self.MENU_PATH, "com.canonical.dbusmenu", "LayoutUpdated", GLib.Variant("(ui)", (self.layout_rev, 0)))

    # -- refresh --
    def refresh(self, force=False):
        if not force and time.time() - self.last_fetch < 15:
            return
        self.last_fetch = time.time()
        threading.Thread(target=lambda: GLib.idle_add(self.apply, *fetch_usage()), daemon=True).start()

    def apply(self, data, err):
        view = build_view(data, err, self.settings["interval"])
        self.error = view.error
        self.label, self.tooltip, rows = view.label, view.tooltip, view.rows
        self.icon = render_icon(view.session, view.weekly)
        self.rows = rows
        self.rebuild()
        for sig in ("NewIcon", "NewToolTip"):
            self.emit(self.SNI_PATH, "org.kde.StatusNotifierItem", sig)
        self.emit(self.SNI_PATH, "org.kde.StatusNotifierItem", "XAyatanaNewLabel",
                  GLib.Variant("(ss)", (self.label, "100% · 100%")))
        return False
