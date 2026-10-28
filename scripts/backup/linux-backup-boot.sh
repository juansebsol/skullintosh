#!/usr/bin/env bash
# Back up the current boot environment from Linux before any Skullintosh testing (read-only).
#
# Saves: UEFI boot entries (efibootmgr -v), the partition table of every disk (sfdisk --dump),
# a block-device listing, and a tar archive of the mounted EFI System Partition. It only READS
# disks and boot variables; it writes nothing except the output directory.
#
# Usage:  sudo scripts/backup/linux-backup-boot.sh [OUTPUT_DIR] [ESP_MOUNTPOINT]
#   OUTPUT_DIR      default: ./efi-backup-<timestamp>  (put it on a different disk or a USB stick)
#   ESP_MOUNTPOINT  default: autodetected (/boot/efi or /efi)
#
# Restoring is a manual, deliberate step: see docs/recovery.md.

set -euo pipefail
umask 077

if [ "$(id -u)" -ne 0 ]; then
  echo "Run with sudo: reading partition tables and the ESP needs root." >&2
  exit 1
fi

OUT="${1:-efi-backup-$(date +%Y%m%d-%H%M%S)}"
ESP="${2:-}"
if [ -z "$ESP" ]; then
  for candidate in /boot/efi /efi /boot; do
    if findmnt -n -o FSTYPE "$candidate" 2>/dev/null | grep -qi vfat; then
      ESP="$candidate"
      break
    fi
  done
fi

mkdir -p "$OUT"
echo "Backing up boot environment to $OUT"

efibootmgr -v >"$OUT/efibootmgr-v.txt" 2>&1 || echo "efibootmgr failed" >>"$OUT/errors.txt"
lsblk -o NAME,SIZE,TYPE,TRAN,FSTYPE,PARTTYPE,PARTLABEL,PARTUUID,MODEL,MOUNTPOINT \
  >"$OUT/lsblk.txt"

while read -r disk; do
  name="$(basename "$disk")"
  sfdisk --dump "$disk" >"$OUT/partition-table-$name.sfdisk" 2>>"$OUT/errors.txt" || true
done < <(lsblk -dnpo NAME,TYPE | awk '$2 == "disk" {print $1}')

if [ -n "$ESP" ]; then
  findmnt "$ESP" >"$OUT/esp-mount.txt"
  tar -C "$ESP" -czf "$OUT/esp-$(echo "$ESP" | tr '/' '_').tar.gz" .
  echo "ESP $ESP archived"
else
  echo "No mounted vfat ESP found; pass its mount point as the second argument." |
    tee -a "$OUT/errors.txt"
fi

(cd "$OUT" && sha256sum -- * >SHA256SUMS)
echo "Done. Copy $OUT somewhere that is not on this machine's internal disks."
echo "It contains partition GUIDs: keep it private."
