"""Schema-checked merging of config overlays onto OpenCore's ``Sample.plist``.

Overlays are partial plists. Merging rules:

* dictionaries merge recursively; every key in an overlay must already exist in the base,
  so a typo or a key that OpenCore removed fails loudly instead of being silently ignored;
* the replacement value must have the same type as the value it replaces;
* lists are replaced wholesale;
* under the free-form dictionaries in ``FREEFORM`` (device paths, NVRAM GUIDs) any key is
  allowed;
* keys starting with ``#`` are documentation for reviewers and are dropped.
"""

from __future__ import annotations

import copy
import plistlib
from pathlib import Path
from typing import Any
from xml.parsers.expat import ExpatError

from skullintosh.errors import SkullintoshError

# Collections Skullintosh owns completely: emptied before overlays/generators fill them, so
# nothing from the OpenCore sample leaks into a build.
OWNED_LISTS = (
    "ACPI/Add",
    "ACPI/Delete",
    "ACPI/Patch",
    "Booter/MmioWhitelist",
    "Booter/Patch",
    "Kernel/Add",
    "Kernel/Block",
    "Kernel/Force",
    "Kernel/Patch",
    "Misc/Entries",
    "Misc/Tools",
    "UEFI/Drivers",
    "UEFI/ReservedMemory",
)
OWNED_DICTS = ("DeviceProperties/Add", "NVRAM/Add")
FREEFORM = (
    "DeviceProperties/Add",
    "DeviceProperties/Delete",
    "NVRAM/Add",
    "NVRAM/Delete",
    "NVRAM/LegacySchema",
)


def load_plist(path: Path) -> dict:
    try:
        with open(path, "rb") as fh:
            data = plistlib.load(fh)
    except (OSError, plistlib.InvalidFileException, ValueError, ExpatError) as exc:
        raise SkullintoshError(f"cannot parse plist {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise SkullintoshError(f"{path}: top level must be a dictionary")
    return data


def get_path(data: dict, path: str) -> Any:
    node: Any = data
    for part in path.split("/"):
        node = node[part]
    return node


def set_path(data: dict, path: str, value: Any) -> None:
    *parents, last = path.split("/")
    node = data
    for part in parents:
        node = node[part]
    node[last] = value


def reset_owned(config: dict) -> None:
    for path in OWNED_LISTS:
        set_path(config, path, [])
    for path in OWNED_DICTS:
        set_path(config, path, {})


def _type_name(value: Any) -> str:
    return type(value).__name__


def _strip_comments(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _strip_comments(v) for k, v in value.items() if not k.startswith("#")}
    if isinstance(value, list):
        return [_strip_comments(v) for v in value]
    return value


def _merge(base: dict, overlay: dict, path: str, source: str) -> None:
    freeform = path in FREEFORM or any(path.startswith(f + "/") for f in FREEFORM)
    for key, value in overlay.items():
        if key.startswith("#"):
            continue
        child = f"{path}/{key}" if path else key
        if key not in base:
            if not freeform:
                raise SkullintoshError(
                    f"{source}: {child} does not exist in this OpenCore version's schema"
                )
            base[key] = _strip_comments(copy.deepcopy(value))
            continue
        current = base[key]
        if isinstance(current, dict) and isinstance(value, dict):
            _merge(current, value, child, source)
            continue
        # bool is a subclass of int; compare exact types.
        if type(current) is not type(value) and not freeform:
            raise SkullintoshError(
                f"{source}: {child} must be {_type_name(current)}, overlay has {_type_name(value)}"
            )
        base[key] = _strip_comments(copy.deepcopy(value))


def apply_overlay(config: dict, overlay: dict, source: str) -> None:
    _merge(config, overlay, "", source)
