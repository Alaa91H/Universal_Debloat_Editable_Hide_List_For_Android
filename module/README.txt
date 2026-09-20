Universal Debloat - editable package list
==========================================

The module reads the package list from /data/adb/debloat_list.conf
(created on first install from this file, and kept across updates).

Rules
-----
  com.example.app    apply the selected action to this package
  !com.example.app   keep / restore this package
  # comment          ignored
  @mode=uninstall    fully hide packages for user 0 (default)
  @mode=disable      disable packages (reversible, visible as "disabled")

After editing, reboot the device.

To restore everything: delete the module from your root manager.

Log for troubleshooting:
  /data/adb/modules/universal_debloat/debloat.log
