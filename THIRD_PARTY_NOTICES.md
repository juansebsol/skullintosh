# Third-party notices

Skullintosh's own code and documentation are MIT-licensed ([LICENSE](LICENSE)). The repository
contains **no third-party binaries**. Built EFI folders and release packages contain unmodified
binaries downloaded from the official GitHub releases below, pinned by SHA-256 in
[`manifests/dependencies.toml`](manifests/dependencies.toml). Each package's license text, taken
from the pinned tag, is in [`licenses/`](licenses/) and is copied into every release package.

| Component | Upstream | Pinned tag | License | License text |
| --- | --- | --- | --- | --- |
| OpenCore (bootloader, drivers, tools, sample ACPI tables, `ocvalidate`) | [acidanthera/OpenCorePkg](https://github.com/acidanthera/OpenCorePkg) | 1.0.8 | BSD-3-Clause | [licenses/opencore.txt](licenses/opencore.txt) |
| Lilu | [acidanthera/Lilu](https://github.com/acidanthera/Lilu) | 1.7.2 | BSD-3-Clause | [licenses/lilu.txt](licenses/lilu.txt) |
| WhateverGreen | [acidanthera/WhateverGreen](https://github.com/acidanthera/WhateverGreen) | 1.7.1 | BSD-3-Clause | [licenses/whatevergreen.txt](licenses/whatevergreen.txt) |
| AppleALC | [acidanthera/AppleALC](https://github.com/acidanthera/AppleALC) | 1.9.8 | BSD-3-Clause | [licenses/applealc.txt](licenses/applealc.txt) |
| VirtualSMC, SMCProcessor | [acidanthera/VirtualSMC](https://github.com/acidanthera/VirtualSMC) | 1.3.8 | BSD-3-Clause | [licenses/virtualsmc.txt](licenses/virtualsmc.txt) |
| IntelMausi | [acidanthera/IntelMausi](https://github.com/acidanthera/IntelMausi) | 1.0.8 | GPL-2.0 | [licenses/intelmausi.txt](licenses/intelmausi.txt) |
| NVMeFix (optional) | [acidanthera/NVMeFix](https://github.com/acidanthera/NVMeFix) | 1.1.3 | BSD-3-Clause and GPL-2.0-only (includes Linux code) | [licenses/nvmefix.txt](licenses/nvmefix.txt) |
| BlueToolFixup (from BrcmPatchRAM) | [acidanthera/BrcmPatchRAM](https://github.com/acidanthera/BrcmPatchRAM) | 2.7.2 | GPL-2.0 | [licenses/brcmpatchram.txt](licenses/brcmpatchram.txt) |
| IntelBluetoothFirmware, IntelBTPatcher | [OpenIntelWireless/IntelBluetoothFirmware](https://github.com/OpenIntelWireless/IntelBluetoothFirmware) | v2.4.0 | GPL-3.0 | [licenses/intelbluetooth.txt](licenses/intelbluetooth.txt) |
| itlwm, AirportItlwm (optional) | [OpenIntelWireless/itlwm](https://github.com/OpenIntelWireless/itlwm) | v2.3.0 | GPL-2.0 | [licenses/itlwm.txt](licenses/itlwm.txt) |

## GPL components

IntelMausi, BlueToolFixup, IntelBluetoothFirmware/IntelBTPatcher, itlwm/AirportItlwm and parts
of NVMeFix are GPL-licensed. Skullintosh redistributes the upstream release binaries
**unmodified**. The complete corresponding source for each is the upstream repository at the
tag listed above (also recorded per build in `provenance.json`). If those repositories ever stop
being available, open an issue and the maintainers will supply the source for any binary that
Skullintosh has distributed.

## Derived data

* `hardware/usb/nuc6i7kyb.toml` and the NUC6i7KYK device-property values in
  `profiles/monterey/config-overlay.plist` are derived from
  [alexpotter1/intel-nuc6i7kyk-opencore](https://github.com/alexpotter1/intel-nuc6i7kyk-opencore)
  (MIT, © 2020 Alex Potter). Attribution is kept in [LICENSE](LICENSE).
* The OpenCore `Sample.plist`, from the pinned OpenCore release, is the base every generated
  `config.plist` starts from (BSD-3-Clause).

## Not included

* **No Apple software**: no macOS installers, recovery images, `HfsPlus.efi`, firmware, icons
  or other Apple files. OpenCore's open-source `OpenHfsPlus.efi` is used instead of Apple's HFS+
  driver.
* macOS is licensed by Apple for use on Apple-branded hardware. Installing it on other
  hardware may breach Apple's Software License Agreement for macOS. Users are responsible for
  their own compliance; Skullintosh exists for research, education and interoperability work.
