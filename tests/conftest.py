import plistlib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def root() -> Path:
    return ROOT


def write_plist(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as fh:
        plistlib.dump(data, fh)


def make_kext(
    kexts_dir: Path,
    bundle: str,
    ident: str,
    version: str = "1.0.0",
    libraries: dict | None = None,
    executable: bool = True,
    compatible: str | None = None,
) -> None:
    base = kexts_dir / bundle
    info = {
        "CFBundleIdentifier": ident,
        "CFBundleVersion": version,
        "OSBundleLibraries": libraries or {"com.apple.kpi.libkern": "8.0.0"},
    }
    if compatible:
        info["OSBundleCompatibleVersion"] = compatible
    if executable:
        exe = bundle.removesuffix(".kext")
        info["CFBundleExecutable"] = exe
        (base / "Contents" / "MacOS").mkdir(parents=True, exist_ok=True)
        (base / "Contents" / "MacOS" / exe).write_bytes(b"\xcf\xfa\xed\xfe")
    write_plist(base / "Contents" / "Info.plist", info)


def kext_entry(
    bundle: str, executable: bool = True, lo: str = "", hi: str = "", enabled: bool = True
) -> dict:
    exe = bundle.removesuffix(".kext")
    return {
        "Arch": "x86_64",
        "BundlePath": bundle,
        "Comment": "",
        "Enabled": enabled,
        "ExecutablePath": f"Contents/MacOS/{exe}" if executable else "",
        "MaxKernel": hi,
        "MinKernel": lo,
        "PlistPath": "Contents/Info.plist",
    }


def base_config() -> dict:
    """A minimal config with the keys the validator reads, in a safe default state."""
    return {
        "ACPI": {"Add": []},
        "Kernel": {"Add": []},
        "UEFI": {"Drivers": [], "Quirks": {"RequestBootVarRouting": True}},
        "Misc": {
            "Tools": [],
            "Boot": {"LauncherOption": "Disabled"},
            "Security": {
                "ScanPolicy": 769,
                "SecureBootModel": "Default",
                "AllowSetDefault": False,
                "DmgLoading": "Signed",
            },
        },
        "NVRAM": {
            "Add": {
                "7C436110-AB2A-4BBB-A880-FE41995C9F82": {
                    "boot-args": "",
                    "csr-active-config": b"\0\0\0\0",
                }
            }
        },
        "PlatformInfo": {
            "Automatic": True,
            "Generic": {
                "SystemSerialNumber": "W00000000001",
                "MLB": "M0000000000000001",
                "SystemUUID": "OEM",
                "ROM": bytes.fromhex("112233445566"),
            },
        },
    }
