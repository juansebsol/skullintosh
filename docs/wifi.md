# Wi-Fi

The NUC's Intel Wireless-AC 8260 has no macOS driver. Skullintosh can add one from
[OpenIntelWireless](https://github.com/OpenIntelWireless/itlwm), chosen with the `wifi` build
option. The driver lives in the EFI folder, not in macOS, so adding or removing it never needs a
reinstall.

| `--set wifi=` | What you get | macOS versions |
| --- | --- | --- |
| `none` (default) | No Wi-Fi; Ethernet only | all |
| `airportitlwm` | Native Wi-Fi menu and settings, like a real Mac | 12 Monterey, 13 Ventura, 14.4+ Sonoma (each profile uses the file built for its version; Sonoma 14.0–14.3 needs `airportitlwm140`) |
| `itlwm` | Wi-Fi through the separate [HeliPort](https://github.com/OpenIntelWireless/HeliPort) app | all, including 15 Sequoia; untested on 26 Tahoe |

Use `airportitlwm` where it exists. The two can't be combined; the validator refuses it.

**Status:** with `airportitlwm` on Monterey 12.7.6, the reference NUC joined a network and stayed
connected (2026-10-29). 5 GHz throughput and reconnecting after sleep are untested
([hardware-testing.md](hardware-testing.md), T-WIFI-1/2).

## Adding Wi-Fi to an installed system

1. On the Mac, build with Wi-Fi:

   ```bash
   skullintosh build --target monterey --flavor debug --set wifi=airportitlwm
   ```

2. Follow [Updating the EFI later](installation.md#updating-the-efi-later): put the new EFI on
   the stick, test it with F10 → `UEFI : USB` → `Macintosh HD`, then copy it to the disk.

When it works, the Wi-Fi icon appears in the menu bar after booting.

## If Wi-Fi doesn't appear

On the NUC:

```bash
kmutil showloaded 2>/dev/null | grep -i itlwm
system_profiler SPAirPortDataType | head -20
```

* **No `itlwm` line:** the driver didn't load. Check that the EFI you booted contains
  `EFI/OC/Kexts/AirportItlwm.kext` (or `itlwm.kext`), and that you booted the EFI you think you
  did: the stick's and the disk's can differ.
* **Driver loaded, no networks:** the card may be disabled in the BIOS
  (F2 → Devices → Onboard Devices → Wi-Fi).

Open a Boot failure or Hardware regression issue with the output if neither explains it.
