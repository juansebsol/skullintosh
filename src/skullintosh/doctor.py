"""Check that the local environment can build and validate Skullintosh EFIs."""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

from skullintosh.errors import SkullintoshError
from skullintosh.fetch import cache_dir, cached_path
from skullintosh.manifest import load_manifest
from skullintosh.profiles import check_profile_against_manifest, list_profiles, load_profile
from skullintosh.usbmap import load_usb_map
from skullintosh.util import relpath_for_display, sha256_file
from skullintosh.validate import ERROR, INFO, WARNING, Finding, ocvalidate_member


def run_doctor(root: Path) -> list[Finding]:
    out: list[Finding] = []
    out.append(Finding(INFO, "python", sys.version.split()[0]))
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        out.append(
            Finding(
                WARNING,
                "root",
                "running as root is never needed; Skullintosh does "
                "not touch disks or EFI partitions",
            )
        )

    try:
        manifest = load_manifest(root / "manifests" / "dependencies.toml")
        out.append(
            Finding(
                INFO,
                "manifest",
                f"{len(manifest.packages)} packages, {len(manifest.kexts)} kexts pinned",
            )
        )
    except SkullintoshError as exc:
        return [*out, Finding(ERROR, "manifest", str(exc))]

    for name in list_profiles(root):
        try:
            profile = load_profile(root, name)
            problems = check_profile_against_manifest(profile, manifest)
            if profile.usb_map:
                load_usb_map(profile.usb_map)
        except SkullintoshError as exc:
            out.append(Finding(ERROR, f"profile:{name}", str(exc)))
            continue
        for p in problems:
            out.append(Finding(ERROR, f"profile:{name}", p))
        if not problems:
            out.append(Finding(INFO, f"profile:{name}", f"status {profile.status}"))

    cache = cache_dir(root)
    cached = bad = 0
    for pkg in manifest.packages.values():
        for asset in pkg.assets.values():
            path = cached_path(cache, asset)
            if path.is_file():
                if sha256_file(path) == asset.sha256:
                    cached += 1
                else:
                    bad += 1
                    out.append(
                        Finding(
                            ERROR,
                            "cache",
                            f"{asset.name} in cache fails its checksum; delete it and re-fetch",
                        )
                    )
    total = sum(len(p.assets) for p in manifest.packages.values())
    out.append(
        Finding(
            INFO,
            "cache",
            f"{cached}/{total} assets cached and verified in {relpath_for_display(cache)}",
        )
    )

    member = ocvalidate_member()
    if member:
        out.append(Finding(INFO, "ocvalidate", f"will use {member} from the pinned OpenCore"))
    else:
        out.append(
            Finding(
                WARNING,
                "ocvalidate",
                "no ocvalidate build for this host; validation will skip the schema check",
            )
        )
    for tool in ("git", "shellcheck"):
        if not shutil.which(tool):
            out.append(Finding(WARNING, tool, f"{tool} not found (only needed for development)"))
    return out
