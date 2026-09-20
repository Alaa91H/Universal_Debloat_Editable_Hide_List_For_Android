#!/system/bin/sh
# Universal Debloat - restore every listed package when the module is removed.
# Covers both action modes: enable (disable mode) and install-existing
# (uninstall mode). Both calls are idempotent and safe to always run.
MODDIR=${0%/*}
CONF=/data/adb/debloat_list.conf

LIST="$MODDIR/hide_list.txt"
[ -f "$CONF" ] && LIST="$CONF"
[ -f "$LIST" ] || exit 0

# strip comments/blank lines, "@" directives and the leading "!" from keep rules
PKGS=$(grep -vE '^[[:space:]]*(#|@|$)' "$LIST" | sed 's/^[[:space:]]*![[:space:]]*//' | tr -d ' \t\r' | sort -u)

for pkg in $PKGS; do
  [ -n "$pkg" ] || continue
  /system/bin/pm enable "$pkg" >/dev/null 2>&1
  /system/bin/cmd package install-existing "$pkg" >/dev/null 2>&1
done
