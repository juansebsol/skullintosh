#!/usr/bin/env bash
# Skullintosh hardware inventory for Linux (read-only).
#
# Collects the identifiers needed to configure OpenCore for the NUC6i7KYK: PCI/USB device IDs,
# audio codec, BIOS version, CPU, UEFI boot entries and disk layout. It never writes anywhere
# except the output directory, never changes boot entries, and never mounts or modifies disks.
#
# Usage:
#   scripts/inventory/linux-inventory.sh [OUTPUT_DIR]          # basic, no root needed
#   sudo scripts/inventory/linux-inventory.sh [OUTPUT_DIR]     # adds dmidecode + ACPI tables
#
# Then sanitize before sharing anything:
#   skullintosh report --input OUTPUT_DIR --output inventory-report.md
#
# Raw output stays on this machine. Serial numbers are filtered at the source where possible,
# but treat the raw directory as private.

set -euo pipefail
umask 077

OUT="${1:-inventory-raw-$(date +%Y%m%d-%H%M%S)}"
mkdir -p "$OUT"
IS_ROOT=0
[ "$(id -u)" -eq 0 ] && IS_ROOT=1

# Drop lines that carry serials, UUIDs or asset tags before anything is written.
strip_ids() {
  grep -viE 'serial|uuid|asset tag|sku number' || true
}

run() {
  # run FILE COMMAND... : record a command's output (or why it was skipped).
  local file="$1"
  shift
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "# skipped: $1 not installed" >"$OUT/$file"
    return 0
  fi
  {
    echo "# \$ $*"
    "$@" 2>&1 || echo "# (exit status $?)"
  } >"$OUT/$file"
}

echo "Writing inventory to $OUT"

# --- Platform / firmware -------------------------------------------------------------------
{
  echo "# DMI (from /sys, serial-free)"
  for f in sys_vendor product_name product_version board_vendor board_name board_version \
    bios_vendor bios_version bios_date; do
    [ -r "/sys/class/dmi/id/$f" ] && printf '%s: %s\n' "$f" "$(cat "/sys/class/dmi/id/$f")"
  done
  echo
  echo "# Boot mode"
  if [ -d /sys/firmware/efi ]; then echo "UEFI"; else echo "Legacy BIOS (OpenCore needs UEFI)"; fi
  if command -v mokutil >/dev/null 2>&1; then mokutil --sb-state 2>&1 || true; fi
} >"$OUT/platform.txt"

if [ "$IS_ROOT" -eq 1 ] && command -v dmidecode >/dev/null 2>&1; then
  dmidecode -t bios -t system -t baseboard -t processor -t memory 2>&1 | strip_ids >"$OUT/dmidecode.txt"
else
  echo "# skipped: run as root for dmidecode (serials are filtered out)" >"$OUT/dmidecode.txt"
fi

# --- CPU -----------------------------------------------------------------------------------
{
  grep -m1 -E '^model name' /proc/cpuinfo || true
  awk -F: '/^(cpu family|model|stepping|microcode)[[:space:]]/ && !seen[$1]++ {print}' /proc/cpuinfo
  echo "logical CPUs: $(grep -c ^processor /proc/cpuinfo)"
  grep -m1 -E '^flags' /proc/cpuinfo | tr ' ' '\n' | grep -E '^(avx2|sse4_2|vmx|aes)$' |
    sed 's/^/flag: /' || true
} >"$OUT/cpu.txt"

# --- PCI / USB -----------------------------------------------------------------------------
run pci.txt lspci -nnk
run pci-tree.txt lspci -tvnn
run usb.txt lsusb
run usb-tree.txt lsusb -tv

# --- Audio codec ---------------------------------------------------------------------------
{
  found=0
  for codec in /proc/asound/card*/codec#*; do
    [ -r "$codec" ] || continue
    found=1
    echo "# $codec"
    grep -E '^(Codec|Address|Vendor Id|Subsystem Id|Revision Id|AFG Function Id)' "$codec" || true
    echo
  done
  [ "$found" -eq 1 ] || echo "# no HDA codec information under /proc/asound"
} >"$OUT/audio.txt"

# --- Thunderbolt ---------------------------------------------------------------------------
{
  for dev in /sys/bus/thunderbolt/devices/*; do
    [ -e "$dev" ] || continue
    printf '%s: ' "$(basename "$dev")"
    for attr in vendor_name device_name generation authorized; do
      [ -r "$dev/$attr" ] && printf '%s=%s ' "$attr" "$(cat "$dev/$attr")"
    done
    echo
  done
  if command -v boltctl >/dev/null 2>&1; then
    echo "# boltctl list (uuids are masked by skullintosh report)"
    boltctl list 2>&1 || true
  fi
} >"$OUT/thunderbolt.txt"

# --- Storage and boot entries --------------------------------------------------------------
run disks.txt lsblk -o NAME,SIZE,TYPE,TRAN,FSTYPE,PARTTYPE,PARTLABEL,MODEL,MOUNTPOINT
run efiboot.txt efibootmgr -v

# --- ACPI tables (root only; for SSDT work) ------------------------------------------------
if [ "$IS_ROOT" -eq 1 ] && [ -d /sys/firmware/acpi/tables ]; then
  mkdir -p "$OUT/acpi"
  for table in /sys/firmware/acpi/tables/*; do
    name="$(basename "$table")"
    case "$name" in
      MSDM* | SLIC*) continue ;; # Windows licensing tables: contain product keys
    esac
    [ -f "$table" ] && cp "$table" "$OUT/acpi/$name.aml"
  done
  echo "ACPI tables copied to $OUT/acpi (MSDM/SLIC excluded). Keep them private."
fi

cat >"$OUT/README.txt" <<'EOF'
Raw Skullintosh inventory. PRIVATE: may still contain machine-specific identifiers.
Create a shareable version with:  skullintosh report --input <this dir> --output report.md
Review the report by eye before posting it anywhere. ACPI tables (acpi/) are never included
in the report; share them only if a maintainer asks and you have checked them.
EOF

echo "Done. Next: skullintosh report --input $OUT --output inventory-report.md"
