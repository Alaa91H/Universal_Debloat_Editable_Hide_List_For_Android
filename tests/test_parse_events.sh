#!/bin/sh
# Host-side test for the evdev parser used by the recovery installer.
# Extracts the parse_events awk program from META-INF update-binary and runs
# it against synthetic input_event streams for both 64-bit and 32-bit timeval
# layouts. Uses only POSIX sh + awk: passes under bash, dash, and busybox ash.
# Usage: sh tests/test_parse_events.sh
set -e
cd "$(dirname "$0")/.."

UB=META-INF/com/google/android/update-binary

# carve the awk program out of the installer (between the awk quote markers)
awk_prog=$(sed -n "/od -An -v -tx1/,/head -n 1/p" "$UB" | sed '1d;$d' | sed "\$d")

# make_bin <outfile> <hexstring> — portable binary fixture generator.
# printf "%c", v emits the raw byte for any awk (gawk/mawk/busybox), unlike
# shell printf whose \x escapes are a bashism (dash prints them literally).
make_bin() {
  printf '%s\n' "$2" | awk '{
    for (i = 1; i <= length($0); i += 2) {
      hi = substr($0, i, 1); lo = substr($0, i + 1, 1)
      v = (index("0123456789abcdef", tolower(hi)) - 1) * 16 \
        + (index("0123456789abcdef", tolower(lo)) - 1)
      printf "%c", v
    }
  }' > "$1"
}

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

# 64-bit timeval records are 24 bytes: 16B timeval + type/code/value (8B).
TV64=00000000000000000000000000000000
# 32-bit timeval records are 16 bytes: 8B timeval + type/code/value.
TV32=0000000000000000

#   press Vol-  (type EV_KEY=01, code 0x72=114, value 1 = press)
make_bin /tmp/t1.bin "${TV64}0100720001000000"
run_case "64-bit press VOLDOWN" /tmp/t1.bin down

#   press Vol+  (code 0x73 = 115)
make_bin /tmp/t2.bin "${TV64}0100730001000000"
run_case "64-bit press VOLUP" /tmp/t2.bin up

#   release Vol- (value 0) must be ignored
make_bin /tmp/t3.bin "${TV64}0100720000000000"
run_case "64-bit release ignored" /tmp/t3.bin ""

#   press Power (code 0x74 = 116)
make_bin /tmp/t4.bin "${TV64}0100740001000000"
run_case "64-bit press POWER" /tmp/t4.bin power

#   non-key event (type 3 = EV_ABS) must be ignored
make_bin /tmp/t5.bin "${TV64}0300730001000000"
run_case "64-bit EV_ABS ignored" /tmp/t5.bin ""

#   release-then-press sequence -> the press wins
make_bin /tmp/t6.bin "${TV64}0100720000000000${TV64}0100730001000000"
run_case "64-bit release-then-press" /tmp/t6.bin up

#   three presses in sequence (down, up, power) -> first press wins
make_bin /tmp/t6b.bin "${TV64}0100720001000000${TV64}0100730001000000${TV64}0100740001000000"
run_case "64-bit sequence first-wins" /tmp/t6b.bin down

#   trailing press at the very end of the stream (regression: p+7<=n guard)
make_bin /tmp/t6c.bin "03000000000000000100000000000000${TV64}0100740001000000"
run_case "64-bit trailing press" /tmp/t6c.bin power

#   press Vol+
make_bin /tmp/t7.bin "${TV32}0100730001000000"
run_case "32-bit press VOLUP" /tmp/t7.bin up

#   press Power
make_bin /tmp/t8.bin "${TV32}0100740001000000"
run_case "32-bit press POWER" /tmp/t8.bin power

#   press Vol-
make_bin /tmp/t9.bin "${TV32}0100720001000000"
run_case "32-bit press VOLDOWN" /tmp/t9.bin down

#   garbage padding around a valid press (misaligned stride still found)
make_bin /tmp/t10.bin "ffffffffffffffff0100720001000000"
run_case "32-bit misaligned stride" /tmp/t10.bin down

echo "all parser tests passed"
