"""Static validation of a built EFI folder.

Nothing here proves an EFI boots. It catches build mistakes that would certainly break booting,
leak identities, weaken security silently, or endanger an existing Windows/Linux install.
"""

from __future__ import annotations

import platform
import plistlib
import subprocess
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from xml.parsers.expat import ExpatError

from skullintosh.build import PERSONAL_MARKER, read_provenance
from skullintosh.errors import SkullintoshError
from skullintosh.fetch import cache_dir, ensure_asset
from skullintosh.identity import non_placeholder_fields
from skullintosh.manifest import Manifest, load_manifest
from skullintosh.overlay import load_plist
from skullintosh.profiles import load_profile
from skullintosh.util import kernel_ranges_overlap, sha256_file, version_ge

ERROR, WARNING, INFO = "error", "warning", "info"

# boot-args that relax macOS security. Profiles must never add these silently.
SECURITY_RELAXING_ARGS = (
    "amfi_get_out_of_my_way",
    "amfi=",
    "-amfipassbeta",
    "-no_compat_check",
    "ipc_control_port_options",
    "cs_enforcement_disable",
    "-arm64e_preview_abi",
    "rootless=0",
    "kext-dev-mode",
)
SCAN_FS_LOCK = 0x1
# ScanPolicy filesystem bits (OpenCore Configuration.pdf). Windows Boot Manager and GRUB live on
# EFI System Partitions; Linux kernels on root/XBOOTLDR partitions. None may be scanned.
SCAN_DISALLOWED_FS = {
    0x400: "EFI System Partition",
    0x1000: "Linux root",
    0x2000: "Linux data",
    0x4000: "XBOOTLDR",
}
SCAN_ALLOW_MSFT_BASIC_DATA = 0x800
WIFI_BUNDLES = ("itlwm.kext", "AirportItlwm.kext")


@dataclass(frozen=True)
class Finding:
    level: str
    code: str
    message: str

    def __str__(self) -> str:
        return f"[{self.level.upper()}] {self.code}: {self.message}"


@dataclass
class _KextInfo:
    index: int
    bundle: str
    enabled: bool
    bounds: tuple[str, str]
    identifiers: dict[str, tuple[str, str]]  # bundle id -> (version, compatible version)
    libraries: dict[str, str]


def _read_kext(oc: Path, index: int, entry: dict) -> _KextInfo:
    bundle = entry.get("BundlePath", "")
    base = oc / "Kexts" / bundle
    identifiers: dict[str, tuple[str, str]] = {}
    libraries: dict[str, str] = {}
    plists = [base / entry.get("PlistPath", "Contents/Info.plist")]
    plists += sorted(base.glob("Contents/PlugIns/*.kext/Contents/Info.plist"))
    for i, plist in enumerate(plists):
        if not plist.is_file():
            continue
        info = load_plist(plist)
        ident = info.get("CFBundleIdentifier")
        if ident:
            identifiers[ident] = (
                str(info.get("CFBundleVersion", "0")),
                str(info.get("OSBundleCompatibleVersion", "")),
            )
        if i == 0:
            libraries.update(info.get("OSBundleLibraries", {}))
            libraries.update(info.get("OSBundleLibraries_x86_64", {}))
    return _KextInfo(
        index,
        bundle,
        bool(entry.get("Enabled")),
        (entry.get("MinKernel", ""), entry.get("MaxKernel", "")),
        identifiers,
        libraries,
    )


def check_references(config: dict, oc: Path) -> list[Finding]:
    out: list[Finding] = []
    referenced: dict[str, set[str]] = {
        "ACPI": set(),
        "Kexts": set(),
        "Drivers": set(),
        "Tools": set(),
    }
    for entry in config["ACPI"]["Add"]:
        referenced["ACPI"].add(entry["Path"])
        if not (oc / "ACPI" / entry["Path"]).is_file():
            out.append(
                Finding(ERROR, "missing-file", f"ACPI/{entry['Path']} is referenced but missing")
            )
    bundles = []
    for entry in config["Kernel"]["Add"]:
        bundle = entry["BundlePath"]
        bundles.append(bundle)
        referenced["Kexts"].add(bundle.split("/", 1)[0])
        base = oc / "Kexts" / bundle
        if not (base / entry["PlistPath"]).is_file():
            out.append(Finding(ERROR, "missing-file", f"{bundle}/{entry['PlistPath']} missing"))
        if entry["ExecutablePath"] and not (base / entry["ExecutablePath"]).is_file():
            out.append(
                Finding(ERROR, "missing-file", f"{bundle}/{entry['ExecutablePath']} missing")
            )
        if entry.get("Arch") not in ("Any", "x86_64"):
            out.append(Finding(ERROR, "kext-arch", f"{bundle}: Arch must be Any or x86_64"))
    duplicates = {b for b in bundles if bundles.count(b) > 1}
    for bundle in sorted(duplicates):
        out.append(Finding(ERROR, "duplicate-kext", f"{bundle} is listed more than once"))
    for entry in config["UEFI"]["Drivers"]:
        referenced["Drivers"].add(entry["Path"])
        if not (oc / "Drivers" / entry["Path"]).is_file():
            out.append(Finding(ERROR, "missing-file", f"Drivers/{entry['Path']} missing"))
    for entry in config["Misc"]["Tools"]:
        referenced["Tools"].add(entry["Path"])
        if not (oc / "Tools" / entry["Path"]).is_file():
            out.append(Finding(ERROR, "missing-file", f"Tools/{entry['Path']} missing"))
    for folder, names in referenced.items():
        directory = oc / folder
        if not directory.is_dir():
            continue
        for child in sorted(directory.iterdir()):
            if child.name not in names and not child.name.startswith("."):
                out.append(
                    Finding(
                        WARNING,
                        "unreferenced-file",
                        f"{folder}/{child.name} is not referenced by config.plist",
                    )
                )
    return out


