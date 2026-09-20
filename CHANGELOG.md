# Changelog

All notable changes to this project are documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [3.2.0] - 2026-09-20

### Removed
- **All Arabic language support.** The project is now English-only and
  stays that way.
  - Recovery installer: the language menu is gone, so flashing starts
    directly with the preset menu; all installer messages are English.
    The legacy `/data/adb/debloat_lang` file is no longer read or written.
  - Web UI: the Arabic translation table, the language switcher button,
    RTL handling, and all inline bilingual ternaries are removed. The UI
    is served in English only.

## [3.1.2] - 2026-09-20

### Changed
- **Menus no longer time out.** There is no countdown anywhere in the
  recovery installer: every menu waits for you to press Power, however
  long that takes. The previous 15 s idle default (which could confirm an
  option while you were still reading) is gone.
- Wait policy replaced by a first-contact probe: each menu gives an
  unattended flash up to 10 s to press a first key. Once one keypress is
  detected the user is considered interactive and all further waits are
  unlimited - the installer can never pick an option for them again.
  Unattended flashes (CI, automated testing) still proceed automatically
  with the preselected defaults.
- Hint lines updated in both languages (`- no time limit` /
  `- بدون أي مهلة زمنية`).

## [3.1.1] - 2026-09-20

### Fixed
- **Menus are no longer static.** The selected option is always shown
  prefixed with `==>` and the whole menu is re-printed after every
  keypress, so the current choice is visible at all times and each key
  press gives immediate feedback.
- **Key reader never detected anything** on a real device: the previous
  reader piped a single `timeout tail -n1 /dev/input/eventX` whose output
  was consumed inside a subshell that never printed, so every menu silently
  fell back to its default. The reader now captures all input devices in
  parallel into a file for a fixed window, then parses the captured bytes.
- **Event parser missed the captured record** (off-by-one): the scan guard
  `p + 8 <= n` skipped the final record of the stream, which is exactly
  where a single keypress sits. The guard is now `p + 7 <= n`.
- Parser no longer requires `strtonum`, which is missing from mawk and
  some busybox builds: key codes are compared directly in hex
  (`0072`=Vol-, `0073`=Vol+, `0074`=Power).

### Changed
- Per-menu timeout raised from 4 s to **15 s of keyboard inactivity**, and
  the countdown is effectively per-menu rather than per-opening because
  every keypress starts a fresh capture window.
- Menus now announce the default that will be applied on idle expiry, and
  print a confirmation line (`-> confirmed: ...` / `-> تم اعتماد: ...`)
  after each choice so the flow is readable end-to-end.
- If no input device can be opened, menus fall back after 5 s instead of
  idling for the full timeout.

### Added
- `tests/test_parse_events.sh`: host-side regression tests for the evdev
  parser covering both 24-byte (64-bit timeval) and 16-byte (32-bit
  timeval) event layouts, press vs release, non-key events, and
  multi-press sequences.

## [3.1.0] - 2026-09-20

### Added
- **Bilingual installer**: a language menu (English / العربية) is shown first
  in recovery and every subsequent prompt renders in the chosen language;
  the choice is persisted to `/data/adb/debloat_lang` and preselected on the
  next flash. (Recovery console fonts without Arabic glyphs may show boxes,
  but the selection is still applied.)
- **Interactive recovery installer**: when flashed from TWRP/OrangeFox, the
  installer presents volume-key menus — (0) language, (1) preset: Safe /
  Default / Maximum / keep current config, (2) action: uninstall / disable,
  (3) clean-ROM mode — each with a timeout fallback so the install never
  hangs on recoveries that cannot deliver key events.
- Silent-install escape hatches: a `noask` marker file inside the zip skips
  all menus, and `build.py --preset {safe|default|max} [--mode
  {uninstall|disable}]` bakes the choices in at build time (the choice is
  also honoured from the zip filename, e.g. `...preset-default...`).
- Bundled preset lists (`presets/safe.txt`, `presets/default.txt`,
  `presets/max.txt`) shipped inside the flashable zip and used by both the
  recovery menus and the build script.

### Changed
- Default non-interactive action is now **uninstall** (previously disable)
  so a fully unattended flash matches the module's primary purpose.
- Web UI gained a "Silent install" toggle that embeds the `noask` marker.

### Fixed
- Preset lists did not carry the `@mode=` directive, causing `--mode` to be
  ignored when building from a preset.

## [3.0.0] - 2026-09-20

### Added
- Device- and ROM-agnostic architecture: package-to-APK paths are resolved
  from `/data/system/packages.xml` at boot, so no device, partition layout,
  or ROM is hardcoded anywhere.
- **Action modes**: `@mode=uninstall` (fully hide the package for user 0 with
  a blank-mount fallback) and `@mode=disable` (`pm disable-user`, reversible
  and visible in system settings). Configurable per list, editable on device.
- Editable on-device config `/data/adb/debloat_list.conf` with rules:
  package = apply action, `!package` = keep/restore, `#` = comment,
  `@mode=` = action mode. The file survives module updates.
- Optional **clean-ROM mode**: a `cleanrom` marker inside the module zip makes
  the first boot skip the setup wizard (sets `user_setup_complete` and
  `device_provisioned`), landing directly on the home screen.
- **Interactive web UI** (`webui/`): lists every package on the connected
  device, highlights critical ones, offers Safe / Default / Maximum / Custom
  presets, action-mode selection, search and filters, one-click build and
  one-click flash+apply over ADB, and a verification button.
- **Bilingual interface (English / Arabic)** with a runtime language
  switcher, full RTL support, and an extensible i18n dictionary designed for
  adding more languages.
- Automatic restore of deselected packages when re-installing with a smaller
  selection.
- GitHub Actions CI: shell/python syntax checks, `module.prop` validation,
  reproducible zip build with integrity assertions, artifact upload, and
  automatic release attachment on version tags.

### Changed
- Neutral naming across the whole project (module id, paths, docs) — no
  device, vendor, or ROM is referenced.
- Installer (`META-INF` `update-binary`) detects the modules directory across
  official KernelSU (`/data/adb/ksu/modules`), standalone ksud
  (`/data/adb/modules`), and Magisk (`/data/adb/magisk`).
- Documentation rewritten in English with a versioned changelog.

### Removed
- All device- and ROM-specific defaults from the module scripts.

[3.2.0]: https://github.com/Alaa91H/Universal_Debloat_Editable_Hide_List_For_Android/releases/tag/v3.2.0
[3.1.2]: https://github.com/Alaa91H/Universal_Debloat_Editable_Hide_List_For_Android/releases/tag/v3.1.2
[3.1.1]: https://github.com/Alaa91H/Universal_Debloat_Editable_Hide_List_For_Android/releases/tag/v3.1.1
[3.1.0]: https://github.com/Alaa91H/Universal_Debloat_Editable_Hide_List_For_Android/releases/tag/v3.1.0
[3.0.0]: https://github.com/Alaa91H/Universal_Debloat_Editable_Hide_List_For_Android/releases/tag/v3.0.0
