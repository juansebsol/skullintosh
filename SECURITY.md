# Security policy

## Reporting a vulnerability

Please **don't open a public issue** for security problems. Use GitHub's private reporting:
**Security → Report a vulnerability** on this repository. We aim to acknowledge reports within
7 days.

In scope:

* The build tool downloading, extracting or executing something other than the pinned,
  checksum-verified assets (manifest bypass, zip-slip, symlink tricks, URL injection).
* Generated configurations that silently weaken macOS security (SIP, Apple Secure Boot, AMFI,
  DMG loading) or endanger other operating systems (boot-order changes, NVRAM resets that delete
  boot entries, `ScanPolicy` exposing Windows/Linux).
* Leaks of personal identifiers (SMBIOS serials, MAC addresses, product keys) through builds,
  packages, reports or CI logs.
* Scripts under `scripts/` doing anything other than reading, except where documented.

Out of scope: vulnerabilities in OpenCore, kexts or macOS themselves. Report those upstream
(acidanthera, OpenIntelWireless, Apple). Do tell us if a pinned version is affected so we can
update the manifest.

## Security properties Skullintosh maintains

* Downloads come only from GitHub releases of approved owners and must match pinned SHA-256s.
* SIP stays fully enabled (`csr-active-config 00000000`); `SecureBootModel` is `Default`;
  `DmgLoading` is `Signed`. The validator rejects relaxations.
* No SMBIOS identity is ever committed or packaged; personal builds are marked and refused by
  `package`.
* No command writes to EFI partitions, disks or firmware boot variables.

## Known trade-offs (documented, not silent)

* **UEFI Secure Boot must be disabled** in the BIOS to boot OpenCore ([B-061](docs/backlog.md#b-061)).
  This lowers protection against boot-level malware for every OS on the machine. Re-enable it
  when you stop testing ([bios-settings.md](docs/bios-settings.md#rolling-back)).
* `Vault` is `Optional`: the EFI on the USB stick isn't cryptographically sealed. Keep the stick
  physically secure.
* Debug builds write logs to the USB stick that can contain device paths and partition GUIDs.
* Later macOS versions may need OpenCore Legacy Patcher root patches, which require relaxing
  SIP/AMFI. These will never be enabled silently
  ([compatibility.md](docs/compatibility.md#security-reducing-patches)).
