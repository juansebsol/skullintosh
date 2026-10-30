#!/usr/bin/env bash
# Apply the macOS settings a Skullintosh install needs after the first boot.
#
# These live inside macOS, not in the EFI, so the build can't set them. Each one is listed below
# with its reason. The script only changes power-management settings (pmset); it doesn't touch
# disks, EFI partitions or boot entries. Running it again is harmless.
#
# Usage:  sudo bash post-install.sh            apply the settings
#         bash post-install.sh --dry-run       show what would change, change nothing
#
# Undo:   sudo pmset restoredefaults

set -euo pipefail

# pmset key, value, reason. Without these, the reference NUC (Monterey 12.7.6) slept but didn't
# wake (docs/dev/backlog.md B-030).
SETTINGS=(
  "hibernatemode 0 hibernation (writing RAM to disk) doesn't work on non-Apple firmware; sleep stays in RAM"
  "standby 0 stops macOS switching a long sleep into hibernation"
  "autopoweroff 0 like standby: no later switch to a deeper, hibernation-style sleep"
  "powernap 0 no background wake-ups while asleep"
  "proximitywake 0 no wake-ups from nearby Apple devices"
)

DRY_RUN=0
case "${1:-}" in
  "") ;;
  --dry-run) DRY_RUN=1 ;;
  *) echo "Usage: sudo bash $0 [--dry-run]" >&2; exit 2 ;;
esac

if [ "$(uname -s)" != "Darwin" ]; then
  echo "This script runs on the NUC's macOS, not on $(uname -s)." >&2
  exit 1
fi
if [ "$DRY_RUN" -eq 0 ] && [ "$(id -u)" -ne 0 ]; then
  echo "Run with sudo (or use --dry-run to only look)." >&2
  exit 1
fi

current() {
  # Prints the current value of a pmset key, or "unset" if this Mac doesn't report it.
  pmset -g | awk -v key="$1" '$1 == key { print $2; found = 1 } END { if (!found) print "unset" }'
}

echo "Power settings (pmset):"
for entry in "${SETTINGS[@]}"; do
  read -r key value reason <<<"$entry"
  now="$(current "$key")"
  if [ "$now" = "$value" ]; then
    printf '  %-14s %s (already set)\n' "$key" "$value"
  elif [ "$DRY_RUN" -eq 1 ]; then
    printf '  %-14s %s -> %s  would change: %s\n' "$key" "$now" "$value" "$reason"
  else
    pmset -a "$key" "$value"
    printf '  %-14s %s -> %s  %s\n' "$key" "$now" "$value" "$reason"
  fi
done

if [ "$DRY_RUN" -eq 1 ]; then
  echo "Dry run: nothing was changed."
else
  echo "Done. Test with Apple menu -> Sleep, wait 30 s, then press a key."
fi
