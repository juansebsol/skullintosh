"""Assemble a version-specific EFI folder from pinned, checksum-verified releases."""

from __future__ import annotations

import copy
import hashlib
import json
import plistlib
import shutil
import tempfile
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from skullintosh import __version__
from skullintosh.errors import SkullintoshError
from skullintosh.fetch import cache_dir, ensure_asset
from skullintosh.identity import PLACEHOLDERS, load_identity
from skullintosh.manifest import Asset, Manifest, load_manifest
from skullintosh.overlay import apply_overlay, load_plist, reset_owned
from skullintosh.profiles import (
    Item,
    Profile,
    check_profile_against_manifest,
    condition_true,
    load_profile,
    resolve_features,
)
from skullintosh.usbmap import load_usb_map, write_kext
from skullintosh.util import extract_member_tree, kernel_bounds, tree_digest

NVRAM_APPLE_BOOT = "7C436110-AB2A-4BBB-A880-FE41995C9F82"
OC_CORE_FILES = (
    "X64/EFI/BOOT/BOOTx64.efi",
    "X64/EFI/BOOT/.contentFlavour",
    "X64/EFI/BOOT/.contentVisibility",
    "X64/EFI/OC/OpenCore.efi",
    "X64/EFI/OC/.contentFlavour",
    "X64/EFI/OC/.contentVisibility",
)
OC_DRIVERS = "X64/EFI/OC/Drivers"
OC_TOOLS = "X64/EFI/OC/Tools"
OC_ACPI = "Docs/AcpiSamples/Binaries"
OC_SAMPLE = "Docs/Sample.plist"
PROVENANCE = "provenance.json"
PERSONAL_MARKER = "PERSONALIZED-DO-NOT-SHARE.txt"
GENERATED = "generated"


@dataclass
class BuildRequest:
    profile: str
    flavor: str = "release"
    overrides: list[str] = field(default_factory=list)
    smbios: Path | None = None
    output: Path | None = None
    offline: bool = False
    allow_research: bool = False


@dataclass
class _Sources:
    """Which package/asset each output path prefix came from."""

    by_prefix: dict[str, str] = field(default_factory=dict)

    def add(self, prefix: str, origin: str) -> None:
        self.by_prefix[prefix] = origin

    def origin_of(self, path: str) -> str:
        best = ""
        for prefix in self.by_prefix:
            if (path == prefix or path.startswith(prefix + "/")) and len(prefix) > len(best):
                best = prefix
        return self.by_prefix.get(best, GENERATED)


def default_output(root: Path, profile: str, flavor: str, personalized: bool) -> Path:
    suffix = "-personal" if personalized else ""
    return root / "build" / f"{profile}-{flavor}{suffix}"


def _origin(asset: Asset, manifest: Manifest) -> str:
    package = manifest.package(asset.package)
    return f"{package.id}@{package.tag}:{asset.name}"


def _template(entries: list[dict], path: str) -> dict:
    for entry in entries:
        if entry.get("Path") == path:
            return copy.deepcopy(entry)
    return copy.deepcopy(entries[0])


def _kext_entry(
    template: dict, bundle_dir: Path, bundle: str, comment: str, bounds: tuple[str, str]
) -> dict:
    info = load_plist(bundle_dir / "Contents" / "Info.plist")
    exe = info.get("CFBundleExecutable", "")
    exe_path = (
        f"Contents/MacOS/{exe}" if exe and (bundle_dir / "Contents/MacOS" / exe).is_file() else ""
    )
    entry = {k: template[k] for k in template}
    entry.update(
        {
            "Arch": "x86_64",
            "BundlePath": bundle,
            "Comment": comment,
            "Enabled": True,
            "ExecutablePath": exe_path,
            "MinKernel": bounds[0],
            "MaxKernel": bounds[1],
            "PlistPath": "Contents/Info.plist",
        }
    )
    return entry


def _generic_entry(template: dict, item: Item, path: str, **values: object) -> dict:
    entry = {k: template[k] for k in template}
    entry.update({"Enabled": True, "Path": path, "Comment": item.comment or path})
    entry.update(values)
    return entry


def _selected(items: tuple[Item, ...], features: dict, flavor: str) -> list[Item]:
    return [i for i in items if i.selected(features, flavor)]


