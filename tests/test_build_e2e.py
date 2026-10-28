# skullintosh: secret-scan-ignore-file  (contains deliberately fake identifiers)
"""End-to-end builds against the real pinned releases (needs network or a warm cache).

Run with: pytest -m network
"""

import plistlib

import pytest

from skullintosh.build import BuildRequest, build, build_digest, read_provenance
from skullintosh.errors import SkullintoshError
from skullintosh.package import package_build
from skullintosh.util import sha256_file
from skullintosh.validate import has_errors, validate_build

pytestmark = pytest.mark.network


@pytest.mark.parametrize("flavor", ["release", "debug"])
def test_monterey_builds_validates_and_is_reproducible(root, tmp_path, flavor):
    a = build(root, BuildRequest("monterey", flavor, output=tmp_path / "a"))
    b = build(root, BuildRequest("monterey", flavor, output=tmp_path / "b"))
    assert build_digest(a) == build_digest(b)
    findings = validate_build(root, a, ocvalidate="auto")
    assert not has_errors(findings), "\n".join(map(str, findings))
    prov = read_provenance(a)
    assert prov["opencore"]["asset"].endswith(f"{flavor.upper()}.zip")
    assert prov["personalized"] is False


def test_monterey_config_matches_audit_decisions(root, tmp_path):
    out = build(root, BuildRequest("monterey", output=tmp_path / "m"))
    cfg = plistlib.loads((out / "EFI/OC/config.plist").read_bytes())
    igpu = cfg["DeviceProperties"]["Add"]["PciRoot(0x0)/Pci(0x2,0x0)"]
    assert igpu["AAPL,ig-platform-id"] == bytes.fromhex("05003b19")
    assert "enable-hdmi20" not in igpu  # no-op on macOS 11+
    assert cfg["PlatformInfo"]["Generic"]["SystemProductName"] == "iMac17,1"
    assert cfg["Misc"]["Security"]["ScanPolicy"] == 769
    assert cfg["Misc"]["Boot"]["LauncherOption"] == "Disabled"
    bundles = [k["BundlePath"] for k in cfg["Kernel"]["Add"]]
    assert bundles[0] == "Lilu.kext"
    assert "USBInjectAll.kext" not in bundles and "CPUFriend.kext" not in bundles
    assert not any("itlwm" in b.lower() for b in bundles)  # wifi defaults to none
    assert [d["Path"] for d in cfg["UEFI"]["Drivers"]] == [
        "OpenHfsPlus.efi",
        "OpenRuntime.efi",
        "ResetNvramEntry.efi",
    ]
    assert not (out / "EFI/OC/Drivers/HfsPlus.efi").exists()  # no Apple binaries
    reset = next(d for d in cfg["UEFI"]["Drivers"] if d["Path"] == "ResetNvramEntry.efi")
    assert reset["Arguments"] == "--preserve-boot"


def test_wifi_variants(root, tmp_path):
    out = build(
        root, BuildRequest("monterey", overrides=["wifi=airportitlwm"], output=tmp_path / "w")
    )
    cfg = plistlib.loads((out / "EFI/OC/config.plist").read_bytes())
    entry = next(k for k in cfg["Kernel"]["Add"] if k["BundlePath"] == "AirportItlwm.kext")
    assert (entry["MinKernel"], entry["MaxKernel"]) == ("21.0.0", "21.99.99")
    assert not has_errors(validate_build(root, out, ocvalidate="skip"))


def test_research_profiles_need_opt_in(root, tmp_path):
    with pytest.raises(SkullintoshError, match="research"):
        build(root, BuildRequest("ventura", output=tmp_path / "v"))
    out = build(root, BuildRequest("ventura", output=tmp_path / "v", allow_research=True))
    assert not has_errors(validate_build(root, out, ocvalidate="auto"))


def test_tampering_is_detected(root, tmp_path):
    out = build(root, BuildRequest("monterey", output=tmp_path / "t"))
    (out / "EFI/OC/Kexts/Lilu.kext/Contents/Info.plist").write_bytes(b"tampered")
    (out / "EFI/OC/Drivers/Extra.efi").write_bytes(b"x")
    found = {f.code for f in validate_build(root, out, ocvalidate="skip") if f.level == "error"}
    assert {"modified-file", "untracked-file"} <= found


def test_package_is_deterministic_and_refuses_personal_builds(root, tmp_path):
    out = build(root, BuildRequest("monterey", output=tmp_path / "p"))
    one = package_build(root, out, tmp_path / "d1", ocvalidate="auto")
    two = package_build(root, out, tmp_path / "d2", ocvalidate="auto")
    assert one.name.endswith("-candidate.zip")
    assert sha256_file(one) == sha256_file(two)

    smbios = tmp_path / "smbios.toml"
    smbios.write_text(
        'SystemSerialNumber = "C02TQ1XYJ1GJ"\n'
        'MLB = "C02734205J9GK4XAB"\n'
        'SystemUUID = "3F1A2B4C-5D6E-4F70-8192-A3B4C5D6E7F8"\n'
        'ROM = "a1b2c3d4e5f6"\n'
    )
    personal = build(root, BuildRequest("monterey", smbios=smbios, output=tmp_path / "me"))
    assert not has_errors(validate_build(root, personal, ocvalidate="skip"))
    with pytest.raises(SkullintoshError, match="personal"):
        package_build(root, personal, tmp_path / "d3")
