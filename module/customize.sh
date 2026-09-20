SKIPUNZIP=0
ui_print "- Universal Debloat: editable hide list"
ui_print "- cleaning up extra files"
rm -rf "$MODPATH/META-INF" 2>/dev/null
set_perm_recursive "$MODPATH" 0 0 0755 0644
set_perm "$MODPATH/service.sh"      0 0 0755
set_perm "$MODPATH/post-fs-data.sh" 0 0 0755
set_perm "$MODPATH/uninstall.sh"    0 0 0755

# keep an existing user-edited override, otherwise seed it with defaults
if [ -f /data/adb/debloat_list.conf ]; then
  ui_print "- keeping your /data/adb/debloat_list.conf"
else
  cp -f "$MODPATH/hide_list.txt" /data/adb/debloat_list.conf 2>/dev/null
  chmod 644 /data/adb/debloat_list.conf 2>/dev/null
  ui_print "- default list copied to /data/adb/debloat_list.conf"
fi

# clean-ROM mode marker (optional file inside the module zip)
if [ -f "$MODPATH/cleanrom" ]; then
  touch /data/adb/debloat_cleanrom
  chmod 644 /data/adb/debloat_cleanrom
  ui_print "- clean ROM mode enabled: setup wizard will be skipped"
fi

ui_print "- installed. Reboot to apply."
ui_print "- Deleting the module restores the apps."