def check_kexts(config: dict, oc: Path) -> list[Finding]:
    out: list[Finding] = []
    kexts = []
    for i, entry in enumerate(config["Kernel"]["Add"]):
        try:
            kexts.append(_read_kext(oc, i, entry))
        except SkullintoshError as exc:
            out.append(Finding(ERROR, "kext-plist", str(exc)))
    enabled = [k for k in kexts if k.enabled]
    for kext in enabled:
        for dep, required in sorted(kext.libraries.items()):
            if dep.startswith("com.apple."):
                continue
            providers = [
                k
                for k in enabled
                if dep in k.identifiers and kernel_ranges_overlap(k.bounds, kext.bounds)
            ]
            if not providers:
                out.append(
                    Finding(
                        ERROR,
                        "kext-dependency",
                        f"{kext.bundle} needs {dep} but no enabled kext provides it",
                    )
                )
                continue
            provider = providers[0]
            if provider.index > kext.index:
                out.append(
                    Finding(
                        ERROR,
                        "kext-order",
                        f"{kext.bundle} loads before its dependency {provider.bundle}",
                    )
                )
            version, compatible = provider.identifiers[dep]
            if not version_ge(version, required):
                out.append(
                    Finding(
                        ERROR,
                        "kext-version",
                        f"{kext.bundle} needs {dep} >= {required}, have {version}",
                    )
                )
            elif compatible and not version_ge(required, compatible):
                out.append(
                    Finding(
                        ERROR,
                        "kext-version",
                        f"{kext.bundle} links {dep} {required}, older than its "
                        f"compatible version {compatible}",
                    )
                )

    wifi = [k for k in enabled if k.bundle in WIFI_BUNDLES]
    for i, a in enumerate(wifi):
        for b in wifi[i + 1 :]:
            if kernel_ranges_overlap(a.bounds, b.bounds):
                out.append(
                    Finding(
                        ERROR,
                        "wifi-conflict",
                        f"{a.bundle} and {b.bundle} are both enabled for the same "
                        "kernels; use exactly one",
                    )
                )
    names = {k.bundle for k in enabled}
    for k in enabled:
        if k.bundle == "IntelBluetoothInjector.kext" and kernel_ranges_overlap(
            k.bounds, ("21.0.0", "")
        ):
            out.append(
                Finding(
                    ERROR,
                    "bluetooth-injector",
                    "IntelBluetoothInjector must not load on macOS 12+; use BlueToolFixup instead",
                )
            )
    if "IntelBluetoothFirmware.kext" in names and "BlueToolFixup.kext" not in names:
        out.append(
            Finding(
                ERROR,
                "bluetooth-fixup",
                "IntelBluetoothFirmware on macOS 12+ requires BlueToolFixup",
            )
        )
    return out


def check_applicability(prov: dict, manifest: Manifest) -> list[Finding]:
    out = []
    darwin = prov["darwin"]
    for record in prov.get("kexts", []):
        kid = record.get("id")
        if kid in manifest.kexts and not manifest.kexts[kid].applies_to(darwin):
            out.append(Finding(ERROR, "kext-os-version", f"{kid} is not built for darwin {darwin}"))
    return out