def build(root: Path, req: BuildRequest) -> Path:
    if req.flavor not in ("release", "debug"):
        raise SkullintoshError("flavor must be release or debug")
    root = root.resolve()
    manifest = load_manifest(root / "manifests" / "dependencies.toml")
    profile: Profile = load_profile(root, req.profile)
    if not profile.buildable and not req.allow_research:
        raise SkullintoshError(
            f"profile {profile.id} has status 'research': it documents open questions and is "
            "not expected to boot. Pass --allow-research to build it anyway for experiments."
        )
    problems = check_profile_against_manifest(profile, manifest)
    if problems:
        raise SkullintoshError("profile/manifest mismatch:\n  " + "\n  ".join(problems))
    features = resolve_features(profile, req.overrides)
    identity = load_identity(req.smbios) if req.smbios else None
    output = req.output or default_output(root, profile.id, req.flavor, identity is not None)

    cache = cache_dir(root)
    oc_asset = manifest.asset_for("opencore", req.flavor)
    oc_zip = ensure_asset(cache, oc_asset, offline=req.offline)
    oc_origin = _origin(oc_asset, manifest)

    kexts = _selected(profile.kexts, features, req.flavor)
    drivers = _selected(profile.drivers, features, req.flavor)
    tools = _selected(profile.tools, features, req.flavor)
    acpi = _selected(profile.acpi, features, req.flavor)

    work_parent = root / "build" / ".tmp"
    work_parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=work_parent) as tmp_name:
        stage = Path(tmp_name) / "out"
        efi = stage / "EFI"
        oc_dir = efi / "OC"
        for sub in ("ACPI", "Drivers", "Kexts", "Tools"):
            (oc_dir / sub).mkdir(parents=True, exist_ok=True)
        sources = _Sources()
        used_assets: dict[str, Asset] = {oc_asset.name: oc_asset}

        with zipfile.ZipFile(oc_zip) as oz:
            for member in OC_CORE_FILES:
                dest = efi / Path(member).parent.relative_to("X64/EFI")
                extract_member_tree(oz, member, dest)
            for item in drivers:
                extract_member_tree(oz, f"{OC_DRIVERS}/{item.name}", oc_dir / "Drivers")
            for item in tools:
                extract_member_tree(oz, f"{OC_TOOLS}/{item.name}", oc_dir / "Tools")
            for item in acpi:
                extract_member_tree(oz, f"{OC_ACPI}/{item.name}", oc_dir / "ACPI")
            sample = plistlib.loads(oz.read(OC_SAMPLE))
        sources.add("EFI", oc_origin)

        kext_records = []
        seen_bundles: set[str] = set()
        for item in kexts:
            if item.name == "USBMap":
                if not profile.usb_map:
                    raise SkullintoshError(f"profile {profile.id} lists USBMap but no usb_map")
                usb = load_usb_map(profile.usb_map)
                write_kext(usb, profile.smbios_model, oc_dir / "Kexts")
                sources.add("EFI/OC/Kexts/USBMap.kext", GENERATED)
                note = "verified" if usb.verified else "UNVERIFIED provisional map"
                kext_records.append(
                    ("USBMap.kext", f"Generated USB map ({note})", ("", ""), "USBMap", None)
                )
                seen_bundles.add("USBMap.kext")
                continue
            kext = manifest.kext(item.name)
            if kext.bundle_name in seen_bundles:
                raise SkullintoshError(f"two selected kexts provide {kext.bundle_name}")
            seen_bundles.add(kext.bundle_name)
            asset = manifest.kext_asset(kext, req.flavor)
            archive = ensure_asset(cache, asset, offline=req.offline)
            with zipfile.ZipFile(archive) as kz:
                extract_member_tree(kz, kext.path, oc_dir / "Kexts")
            used_assets[asset.name] = asset
            sources.add(f"EFI/OC/Kexts/{kext.bundle_name}", _origin(asset, manifest))
            bounds = (
                kext.min_kernel or kernel_bounds(kext.darwin_min, kext.darwin_max)[0],
                kext.max_kernel or kernel_bounds(kext.darwin_min, kext.darwin_max)[1],
            )
            package = manifest.package(kext.package)
            comment = f"{kext.id} {package.tag}" + (f" - {item.comment}" if item.comment else "")
            kext_records.append((kext.bundle_name, comment, bounds, kext.id, asset.name))

        config = copy.deepcopy(sample)
        reset_owned(config)
        overlays = list(profile.overlays)
        if req.flavor == "debug":
            overlays += list(profile.debug_overlays)
        for condition, paths in profile.feature_overlays.items():
            if condition_true(condition, features):
                overlays += list(paths)
        for path in overlays:
            apply_overlay(config, load_plist(path), str(path.relative_to(root)))

        config["ACPI"]["Add"] = [
            _generic_entry(_template(sample["ACPI"]["Add"], i.name), i, i.name) for i in acpi
        ]
        kernel_template = sample["Kernel"]["Add"][0]
        config["Kernel"]["Add"] = [
            _kext_entry(kernel_template, oc_dir / "Kexts" / bundle, bundle, comment, bounds)
            for bundle, comment, bounds, _kid, _asset in kext_records
        ]
        config["UEFI"]["Drivers"] = []
        for item in drivers:
            template = _template(sample["UEFI"]["Drivers"], item.name)
            load_early = template.get("Path") == item.name and template.get("LoadEarly", False)
            config["UEFI"]["Drivers"].append(
                _generic_entry(
                    template, item, item.name, LoadEarly=load_early, Arguments=item.arguments
                )
            )
        config["Misc"]["Tools"] = []
        for item in tools:
            template = _template(sample["Misc"]["Tools"], item.name)
            values: dict[str, object] = {"Auxiliary": True}
            if template.get("Path") != item.name:
                values.update(
                    Name=item.name.removesuffix(".efi"),
                    Flavour="Auto",
                    Arguments="",
                    TextMode=True,
                    RealPath=False,
                )
            config["Misc"]["Tools"].append(_generic_entry(template, item, item.name, **values))

        boot_args = list(profile.boot_args)
        if req.flavor == "debug":
            boot_args += list(profile.debug_boot_args)
        config["NVRAM"]["Add"].setdefault(NVRAM_APPLE_BOOT, {})["boot-args"] = " ".join(boot_args)

        generic = config["PlatformInfo"]["Generic"]
        generic["SystemProductName"] = profile.smbios_model
        generic.update(identity or PLACEHOLDERS)

        sources.add("EFI/OC/config.plist", GENERATED)
        with open(oc_dir / "config.plist", "wb") as fh:
            plistlib.dump(config, fh, sort_keys=True)

        files = tree_digest(stage)
        provenance = {
            "tool": f"skullintosh {__version__}",
            "profile": profile.id,
            "profile_status": profile.status,
            "darwin": profile.darwin,
            "flavor": req.flavor,
            "features": dict(sorted(features.items())),
            "smbios_model": profile.smbios_model,
            "personalized": identity is not None,
            "opencore": {
                "tag": manifest.package("opencore").tag,
                "asset": oc_asset.name,
                "sha256": oc_asset.sha256,
            },
            "kexts": [
                {"bundle": b, "id": kid, "asset": a, "min_kernel": lo, "max_kernel": hi}
                for b, _c, (lo, hi), kid, a in kext_records
            ],
            "sources": [
                {
                    "package": a.package,
                    "repo": manifest.package(a.package).repo,
                    "tag": manifest.package(a.package).tag,
                    "license": manifest.package(a.package).license,
                    "asset": a.name,
                    "sha256": a.sha256,
                    "url": a.url,
                }
                for a in sorted(used_assets.values(), key=lambda a: (a.package, a.name))
            ],
            "files": {p: {"sha256": h, "source": sources.origin_of(p)} for p, h in files.items()},
        }
        (stage / PROVENANCE).write_text(json.dumps(provenance, indent=2, sort_keys=True) + "\n")
        if identity:
            (stage / PERSONAL_MARKER).write_text(
                "This EFI contains a personal SMBIOS identity (serial, MLB, UUID, ROM).\n"
                "Do not upload, share, or attach it to issues. `skullintosh package` refuses it.\n"
            )

        if output.exists():
            if not (output / PROVENANCE).is_file():
                raise SkullintoshError(
                    f"{output} exists and is not a Skullintosh build; refusing to replace it"
                )
            shutil.rmtree(output)
        output.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(stage), str(output))
    return output


def read_provenance(build_dir: Path) -> dict:
    path = build_dir / PROVENANCE
    if not path.is_file():
        raise SkullintoshError(f"{build_dir} has no {PROVENANCE}; is it a Skullintosh build?")
    return json.loads(path.read_text())


def build_digest(build_dir: Path) -> str:
    """A single hash over every file in a build, for reproducibility checks."""
    h = hashlib.sha256()
    for rel, digest in tree_digest(build_dir).items():
        h.update(f"{rel}\0{digest}\n".encode())
    return h.hexdigest()
