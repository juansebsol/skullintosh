"""SMBIOS identity handling. Real identities live only in git-ignored local files."""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

from skullintosh.errors import SkullintoshError

# Values every shareable build carries: OpenCore's Sample.plist placeholders, except SystemUUID.
# Apple Secure Boot (SecureBootModel Default, ApECID 0) derives its ID from system-id and halts
# on a zero UUID ("Grabbed zero system-id for SB"), so shared builds read the firmware's own
# SMBIOS UUID at boot with "OEM". Nothing machine-specific ends up in the file.
PLACEHOLDERS: dict[str, object] = {
    "SystemSerialNumber": "W00000000001",
    "MLB": "M0000000000000001",
    "SystemUUID": "OEM",
    "ROM": bytes.fromhex("112233445566"),
}
ZERO_UUID = "00000000-0000-0000-0000-000000000000"
FIELDS = tuple(PLACEHOLDERS)

_SERIAL_RE = re.compile(r"^[A-Z0-9]{11,12}$")
_MLB_RE = re.compile(r"^[A-Z0-9]{13,17}$")
_UUID_RE = re.compile(r"^[0-9A-F]{8}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{12}$")
_ROM_RE = re.compile(r"^[0-9a-fA-F]{12}$")


def load_identity(path: Path) -> dict[str, object]:
    """Read ``SystemSerialNumber``/``MLB``/``SystemUUID``/``ROM`` from a local TOML file."""
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise SkullintoshError(f"cannot read SMBIOS identity {path}: {exc}") from exc
    missing = [f for f in FIELDS if f not in data]
    extra = set(data) - set(FIELDS)
    if missing or extra:
        raise SkullintoshError(
            f"{path}: needs exactly {', '.join(FIELDS)} (missing {missing}, unexpected "
            f"{sorted(extra)})"
        )
    serial, mlb = str(data["SystemSerialNumber"]), str(data["MLB"])
    uuid, rom = str(data["SystemUUID"]).upper(), str(data["ROM"]).replace(":", "")
    if not _SERIAL_RE.match(serial):
        raise SkullintoshError(f"{path}: SystemSerialNumber is not a 11-12 character serial")
    if not _MLB_RE.match(mlb):
        raise SkullintoshError(f"{path}: MLB is not a 13-17 character board serial")
    if not _UUID_RE.match(uuid) or uuid == ZERO_UUID:
        raise SkullintoshError(f"{path}: SystemUUID is not a non-zero UUID")
    if not _ROM_RE.match(rom):
        raise SkullintoshError(f"{path}: ROM must be 12 hex digits (6 bytes)")
    identity = {
        "SystemSerialNumber": serial,
        "MLB": mlb,
        "SystemUUID": uuid,
        "ROM": bytes.fromhex(rom),
    }
    if any(identity[f] == PLACEHOLDERS[f] for f in FIELDS):
        raise SkullintoshError(f"{path}: still contains OpenCore placeholder values")
    return identity


def non_placeholder_fields(generic: dict) -> list[str]:
    return [f for f in FIELDS if generic.get(f) != PLACEHOLDERS[f]]