def check_security(config: dict, profile_allows_relaxation: bool = False) -> list[Finding]:
    out = []
    nvram = config["NVRAM"]["Add"].get("7C436110-AB2A-4BBB-A880-FE41995C9F82", {})
    csr = nvram.get("csr-active-config", b"\0\0\0\0")
    if csr != b"\0\0\0\0":
        out.append(
            Finding(
                ERROR,
                "sip-relaxed",
                f"csr-active-config is {csr.hex()}; SIP must stay fully enabled",
            )
        )
    args = str(nvram.get("boot-args", ""))
    for bad in SECURITY_RELAXING_ARGS:
        if bad in args:
            out.append(
                Finding(
                    ERROR,
                    "security-boot-arg",
                    f"boot-args contain {bad!r}, which weakens macOS security",
                )
            )
    sbm = config["Misc"]["Security"]["SecureBootModel"]
    if sbm == "Disabled" and not profile_allows_relaxation:
        out.append(
            Finding(
                ERROR,
                "secure-boot-disabled",
                "SecureBootModel is Disabled without a documented reason",
            )
        )
    if config["Misc"]["Security"].get("DmgLoading") == "Any":
        out.append(Finding(ERROR, "dmg-loading", "DmgLoading=Any allows unsigned DMGs"))
    return out


def check_dual_boot_safety(config: dict) -> list[Finding]:
    out = []
    boot = config["Misc"]["Boot"]
    if boot.get("LauncherOption") != "Disabled":
        out.append(
            Finding(
                ERROR,
                "boot-order",
                "LauncherOption must be Disabled so OpenCore never edits the firmware boot order",
            )
        )
    if not config["UEFI"]["Quirks"].get("RequestBootVarRouting"):
        out.append(
            Finding(
                ERROR,
                "boot-order",
                "RequestBootVarRouting must be true so macOS can't rewrite BootOrder/BootNext",
            )
        )
    if config["Misc"]["Security"].get("AllowSetDefault"):
        out.append(
            Finding(
                WARNING,
                "boot-order",
                "AllowSetDefault lets the picker change the default boot entry",
            )
        )
    for driver in config["UEFI"]["Drivers"]:
        if driver.get("Path") == "ResetNvramEntry.efi" and driver.get("Enabled"):
            args = str(driver.get("Arguments", "")).split()
            if "--preserve-boot" not in args or "--apple" in args:
                out.append(
                    Finding(
                        ERROR,
                        "nvram-reset",
                        "ResetNvramEntry needs --preserve-boot (and not --apple); otherwise a "
                        "Reset NVRAM deletes the Windows Boot Manager and GRUB boot entries",
                    )
                )
    policy = int(config["Misc"]["Security"]["ScanPolicy"])
    if policy == 0 or not policy & SCAN_FS_LOCK:
        out.append(
            Finding(
                ERROR,
                "scan-policy",
                "ScanPolicy does not lock filesystems; OpenCore would offer to boot "
                "Windows/Linux with macOS ACPI changes applied",
            )
        )
    else:
        exposed = [name for bit, name in SCAN_DISALLOWED_FS.items() if policy & bit]
        if exposed:
            out.append(
                Finding(
                    ERROR,
                    "scan-policy",
                    f"ScanPolicy exposes {', '.join(exposed)} filesystems to the OpenCore picker",
                )
            )
        if policy & SCAN_ALLOW_MSFT_BASIC_DATA:
            drivers = {d.get("Path") for d in config["UEFI"]["Drivers"] if d.get("Enabled")}
            if "OpenNtfsDxe.efi" in drivers:
                out.append(
                    Finding(
                        ERROR,
                        "scan-policy",
                        "Msft Basic Data scanning with OpenNtfsDxe loaded exposes Windows volumes",
                    )
                )
            else:
                out.append(
                    Finding(
                        WARNING,
                        "scan-policy",
                        "Msft Basic Data (FAT32) volumes are scanned for installer media; "
                        "rebuild without fat32_installer once macOS is installed",
                    )
                )
    return out


def check_identity(config: dict, build_dir: Path, prov: dict) -> list[Finding]:
    generic = config["PlatformInfo"]["Generic"]
    changed = non_placeholder_fields(generic)
    marker = (build_dir / PERSONAL_MARKER).is_file()
    if prov.get("personalized"):
        if not marker:
            return [Finding(ERROR, "identity", "personalized build is missing its marker file")]
        return [
            Finding(INFO, "identity", "personal SMBIOS identity present: do not share this build")
        ]
    if changed:
        return [
            Finding(
                ERROR,
                "identity-leak",
                f"PlatformInfo fields {', '.join(changed)} are not placeholders in a "
                "build marked shareable",
            )
        ]
    return []


