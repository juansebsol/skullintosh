# Contributing to Skullintosh

Thanks for helping keep the Skull Canyon alive. The most valuable contributions are **hardware
test reports** from real NUC6i7KYK owners, and they need no coding.

## Ground rules

1. **Evidence over claims.** A feature is "working" only with a test report that names the build
   (`provenance.json` tree digest) and the steps run ([docs/hardware-testing.md](docs/hardware-testing.md)).
   CI passing is not evidence.
2. **One change at a time.** Configuration changes need a reason (source link or measurement)
   and, for hardware behaviour, a before/after test.
3. **No unexplained patches.** No ACPI binary patches, kernel patches or device properties
   copied from another machine without an explanation of what they do and why they apply to
   this board. Other NUC models' USB maps and Thunderbolt patches don't transfer.
4. **Protect other OSes.** Nothing may write to EFI partitions, disks or boot variables
   automatically, or route Windows/Linux through OpenCore by default.
5. **No secrets.** Never commit or post SMBIOS serials, MLB, UUIDs, ROM, MAC addresses, BitLocker
   or product keys. Run `skullintosh scan-secrets` before pushing.
6. **No Apple software** in the repository or packages.

## Ways to contribute

* **Test reports:** use the *Compatibility test report* or *Boot failure* issue template.
* **Hardware inventory:** run the inventory scripts and post the **sanitized** report
  ([docs/hardware-inventory.md](docs/dev/hardware-inventory.md)).
* **Backlog items:** see [docs/backlog.md](docs/dev/backlog.md). Items without 🖥 need no NUC.
* **Code:** see [docs/development.md](docs/dev/development.md).

## Pull requests

* Base on `main`; keep PRs focused.
* `pytest`, `pytest -m network` (if you touched builds), `ruff check`, `ruff format --check` and
  `skullintosh scan-secrets` pass locally.
* Changes to `manifests/dependencies.toml` come with the new license text (if changed) and a
  CHANGELOG entry. Hardware-affecting version bumps reset the profile's verified status until
  re-tested.
* Changing a profile's `status` needs a linked hardware report.
* Update [docs/compatibility.md](docs/compatibility.md) and the CHANGELOG when behaviour changes.

## Conduct

Be kind and specific. Hackintosh debugging is slow: give people logs and steps, not guesses.
Upstream projects (acidanthera, OpenIntelWireless, Dortania) are volunteers too. File bugs
there only after reproducing them without Skullintosh-specific changes.
