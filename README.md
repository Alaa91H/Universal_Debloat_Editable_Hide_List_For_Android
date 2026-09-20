# Universal Debloat

[![Build](https://github.com/Alaa91H/Universal_Debloat_Editable_Hide_List_For_Android/actions/workflows/build.yml/badge.svg)](https://github.com/Alaa91H/Universal_Debloat_Editable_Hide_List_For_Android/actions/workflows/build.yml)
[![Release](https://img.shields.io/github/v/release/Alaa91H/Universal_Debloat_Editable_Hide_List_For_Android)](https://github.com/Alaa91H/Universal_Debloat_Editable_Hide_List_For_Android/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

A device-agnostic, ROM-agnostic **KernelSU / Magisk module** that systemlessly
**hides (uninstall) or disables (disable)** unwanted built-in apps on any
rooted Android device. Nothing on read-only partitions is ever modified, and
removing the module restores everything.

- 🧩 **Systemless** — bind-mounts an empty file over the APK or uses a
  per-user uninstall; no system partition is touched.
- 📝 **Editable list** — packages are read from
  `/data/adb/debloat_list.conf`, so you can change the selection at any time
  and simply reboot. The file survives module updates.
- 🗑️ / ⏸️ **Two action modes** — `@mode=uninstall` (package disappears from
  user 0) or `@mode=disable` (package shows as "Disabled" in settings).
- 🌐 **Works everywhere** — package → APK paths are resolved from the
  device's own package database (`/data/system/packages.xml`), so it works on
  any partition layout (`/system`, `/system_ext`, `/product`, `/vendor`,
  `/odm`, `/apex`) on any ROM.
- ⚡ **Optional clean first boot** — add the `cleanrom` marker to skip the
  first-boot setup wizard entirely.
- 🖥️ **Interactive web UI** (optional) — browse every package on the device,
  pick presets (Safe / Default / Maximum / Custom), choose the action mode,
  and build or flash the module straight from the browser. English + Arabic
  included; more languages are easy to add.
- 🔘 **Interactive recovery installer** — when flashed from TWRP/OrangeFox the
  installer shows volume-key menus (language EN/AR, preset,
  uninstall/disable, clean-ROM). The selected option is always visible with
  a `==>` marker that moves on every keypress. Menus have **no time
  limit**: after your first keypress the installer waits indefinitely for
  as long as you need, and never picks an option for you. The language choice is remembered for the next flash. Full touch
  UIs inside recovery (AROMA) are effectively dead on modern devices, so
  volume keys are the portable way. Add a `noask` file inside the zip (or
  build with `--preset`) for a fully silent install.

## Install

1. Download the latest zip from
   [Releases](https://github.com/Alaa91H/Universal_Debloat_Editable_Hide_List_For_Android/releases)
   (or build it yourself: `python build.py`).
2. Flash it from your root manager (**Modules → Install from storage**) or
   from a custom recovery such as TWRP/OrangeFox. The installer detects the
   modules folder automatically (KernelSU, standalone ksud, or Magisk).
3. Reboot.

> Stock LineageOS recovery rejects unsigned zips — use the root manager
> instead.

## The editable list

After the first install the list lives at `/data/adb/debloat_list.conf`:

```
# one package per line; '#' comments
@mode=uninstall          # or @mode=disable
com.example.unwanted.app # apply the selected action
!com.android.nfc         # keep/restore this package
```

Edit the file with any text editor, save, reboot. The bundled
`module/hide_list.txt` is only the seed used on first install.

## Web UI (optional)

```bash
cd webui
python server.py        # requires adb in PATH and the device connected
```

Open <http://127.0.0.1:8765>. The UI reads every package from the connected
device, highlights risky ones, and can build or install the module with one
click. Language switcher (EN/AR) is built in — add a new dictionary to the
`I18N` object in `webui/index.html` to support another language.

## Building

```bash
python build.py                       # interactive zip (menus on recovery)
python build.py --cleanrom            # include the clean-ROM marker
python build.py --preset max          # silent zip with the Maximum preset
python build.py --preset safe --mode disable  # silent + disable mode
python build.py --list mylist.txt     # replace the bundled list
```

CI builds and verifies the zip on every push and attaches it to GitHub
releases automatically.

## Restore

- Delete the module in your root manager, **or**
- prefix a package with `!` in `/data/adb/debloat_list.conf` and reboot, **or**
- run manually: `su -c 'cmd package install-existing <package>'`

## Warning

Do **not** remove critical packages (SystemUI, Settings, keyboard, WebView,
Google Play services, telephony providers…). The bundled list only contains
safe entries, and the web UI blocks risky ones by default. You are responsible
for the packages you add.

## License

[MIT](LICENSE)
