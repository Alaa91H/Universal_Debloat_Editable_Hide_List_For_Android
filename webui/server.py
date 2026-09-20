#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Universal Debloat Builder - interactive UI server.
Talks to a phone over ADB, lists ROM packages, and builds/flashes a
KernelSU/Magisk module that systemlessly hides (uninstall mode) or
disables (disable mode) the selected packages.

Run:  python server.py   then open  http://127.0.0.1:8765
"""
import io
import json
import os
import re
import shlex
import subprocess
import tempfile
import threading
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
MODULE_DIR = os.path.join(ROOT, "module")
PRESETS_DIR = os.path.join(ROOT, "presets")
UPDATE_BINARY = os.path.join(ROOT, "META-INF", "com", "google", "android", "update-binary")
UPDATER_SCRIPT = os.path.join(ROOT, "META-INF", "com", "google", "android", "updater-script")
ADB = "adb"
PORT = 8765

MODID = "universal_debloat"
CONF = "/data/adb/debloat_list.conf"
CLEANFLAG = "/data/adb/debloat_cleanrom"

lock = threading.Lock()
last_log = ""

CRITICAL = {
    "android",
    "com.android.settings", "com.android.systemui",
    "com.android.launcher3", "com.google.android.apps.nexuslauncher",
    "com.android.permissioncontroller", "com.google.android.permissioncontroller",
    "com.android.vending", "com.android.chrome",
    "com.android.providers.contacts", "com.android.providers.media",
    "com.android.providers.telephony", "com.android.providers.settings",
    "com.android.phone", "com.android.server.telecom", "com.android.incallui",
    "com.android.dialer", "com.google.android.dialer", "com.android.mms",
    "com.google.android.apps.messaging", "com.android.bluetooth", "com.android.nfc",
    "com.android.networkstack", "com.android.wifi", "com.android.hotword",
    "com.android.inputmethod.latin", "com.google.android.inputmethod.latin",
    "com.google.android.gms", "com.google.android.gsf",
    "com.google.android.webview", "com.android.webview",
    "com.android.documentsui", "com.android.packageinstaller",
    "com.google.android.packageinstaller", "com.android.externalstorage",
    "com.android.storagemanager", "com.android.se", "com.android.ims.rcsmanager",
    "com.android.shell", "com.android.localtransport", "com.android.keychain",
    "com.android.pacprocessor", "com.android.proxyhandler", "com.android.vpndialogs",
    "com.android.companiondevicemanager", "com.android.managedprovisioning",
    "com.google.android.setupwizard", "com.google.android.configupdater",
    "com.google.android.partnersetup", "com.android.networkstack.tethering",
    "com.android.cts.ctsshim", "com.android.emergency",
    "com.android.cellbroadcastreceiver", "com.android.cellbroadcastservice",
    "com.android.settings.intelligence", "com.google.android.settings.intelligence",
    "com.android.connectivity.resources", "com.android.servicepackagemanager",
}
CRITICAL_PATTERNS = re.compile(
    r"(^android$|systemui|launcher|inputmethod|\.webview$|providers\.|ims|rcs|"
    r"telephony|cellbroadcast|networkstack|connectivity|media\.provider|setupwizard|"
    r"packageinstaller|permissions|securitycenter|extservices|extdomains|"
    r"health|thermal|iowatch|storage.?manager$|\.resurrected$)",
    re.I,
)

RISK_META = {
    "com.android.chrome": "browser - some apps open links through it",
    "com.android.deskclock": "system clock - keep an alternative",
    "com.android.calendar": "system calendar - event sync",
    "com.google.android.deskclock": "Google clock",
    "com.google.android.calendar": "Google calendar",
    "com.google.android.gms": "DANGER: breaks most apps",
    "com.google.android.gsf": "DANGER: Google services framework",
    "com.google.android.webview": "DANGER: in-app web rendering",
    "com.google.android.tts": "text-to-speech - used by navigation/a11y",
    "com.google.android.marvin.talkback": "screen reader - needed by visually impaired users",
    "com.google.android.apps.photos": "gallery - keep an alternative",
    "com.google.android.inputmethod.latin": "DANGER: keyboard - only remove with an alternative installed",
}

DESCS = {
    "com.google.android.apps.safetyhub": ("Personal Safety", "emergency alerts"),
    "com.chiller3.bcr": ("Call Recorder (BCR)", "call recording"),
    "com.google.android.apps.recorder": ("Recorder", "voice memos"),
    "com.android.axion.sandbox": ("Sandbox stub", "isolated test env"),
    "com.google.android.accessibility.soundamplifier": ("Sound Amplifier", "accessibility"),
    "com.google.android.accessibility.switchaccess": ("Switch Access", "accessibility"),
    "com.google.android.apps.magicportrait": ("Magic Portrait", "live wallpapers"),
    "com.google.android.glasses.core": ("Glasses core", "AR companion stub"),
    "com.google.android.gms.supervision": ("Kids supervision", "family link"),
    "com.google.android.marvin.talkback": ("TalkBack", "screen reader"),
    "com.google.audio.hearing.visualization.accessibility.scribe": ("Scribe", "accessibility captions"),
    "com.google.android.apps.wellbeing": ("Digital Wellbeing", "screen time"),
    "com.google.android.apps.turbo": ("Device Health", "battery stats"),
    "com.google.android.apps.betterbug": ("Bug reporting", "feedback"),
    "com.google.android.apps.restore": ("Restore", "data transfer"),
    "com.google.android.apps.dreamliner": ("Dock gestures", "accessory stub"),
    "com.google.android.apps.miphone.aiai": ("AI core", "assistant features"),
    "com.google.android.apps.miphone.aiai.echo": ("AI side search", "assistant"),
    "com.google.android.apps.googleassistant": ("Assistant", "voice helper"),
    "com.google.android.googlequicksearchbox": ("Google Search", "search widget"),
    "com.google.android.apps.tachyon": ("Meet/Duo", "video calls"),
    "com.google.android.videos": ("Google TV", "movies"),
    "com.google.android.apps.youtube.music": ("YouTube Music", "music"),
    "com.google.android.apps.magazines": ("Google News", "news"),
    "com.google.android.apps.docs.editors.docs": ("Docs", "documents"),
    "com.google.android.youtube": ("YouTube", "video"),
    "com.google.android.maps": ("Maps", "navigation"),
    "com.google.android.printservice.recommendation": ("Print service", "printing"),
    "com.android.printspooler": ("Print spooler", "printing"),
    "com.google.android.feedback": ("Feedback", "user reports"),
    "com.google.android.onetimeinitializer": ("One-time init", "setup helper"),
    "com.google.android.syncadapters.calendar": ("Calendar sync", "sync adapter"),
}

ALWAYS_KEEP = [
    "com.android.nfc", "com.android.systemui", "com.android.settings",
    "com.android.launcher3", "com.google.android.apps.nexuslauncher",
]


def sh(args, timeout=30):
    try:
        return subprocess.run(args, capture_output=True, text=True, timeout=timeout,
                              encoding="utf-8", errors="replace")
    except FileNotFoundError:
        raise RuntimeError("adb not found in PATH")


def adb(*args, timeout=30):
    return sh([ADB] + list(args), timeout=timeout)


def device_info():
    r = adb("shell", "getprop ro.product.model; getprop ro.product.device; "
            "getprop ro.build.version.release; getprop ro.build.fingerprint")
    lines = [x.strip() for x in r.stdout.splitlines() if x.strip()]
    while len(lines) < 4:
        lines.append("")
    model, device, release, fp = lines[:4]
    rom = "AOSP/GSI"
    for name, marker in (("LineageOS", "lineage"), ("crDroid", "crdroid"),
                         ("Evolution X", "evolution"), ("Pixel", "pixel")):
        if marker in fp.lower():
            rom = name
            break
    return {"connected": bool(model), "model": model, "device": device,
            "android": release, "rom": rom, "fingerprint": fp}


def read_active_conf():
    """Parse the on-device config -> (hide_list, keep_set, mode)."""
    try:
        r = adb("shell", "su -c 'cat %s'" % CONF, timeout=20)
        hide, keep, mode = [], set(), "uninstall"
        for ln in r.stdout.splitlines():
            ln = ln.strip()
            if not ln or ln.startswith("#"):
                continue
            ln = ln.replace(" ", "").replace("\t", "").replace("\r", "")
            if not ln:
                continue
            if ln.startswith("@mode="):
                mode = ln[6:] if ln[6:] in ("uninstall", "disable") else "uninstall"
            elif ln.startswith("!"):
                keep.add(ln[1:])
            else:
                hide.append(ln)
        return hide, keep, mode
    except Exception:
        return [], set(), "uninstall"


def list_packages():
    r = adb("shell", "pm list packages -s", timeout=60)
    pkgs = sorted({ln.strip()[8:] for ln in r.stdout.splitlines()
                   if ln.startswith("package:") and ln.strip()[8:]})
    if not pkgs:
        raise RuntimeError("no device / empty package list")
    r2 = adb("shell", "pm list packages -d", timeout=30)
    disabled = {ln.strip()[8:] for ln in r2.stdout.splitlines() if ln.startswith("package:")}

    out, visible_set = [], set(pkgs)
    for p in pkgs:
        label = DESCS.get(p, (p.rsplit(".", 1)[-1],))[0]
        risk = "critical" if (p in CRITICAL or CRITICAL_PATTERNS.search(p)) else "safe"
        warn = RISK_META.get(p) or (DESCS.get(p, ("", ""))[1] if p in DESCS else "")
        out.append({"package": p, "label": label, "risk": risk, "warn": warn,
                    "presetDisabled": p in disabled, "currentlyHidden": False})

    conf_hide, conf_keep, mode = read_active_conf()
    for p in conf_hide:
        if p in visible_set:
            continue
        label = DESCS.get(p, (p.rsplit(".", 1)[-1],))[0]
        risk = "critical" if (p in CRITICAL or CRITICAL_PATTERNS.search(p)) else "safe"
        warn = RISK_META.get(p) or (DESCS.get(p, ("", ""))[1] if p in DESCS else "")
        out.append({"package": p, "label": label, "risk": risk, "warn": warn,
                    "presetDisabled": False, "currentlyHidden": True})
    out.sort(key=lambda x: x["package"])

    keep_rules = sorted(conf_keep | set(ALWAYS_KEEP))
    return out, keep_rules, mode


def conf_bytes(selected, mode="uninstall"):
    lines = [
        "# =====================================================================",
        "# Universal Debloat - editable package list",
        "# Generated by the web UI. Rules:",
        "#   pkg = apply action, !pkg = keep/restore, # = comment",
        "#   @mode=uninstall | @mode=disable",
        "# =====================================================================",
        "",
        "@mode=%s" % ("disable" if mode == "disable" else "uninstall"),
        "",
    ]
    lines += sorted(selected)
    lines += ["", "# --- always keep (safety) ---"]
    lines += ["!" + p for p in ALWAYS_KEEP]
    return ("\n".join(lines) + "\n").encode("utf-8")


def write_zip(selected, cleanrom=False, mode="uninstall", noask=False):
    buf = io.BytesIO()
    z = zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED)
    files = [
        ("module.prop", "module.prop", 0o644),
        ("service.sh", "service.sh", 0o755),
        ("post-fs-data.sh", "post-fs-data.sh", 0o755),
        ("uninstall.sh", "uninstall.sh", 0o755),
        ("customize.sh", "customize.sh", 0o755),
        ("blank.apk", "blank.apk", 0o644),
        ("README.txt", "README.txt", 0o644),
        ("../presets/safe.txt", "presets/safe.txt", 0o644),
        ("../presets/default.txt", "presets/default.txt", 0o644),
        ("../presets/max.txt", "presets/max.txt", 0o644),
    ]
    for diskname, arcname, fmode in files:
        with open(os.path.join(MODULE_DIR, diskname), "rb") as f:
            data = f.read()
        if not diskname.endswith(".apk"):
            data = data.replace(b"\r\n", b"\n")
        zi = zipfile.ZipInfo(arcname, date_time=(2026, 9, 20, 12, 0, 0))
        zi.external_attr = fmode << 16
        z.writestr(zi, data)

    zi = zipfile.ZipInfo("hide_list.txt", date_time=(2026, 9, 20, 12, 0, 0))
    zi.external_attr = 0o644 << 16
    z.writestr(zi, conf_bytes(selected, mode))

    with open(UPDATE_BINARY, "rb") as f:
        zi = zipfile.ZipInfo("META-INF/com/google/android/update-binary",
                             date_time=(2026, 9, 20, 12, 0, 0))
        zi.external_attr = 0o755 << 16
        z.writestr(zi, f.read().replace(b"\r\n", b"\n"))
    with open(UPDATER_SCRIPT, "rb") as f:
        zi = zipfile.ZipInfo("META-INF/com/google/android/updater-script",
                             date_time=(2026, 9, 20, 12, 0, 0))
        zi.external_attr = 0o644 << 16
        z.writestr(zi, f.read().replace(b"\r\n", b"\n"))
    if cleanrom:
        zi = zipfile.ZipInfo("cleanrom", date_time=(2026, 9, 20, 12, 0, 0))
        zi.external_attr = 0o644 << 16
        z.writestr(zi, b"")
    if noask:
        zi = zipfile.ZipInfo("noask", date_time=(2026, 9, 20, 12, 0, 0))
        zi.external_attr = 0o644 << 16
        z.writestr(zi, b"")
    z.close()
    return buf.getvalue()


def push_bytes(local_tag, data, remote):
    with tempfile.NamedTemporaryFile(suffix=local_tag, delete=False) as tf:
        tf.write(data)
        local = tf.name
    try:
        return subprocess.run([ADB, "push", local, remote],
                              capture_output=True, timeout=60)
    finally:
        os.unlink(local)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def _send(self, code, body, ctype="application/json; charset=utf-8"):
        data = body if isinstance(body, bytes) else json.dumps(body, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _body(self):
        n = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(n).decode("utf-8")) if n else {}

    def do_GET(self):
        global last_log
        try:
            if self.path in ("/", "/index.html"):
                with open(os.path.join(HERE, "index.html"), "rb") as f:
                    return self._send(200, f.read(), "text/html; charset=utf-8")
            if self.path == "/api/status":
                with lock:
                    info = device_info()
                info["log"] = last_log
                return self._send(200, info)
            if self.path == "/api/packages":
                with lock:
                    pkgs, keep_rules, mode = list_packages()
                return self._send(200, {"packages": pkgs, "keepRules": keep_rules,
                                        "currentMode": mode})
            return self._send(404, {"error": "not found"})
        except Exception as e:
            return self._send(500, {"error": str(e)})

    def do_POST(self):
        global last_log
        try:
            req = self._body()
            selected = [p for p in req.get("selected", []) if p]
            cleanrom = bool(req.get("cleanRom"))
            noask = bool(req.get("noAsk"))
            mode = "disable" if req.get("mode") == "disable" else "uninstall"

            if self.path == "/api/build":
                data = write_zip(selected, cleanrom, mode, noask)
                out = os.path.join(HERE, "Universal_Debloat_Custom.zip")
                with open(out, "wb") as f:
                    f.write(data)
                last_log = "built %s (%d packages, mode=%s)" % (out, len(selected), mode)
                return self._send(200, {"ok": True, "count": len(selected),
                                        "file": out, "size": len(data)})

            if self.path == "/api/install":
                if not selected:
                    return self._send(400, {"error": "no packages selected"})
                sel_set = set(selected)
                old_hide, _k, old_mode = read_active_conf()

                # restore packages that are no longer selected
                restored = []
                for pkg in [x for x in old_hide if x not in sel_set]:
                    adb("shell", "su -c 'pm enable %s'" % pkg, timeout=20)
                    rp = adb("shell", "su -c 'cmd package install-existing %s'" % pkg, timeout=20)
                    if "Success" in (rp.stdout or "") or "already installed" in (rp.stdout or ""):
                        restored.append(pkg)

                # switching uninstall -> disable: the pkgs must exist first
                if mode == "disable":
                    for pkg in selected:
                        adb("shell", "su -c 'cmd package install-existing %s'" % pkg, timeout=20)

                data = write_zip(selected, cleanrom, mode, noask)
                last_log = "installing module (%d packages, mode=%s)..." % (len(selected), mode)

                p = push_bytes(".zip", data, "/data/local/tmp/debloat_custom.zip")
                if p.returncode != 0:
                    return self._send(500, {"error": "push failed: " + p.stderr.decode(errors="replace")})
                p = push_bytes(".txt", conf_bytes(selected, mode),
                               "/data/local/tmp/debloat_newconf.txt")
                if p.returncode != 0:
                    return self._send(500, {"error": "conf push failed"})

                cmds = (
                    "rm -rf /data/adb/modules/%s && "
                    "unzip -o /data/local/tmp/debloat_custom.zip -d "
                    "/data/adb/modules/%s >/dev/null && "
                    "chmod 644 /data/adb/modules/%s/module.prop "
                    "/data/adb/modules/%s/blank.apk "
                    "/data/adb/modules/%s/customize.sh "
                    "/data/adb/modules/%s/hide_list.txt "
                    "/data/adb/modules/%s/README.txt && "
                    "chmod 755 /data/adb/modules/%s/*.sh && "
                    "chown -R 0:0 /data/adb/modules/%s && "
                    "restorecon -R /data/adb/modules/%s 2>/dev/null && "
                    "cp -f /data/local/tmp/debloat_newconf.txt %s && "
                    "chmod 644 %s && "
                    % (MODID, MODID, MODID, MODID, MODID, MODID, MODID, MODID, MODID, MODID, CONF, CONF)
                )
                if cleanrom:
                    cmds += "touch %s && chmod 644 %s && " % (CLEANFLAG, CLEANFLAG)
                else:
                    cmds += "rm -f %s && " % CLEANFLAG
                cmds += "echo INSTALL_OK"
                # /data/adb/modules/NOASK is a marker read by nothing here;
                # direct install via ADB is already non-interactive.

                p = adb("shell", "su -c " + shlex.quote(cmds), timeout=60)
                if "INSTALL_OK" not in p.stdout:
                    return self._send(500, {"error": "install failed: " + (p.stdout + p.stderr)})

                last_log = "module installed. applying action now..."
                p = adb("shell", "su -c 'SKIP_DELAY=1 sh /data/adb/modules/%s/service.sh'" % MODID,
                        timeout=240)
                last_log = (p.stdout or "").strip() or "service done"
                return self._send(200, {"ok": True, "count": len(selected),
                                        "restored": restored, "log": p.stdout[-4000:]})

            if self.path == "/api/reboot":
                adb("shell", "reboot")
                last_log = "rebooting device..."
                return self._send(200, {"ok": True})

            if self.path == "/api/verify":
                if mode == "disable":
                    r = adb("shell", "pm list packages -d", timeout=30)
                else:
                    r = adb("shell", "pm list packages", timeout=30)
                listed = {ln.strip()[8:] for ln in r.stdout.splitlines()
                          if ln.startswith("package:")}
                if mode == "disable":
                    still = [p for p in selected if p not in listed]
                else:
                    still = [p for p in selected if p in listed]
                return self._send(200, {"visible": still,
                                        "hidden": len(selected) - len(still)})

            return self._send(404, {"error": "not found"})
        except Exception as e:
            return self._send(500, {"error": str(e)})


def main():
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print("Universal Debloat Builder running at http://127.0.0.1:%d" % PORT)
    srv.serve_forever()


if __name__ == "__main__":
    main()
