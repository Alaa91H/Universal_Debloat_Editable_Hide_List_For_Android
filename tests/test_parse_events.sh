#!/bin/sh
# Host-side test for the evdev parser used by the recovery installer.
# Extracts the parse_events awk program from META-INF update-binary and runs
# it against synthetic input_event streams for both 64-bit and 32-bit timeval
# layouts. Usage: sh tests/test_parse_events.sh
set -e
cd "$(dirname "$0")/.."

UB=META-INF/com/google/android/update-binary

# carve the awk program out of the installer (between the awk quote markers)
awk_prog=$(sed -n "/od -An -v -tx1/,/head -n 1/p" "$UB" | sed '1d;$d' | sed "\$d")

run_case() {
  desc="$1"; file="$2"; expected="$3"
  got=$(od -An -v -tx1 "$file" | tr -s ' \n' ' ' | awk "$awk_prog")
  if [ "$got" = "$expected" ]; then
    echo "PASS: $desc -> $got"
  else
    echo "FAIL: $desc -> expected '$expected', got '$got'"
    exit 1
  fi
}

# 64-bit timeval records are 24 bytes: 16B timeval + type/code/value.
TV64='\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'

#   press Vol-  (code 0x72 = 114)
printf "${TV64}\x01\x00\x72\x00\x01\x00\x00\x00" > /tmp/t1.bin
run_case "64-bit press VOLDOWN" /tmp/t1.bin down

#   press Vol+  (code 0x73 = 115)
printf "${TV64}\x01\x00\x73\x00\x01\x00\x00\x00" > /tmp/t2.bin
run_case "64-bit press VOLUP" /tmp/t2.bin up

#   release Vol- (value 0) must be ignored
printf "${TV64}\x01\x00\x72\x00\x00\x00\x00\x00" > /tmp/t3.bin
run_case "64-bit release ignored" /tmp/t3.bin ""

#   press Power (code 0x74 = 116)
printf "${TV64}\x01\x00\x74\x00\x01\x00\x00\x00" > /tmp/t4.bin
run_case "64-bit press POWER" /tmp/t4.bin power

#   non-key event (type 3 = EV_ABS) must be ignored
printf "${TV64}\x03\x00\x73\x00\x01\x00\x00\x00" > /tmp/t5.bin
run_case "64-bit EV_ABS ignored" /tmp/t5.bin ""

#   release-then-press sequence -> the press wins
printf "${TV64}\x01\x00\x72\x00\x00\x00\x00\x00${TV64}\x01\x00\x73\x00\x01\x00\x00\x00" > /tmp/t6.bin
run_case "64-bit release-then-press" /tmp/t6.bin up

#   three presses in sequence (down, up, power) -> first press wins
printf "${TV64}\x01\x00\x72\x00\x01\x00\x00\x00${TV64}\x01\x00\x73\x00\x01\x00\x00\x00${TV64}\x01\x00\x74\x00\x01\x00\x00\x00" > /tmp/t6b.bin
run_case "64-bit sequence first-wins" /tmp/t6b.bin down

# 32-bit timeval records are 16 bytes: 8B timeval + type/code/value.
TV32='\x00\x00\x00\x00\x00\x00\x00\x00'

#   press Vol+
printf "${TV32}\x01\x00\x73\x00\x01\x00\x00\x00" > /tmp/t7.bin
run_case "32-bit press VOLUP" /tmp/t7.bin up

#   press Power
printf "${TV32}\x01\x00\x74\x00\x01\x00\x00\x00" > /tmp/t8.bin
run_case "32-bit press POWER" /tmp/t8.bin power

#   press Vol-
printf "${TV32}\x01\x00\x72\x00\x01\x00\x00\x00" > /tmp/t9.bin
run_case "32-bit press VOLDOWN" /tmp/t9.bin down

echo "all parser tests passed"