def check_files(build_dir: Path, prov: dict) -> list[Finding]:
    out = []
    recorded = prov.get("files", {})
    actual = {p.relative_to(build_dir).as_posix() for p in build_dir.rglob("*") if p.is_file()}
    actual -= {"provenance.json", PERSONAL_MARKER}
    for rel in sorted(actual - set(recorded)):
        out.append(Finding(ERROR, "untracked-file", f"{rel} is not in provenance.json"))
    for rel, meta in sorted(recorded.items()):
        path = build_dir / rel
        if not path.is_file():
            out.append(Finding(ERROR, "missing-file", f"{rel} is in provenance but missing"))
        elif sha256_file(path) != meta["sha256"]:
            out.append(
                Finding(ERROR, "modified-file", f"{rel} changed after the build (hash mismatch)")
            )
    oc_sources = {
        m["source"]
        for r, m in recorded.items()
        if r.startswith("EFI/")
        and not r.startswith("EFI/OC/Kexts/")
        and not r.endswith("config.plist")
    }
    if len(oc_sources) > 1:
        out.append(
            Finding(
                ERROR,
                "opencore-mixed",
                f"OpenCore files come from several releases: {sorted(oc_sources)}",
            )
        )
    return out


def ocvalidate_member() -> str | None:
    system, machine = platform.system(), platform.machine().lower()
    if system == "Darwin":
        return "Utilities/ocvalidate/ocvalidate"
    if system == "Linux" and machine in ("x86_64", "amd64"):
        return "Utilities/ocvalidate/ocvalidate.linux"
    if system == "Windows":
        return "Utilities/ocvalidate/ocvalidate.exe"
    return None


def run_ocvalidate(
    root: Path, manifest: Manifest, prov: dict, config_path: Path, *, offline: bool
) -> tuple[bool | None, str]:
    """Run the ocvalidate shipped in the same OpenCore archive. ``None`` = not runnable here."""
    member = ocvalidate_member()
    if member is None:
        return None, f"no ocvalidate binary for {platform.system()}/{platform.machine()}"
    flavor = prov["flavor"]
    asset = manifest.asset_for("opencore", flavor)
    if asset.name != prov["opencore"]["asset"]:
        return False, (
            f"build used {prov['opencore']['asset']} but the manifest now pins "
            f"{asset.name}; rebuild before validating"
        )
    archive = ensure_asset(cache_dir(root), asset, offline=offline)
    with tempfile.TemporaryDirectory() as tmp, zipfile.ZipFile(archive) as zf:
        target = Path(tmp) / Path(member).name
        target.write_bytes(zf.read(member))
        target.chmod(0o755)
        proc = subprocess.run(
            [str(target), str(config_path)], capture_output=True, text=True, timeout=120
        )
    output = (proc.stdout + proc.stderr).strip()
    return proc.returncode == 0 and "No issues found" in output, output


def validate_build(
    root: Path, build_dir: Path, *, ocvalidate: str = "auto", offline: bool = False
) -> list[Finding]:
    """``ocvalidate`` is ``auto`` (run when available), ``require`` or ``skip``."""
    root = root.resolve()
    prov = read_provenance(build_dir)
    manifest = load_manifest(root / "manifests" / "dependencies.toml")
    config_path = build_dir / "EFI" / "OC" / "config.plist"
    try:
        with open(config_path, "rb") as fh:
            config = plistlib.load(fh)
    except (OSError, plistlib.InvalidFileException, ValueError, ExpatError) as exc:
        return [Finding(ERROR, "plist", f"config.plist does not parse: {exc}")]
    oc = build_dir / "EFI" / "OC"

    findings: list[Finding] = []
    if prov.get("profile_status") == "research":
        findings.append(
            Finding(WARNING, "research", "research profile: not expected to boot; experiments only")
        )
    try:
        load_profile(root, prov["profile"])
    except SkullintoshError as exc:
        findings.append(Finding(ERROR, "profile", str(exc)))
    findings += check_files(build_dir, prov)
    findings += check_references(config, oc)
    findings += check_kexts(config, oc)
    findings += check_applicability(prov, manifest)
    findings += check_security(config)
    findings += check_dual_boot_safety(config)
    findings += check_identity(config, build_dir, prov)
    if prov["opencore"]["sha256"] != manifest.asset_for("opencore", prov["flavor"]).sha256:
        findings.append(
            Finding(
                ERROR,
                "opencore-version",
                "build was made from a different OpenCore archive than the manifest pins",
            )
        )

    if ocvalidate != "skip":
        ok, output = run_ocvalidate(root, manifest, prov, config_path, offline=offline)
        tail = output.splitlines()[-1] if output else ""
        if ok is None:
            level = ERROR if ocvalidate == "require" else WARNING
            findings.append(Finding(level, "ocvalidate", f"skipped: {output}"))
        elif ok:
            findings.append(
                Finding(INFO, "ocvalidate", f"ocvalidate {prov['opencore']['tag']}: {tail}")
            )
        else:
            findings.append(Finding(ERROR, "ocvalidate", output))
    return findings


def has_errors(findings: list[Finding]) -> bool:
    return any(f.level == ERROR for f in findings)
