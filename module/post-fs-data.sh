#!/system/bin/sh
# Universal Debloat - early boot phase (before PackageManager scan).
# Resolves each listed package to its APK path using the persisted package
# database (/data/system/packages.xml), then bind-mounts an empty file over
# the system APK so the package disappears from the scan.
# Only applies in "@mode=uninstall". In "@mode=disable" nothing is mounted.
MODDIR=${0%/*}
LOG="$MODDIR/debloat.log"
BLANK="$MODDIR/blank.apk"
CONF=/data/adb/debloat_list.conf
PXML=/data/system/packages.xml

log() { echo "$(date '+%Y-%m-%d %H:%M:%S') [post-fs-data] $*" >> "$LOG"; }

get_list() {
  if [ -f "$CONF" ]; then
    cat "$CONF"
  elif [ -f "$MODDIR/hide_list.txt" ]; then
    cat "$MODDIR/hide_list.txt"
  fi
}

is_mounted() { grep -qs " $1 " /proc/mounts; }

in_keep() {
  for k in $KEEP; do
    [ "$k" = "$1" ] && return 0
  done
  return 1
}

hide_pkg() {
  pkg="$1"
  line=$(grep -m1 "name=\"$pkg\"" "$PXML" 2>/dev/null)
  [ -n "$line" ] || { log "no packages.xml entry (first boot after flash?): $pkg"; return 0; }
  path=$(printf '%s' "$line" | sed -n 's/.*codePath="\([^"]*\)".*/\1/p')
  [ -n "$path" ] || { log "no codePath for: $pkg"; return 0; }
  [ -d "$path" ] && path="$path/base.apk"
  case "$path" in
    *.apk) ;;
    *) log "not an apk path: $pkg -> $path"; return 0 ;;
  esac
  # only hide copies on read-only system partitions
  case "$path" in
    /system/*|/system_ext/*|/product/*|/vendor/*|/odm/*|/apex/*) ;;
    *) return 0 ;;
  esac
  [ -f "$path" ] || { log "apk not found: $path"; return 0; }
  is_mounted "$path" && return 0
  if [ -f "$BLANK" ] && mount -o bind "$BLANK" "$path" 2>>"$LOG"; then
    log "mounted blank over: $pkg -> $path"
  else
    log "WARNING: mount failed: $pkg -> $path"
  fi
}

# ---- parse the editable list ----
MODE=uninstall
HIDE=""
KEEP=""
while IFS= read -r line; do
  case "$line" in
    ''|\#*) continue ;;
  esac
  line=$(printf '%s' "$line" | tr -d ' \t\r')
  [ -n "$line" ] || continue
  case "$line" in
    '@mode='*) MODE=${line#@mode=} ;;
    '!'*) KEEP="$KEEP ${line#!}" ;;
    @*) ;;
    *) HIDE="$HIDE $line" ;;
  esac
done <<EOF
$(get_list)
EOF
[ "$MODE" = "disable" ] || MODE=uninstall

log "--- post-fs-data start (mode=$MODE, hide=$(set -- $HIDE; echo $#), keep=$(set -- $KEEP; echo $#)) ---"
if [ "$MODE" = "uninstall" ]; then
  for pkg in $HIDE; do
    in_keep "$pkg" && continue
    hide_pkg "$pkg"
  done
else
  log "disable mode: skipping apk mount-hiding"
fi
log "--- post-fs-data done ---"
