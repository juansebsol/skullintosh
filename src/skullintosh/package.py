"""Turn a validated, shareable build into a deterministic release zip."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from skullintosh import __version__
from skullintosh.build import PERSONAL_MARKER, read_provenance
from skullintosh.errors import SkullintoshError
from skullintosh.util import deterministic_zip, sha256_file
from skullintosh.validate import has_errors, validate_build

README_FIRST = """\
Skullintosh {version} - {profile} ({flavor})
=================================================

Profile status: {status_upper}
{status_text}

This package contains an OpenCore EFI folder for the Intel NUC6i7KYK (Skull Canyon) ONLY.

Before using it:
  1. Read docs/installation.md and docs/recovery.md in the Skullintosh repository.
  2. Back up your existing EFI partitions and UEFI boot entries (scripts/backup/).
  3. Put this EFI on a REMOVABLE USB stick first. Do not copy it to an internal disk's EFI
     partition, and do not let it replace Windows Boot Manager or GRUB.
  4. Add your own SMBIOS identity (GenSMBIOS) locally. This package deliberately contains
     OpenCore's placeholder serials, which are not valid for Apple services.

provenance.json lists the exact upstream release, version and SHA-256 of every file.
Third-party licenses are in licenses/ and THIRD_PARTY_NOTICES.md. GPL-licensed components
(IntelMausi, BrcmPatchRAM/BlueToolFixup, IntelBluetoothFirmware, itlwm, parts of NVMeFix)
are unmodified upstream binaries; their source code is at the repository and tag listed for
each one in provenance.json.

macOS is licensed by Apple for Apple-branded hardware. This package contains no Apple
software. You are responsible for complying with Apple's license terms.
"""

STATUS_TEXT = {
    "candidate": "UNVERIFIED: this configuration passes static validation but has NOT been\n"
    "confirmed to boot on real hardware. Expect problems.",
    "verified": "Verified on hardware for the features listed in docs/compatibility.md.",
    "research": "EXPERIMENTAL RESEARCH BUILD: not expected to work.",
}


def package_build(
    root: Path, build_dir: Path, dist: Path, *, offline: bool = False, ocvalidate: str = "require"
) -> Path:
    root = root.resolve()
    prov = read_provenance(build_dir)
    if prov.get("personalized") or (build_dir / PERSONAL_MARKER).exists():
        raise SkullintoshError(
            "refusing to package a build containing a personal SMBIOS "
            "identity; rebuild without --smbios"
        )
    if prov["profile_status"] == "research":
        raise SkullintoshError("research profiles are never packaged")
    findings = validate_build(root, build_dir, ocvalidate=ocvalidate, offline=offline)
    if has_errors(findings):
        details = "\n  ".join(str(f) for f in findings if f.level == "error")
        raise SkullintoshError(f"validation failed; not packaging:\n  {details}")

    status = prov["profile_status"]
    label = "" if status == "verified" else f"-{status}"
    name = f"skullintosh-{__version__}-{prov['profile']}-{prov['flavor']}{label}"
    with tempfile.TemporaryDirectory() as tmp:
        stage = Path(tmp) / name
        shutil.copytree(build_dir / "EFI", stage / "EFI")
        shutil.copy2(build_dir / "provenance.json", stage / "provenance.json")
        shutil.copy2(root / "LICENSE", stage / "LICENSE")
        shutil.copy2(root / "THIRD_PARTY_NOTICES.md", stage / "THIRD_PARTY_NOTICES.md")
        (stage / "licenses").mkdir()
        for source in prov["sources"]:
            license_file = root / "licenses" / f"{source['package']}.txt"
            if not license_file.is_file():
                raise SkullintoshError(
                    f"missing license text {license_file.name} for {source['package']}"
                )
            shutil.copy2(license_file, stage / "licenses" / license_file.name)
        (stage / "README-FIRST.txt").write_text(
            README_FIRST.format(
                version=__version__,
                profile=prov["profile"],
                flavor=prov["flavor"],
                status_upper=status.upper(),
                status_text=STATUS_TEXT[status],
            )
        )
        out = dist / f"{name}.zip"
        deterministic_zip(Path(tmp), out)
    digest = sha256_file(out)
    out.with_name(out.name + ".sha256").write_text(f"{digest}  {out.name}\n")
    return out
