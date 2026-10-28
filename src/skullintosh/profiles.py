"""macOS version profiles (``profiles/<name>/profile.toml``)."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from skullintosh.errors import SkullintoshError
from skullintosh.manifest import Manifest

STATUSES = ("research", "candidate", "verified")
FLAVORS = ("release", "debug")


@dataclass(frozen=True)
class Item:
    """An ACPI table, kext, driver or tool in a profile, with optional build conditions."""

    name: str
    when: str | None = None
    flavors: tuple[str, ...] = FLAVORS
    comment: str = ""
    arguments: str = ""

    def selected(self, features: dict[str, object], flavor: str) -> bool:
        return flavor in self.flavors and condition_true(self.when, features)


@dataclass(frozen=True)
class Profile:
    id: str
    dir: Path
    title: str
    status: str
    darwin: int
    smbios_model: str
    overlays: tuple[Path, ...]
    debug_overlays: tuple[Path, ...]
    boot_args: tuple[str, ...]
    debug_boot_args: tuple[str, ...]
    usb_map: Path | None
    features: dict[str, object]
    feature_choices: dict[str, tuple[str, ...]]
    acpi: tuple[Item, ...]
    kexts: tuple[Item, ...]
    drivers: tuple[Item, ...]
    tools: tuple[Item, ...]
    # Extra overlays applied when a feature condition holds, e.g. {"fat32_installer": (path,)}.
    feature_overlays: dict[str, tuple[Path, ...]] = field(default_factory=dict)
    notes: tuple[str, ...] = field(default_factory=tuple)

    @property
    def buildable(self) -> bool:
        return self.status != "research"


def condition_true(when: str | None, features: dict[str, object]) -> bool:
    if not when:
        return True
    if "=" in when:
        key, value = when.split("=", 1)
        if key not in features:
            raise SkullintoshError(f"condition {when!r} names unknown feature {key!r}")
        return str(features[key]) == value
    if when not in features:
        raise SkullintoshError(f"condition {when!r} names an unknown feature")
    return bool(features[when])


def _items(raw: list[dict], kind: str, source: Path) -> tuple[Item, ...]:
    items = []
    for entry in raw:
        unknown = set(entry) - {"name", "when", "flavors", "comment", "arguments"}
        if unknown or "name" not in entry:
            raise SkullintoshError(f"{source}: bad [[{kind}]] entry {entry}")
        flavors = tuple(entry.get("flavors", FLAVORS))
        if not set(flavors) <= set(FLAVORS):
            raise SkullintoshError(f"{source}: [[{kind}]] {entry['name']}: bad flavors {flavors}")
        items.append(
            Item(
                entry["name"],
                entry.get("when"),
                flavors,
                entry.get("comment", ""),
                entry.get("arguments", ""),
            )
        )
    return tuple(items)


def load_profile(root: Path, name: str) -> Profile:
    path = root / "profiles" / name / "profile.toml"
    if not path.is_file():
        available = ", ".join(list_profiles(root)) or "none"
        raise SkullintoshError(f"no profile named {name!r} (available: {available})")
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise SkullintoshError(f"{path}: {exc}") from exc

    meta = data.get("profile", {})
    status = meta.get("status")
    if status not in STATUSES:
        raise SkullintoshError(f"{path}: status must be one of {STATUSES}")
    base = path.parent

    def rel(p: str) -> Path:
        resolved = (base / p).resolve()
        if not resolved.is_file():
            raise SkullintoshError(f"{path}: referenced file {p} does not exist")
        return resolved

    choices = {k: tuple(v) for k, v in data.get("feature_choices", {}).items()}
    features = dict(data.get("features", {}))
    for key, value in features.items():
        if key in choices and value not in choices[key]:
            raise SkullintoshError(f"{path}: feature {key}={value!r} not in {choices[key]}")

    return Profile(
        id=name,
        dir=base,
        title=meta.get("title", name),
        status=status,
        darwin=int(meta["darwin"]),
        smbios_model=meta.get("smbios_model", ""),
        overlays=tuple(rel(p) for p in meta.get("overlays", [])),
        debug_overlays=tuple(rel(p) for p in meta.get("debug_overlays", [])),
        boot_args=tuple(meta.get("boot_args", [])),
        debug_boot_args=tuple(meta.get("debug_boot_args", [])),
        usb_map=rel(meta["usb_map"]) if meta.get("usb_map") else None,
        features=features,
        feature_choices=choices,
        acpi=_items(data.get("acpi", []), "acpi", path),
        kexts=_items(data.get("kexts", []), "kexts", path),
        drivers=_items(data.get("drivers", []), "drivers", path),
        tools=_items(data.get("tools", []), "tools", path),
        feature_overlays={
            cond: tuple(rel(p) for p in paths)
            for cond, paths in data.get("feature_overlays", {}).items()
        },
        notes=tuple(meta.get("notes", [])),
    )


def list_profiles(root: Path) -> list[str]:
    return sorted(p.parent.name for p in (root / "profiles").glob("*/profile.toml"))


def resolve_features(profile: Profile, overrides: list[str]) -> dict[str, object]:
    """Apply ``key=value`` overrides from the command line to the profile defaults."""
    features = dict(profile.features)
    for item in overrides:
        if "=" not in item:
            raise SkullintoshError(f"--set expects key=value, got {item!r}")
        key, value = item.split("=", 1)
        if key not in features:
            raise SkullintoshError(
                f"unknown feature {key!r} for {profile.id} (known: {', '.join(features)})"
            )
        if isinstance(features[key], bool):
            if value.lower() not in ("true", "false"):
                raise SkullintoshError(f"feature {key} is a boolean; use true/false")
            features[key] = value.lower() == "true"
        else:
            allowed = profile.feature_choices.get(key)
            if allowed and value not in allowed:
                raise SkullintoshError(f"feature {key} must be one of {', '.join(allowed)}")
            features[key] = value
    return features


def check_profile_against_manifest(profile: Profile, manifest: Manifest) -> list[str]:
    """Static problems with a profile's kext list (unknown ids, wrong macOS version)."""
    problems = []
    for item in profile.kexts:
        if item.name == "USBMap":
            continue
        if item.name not in manifest.kexts:
            problems.append(f"kext {item.name} is not defined in the manifest")
            continue
        kext = manifest.kexts[item.name]
        if not kext.applies_to(profile.darwin):
            problems.append(
                f"kext {item.name} is built for darwin {kext.darwin_min}-{kext.darwin_max}, "
                f"but profile {profile.id} targets darwin {profile.darwin}"
            )
    return problems
