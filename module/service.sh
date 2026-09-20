#!/system/bin/sh
# Universal Debloat - late boot service.
# Applies the configured action mode to every listed package:
#   @mode=uninstall  per-user uninstall of the system copy (+ data copies),
#                    with a blank-mount fallback                       [default]
#   @mode=disable    disable packages for user 0 (reversible, visible
#                    as "disabled" in system settings)
# Packages prefixed with "!" are restored instead.
MODDIR=${0%/*}
LOG="$MODDIR/debloat.log"
BLANK="$MODDIR/blank.apk"
CONF=/data/adb/debloat_list.conf
CLEANFLAG=/data/adb/debloat_cleanrom
PM=/system/bin/pm

log() { echo "$(date '+%Y-%m-%d %H:%M:%S') [service] $*" >> "$LOG"; }

get_list() {
  if [ -f "$CONF" ]; then
    cat "$CONF"
  elif [ -f "$MODDIR/hide_list.txt" ]; then
    cat "$MODDIR/hide_list.txt"
  fi
}

in_keep() {
  for k in $KEEP; do
    [ "$k" = "$1" ] && return 0
  done
  return 1
}

is_mounted() { grep -qs " $1 " /proc/mounts; }

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

log "--- boot service start (mode=$MODE, hide=$(set -- $HIDE; echo $#), keep=$(set -- $KEEP; echo $#)) ---"

# Wait for boot to complete (max ~3 min)
i=0
while [ "$(getprop sys.boot_completed)" != "1" ] && [ "$i" -lt 90 ]; do
  sleep 2
  i=$((i+1))
done
# Give PackageManager a moment to finish its scan
sleep 20

# ---- clean-ROM mode: finish provisioning so the home screen opens directly ----
if [ -f "$CLEANFLAG" ]; then
  S=/system/bin/settings
  $S put secure user_setup_complete 1 >/dev/null 2>&1
  $S put global device_provisioned 1 >/dev/null 2>&1
  $S put secure user_setup_complete_necessary 0 >/dev/null 2>&1
  log "clean-rom: provisioning flags applied"
fi

uninstall_pkg() {
  pkg="$1"
  # 1) remove any user-installed / updated copy (runs as root)
  $PM uninstall "$pkg" >/dev/null 2>&1 && log "removed data copy: $pkg"
  # 2) hide the system copy for user 0
  $PM uninstall --user 0 "$pkg" >/dev/null 2>&1 && log "hidden for user 0: $pkg"
  # 3) fallback: still visible? bind-mount an empty file over its apk
  apk=$($PM path "$pkg" 2>/dev/null | sed -n 's/^package://p' | head -n 1)
  if [ -n "$apk" ]; then
    case "$apk" in
      /data/*)
        $PM uninstall --user 0 "$pkg" >/dev/null 2>&1
        apk=$($PM path "$pkg" 2>/dev/null | sed -n 's/^package://p' | head -n 1)
        ;;
    esac
  fi
  if [ -n "$apk" ]; then
    if [ -f "$BLANK" ] && ! is_mounted "$apk" && mount -o bind "$BLANK" "$apk" 2>>"$LOG"; then
      log "bind-mounted blank over: $apk"
    elif is_mounted "$apk"; then
      log "already mounted: $apk"
    else
      log "WARNING: could not hide $pkg ($apk)"
    fi
  else
    log "gone: $pkg"
  fi
}

disable_pkg() {
  pkg="$1"
  # make sure the system copy exists for the user, then disable it
  /system/bin/cmd package install-existing "$pkg" >/dev/null 2>&1
  if $PM disable-user --user 0 "$pkg" >/dev/null 2>&1; then
    log "disabled: $pkg"
  else
    log "WARNING: disable failed: $pkg"
  fi
}

for pkg in $HIDE; do
  in_keep "$pkg" && continue
  if [ "$MODE" = "disable" ]; then
    disable_pkg "$pkg"
  else
    uninstall_pkg "$pkg"
  fi
done

# packages marked with "!" are restored
for pkg in $KEEP; do
  if [ "$MODE" = "disable" ]; then
    $PM enable "$pkg" >/dev/null 2>&1 && log "kept/enabled: $pkg"
  fi
  if ! $PM path "$pkg" >/dev/null 2>&1; then
    /system/bin/cmd package install-existing "$pkg" >/dev/null 2>&1 && log "restored by ! rule: $pkg"
  else
    log "kept: $pkg"
  fi
done

log "--- boot service done ---"
