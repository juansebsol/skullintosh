"""Command-line interface.

No command writes to an EFI System Partition, edits partitions, or changes UEFI boot entries.
Output goes to ``build/``, ``dist/`` and ``.cache/`` inside the repository.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from skullintosh import __version__
from skullintosh.build import BuildRequest, build, build_digest, default_output
from skullintosh.doctor import run_doctor
from skullintosh.errors import SkullintoshError
from skullintosh.fetch import cache_dir, ensure_asset, pin_assets
from skullintosh.manifest import load_manifest
from skullintosh.package import package_build
from skullintosh.profiles import list_profiles, load_profile
from skullintosh.report import environment_report, inventory_report
from skullintosh.secretscan import candidate_files, scan_paths
from skullintosh.util import find_repo_root, relpath_for_display
from skullintosh.validate import ERROR, Finding, has_errors, validate_build


def _print_findings(findings: list[Finding], quiet_info: bool = False) -> None:
    for f in findings:
        if quiet_info and f.level == "info":
            continue
        print(f)
    errors = sum(f.level == ERROR for f in findings)
    warnings = sum(f.level == "warning" for f in findings)
    print(f"\n{errors} error(s), {warnings} warning(s)")


def _build_dir(root: Path, args: argparse.Namespace) -> Path:
    if getattr(args, "build_dir", None):
        return Path(args.build_dir).resolve()
    return default_output(root, args.target, args.flavor, getattr(args, "personal", False))


def cmd_doctor(root: Path, args: argparse.Namespace) -> int:
    findings = run_doctor(root)
    _print_findings(findings)
    return 1 if has_errors(findings) else 0


def cmd_fetch(root: Path, args: argparse.Namespace) -> int:
    manifest = load_manifest(root / "manifests" / "dependencies.toml")
    cache = cache_dir(root)
    packages = args.packages or list(manifest.packages)
    for pid in packages:
        for asset in manifest.package(pid).assets.values():
            path = ensure_asset(cache, asset, offline=args.offline)
            print(f"ok  {asset.sha256[:16]}  {relpath_for_display(path)}")
    return 0


def cmd_pin(root: Path, args: argparse.Namespace) -> int:
    manifest = load_manifest(root / "manifests" / "dependencies.toml", require_hashes=False)
    results = pin_assets(manifest, cache_dir(root), args.packages)
    print(json.dumps(results, indent=2))
    print("\nCopy the sha256 values into manifests/dependencies.toml after reviewing them.")
    return 0


def cmd_build(root: Path, args: argparse.Namespace) -> int:
    req = BuildRequest(
        profile=args.target,
        flavor=args.flavor,
        overrides=args.set or [],
        smbios=Path(args.smbios).resolve() if args.smbios else None,
        output=Path(args.output).resolve() if args.output else None,
        offline=args.offline,
        allow_research=args.allow_research,
    )
    out = build(root, req)
    print(f"built {relpath_for_display(out)}")
    print(f"tree digest {build_digest(out)}")
    if req.smbios:
        print("NOTE: this build contains your personal SMBIOS identity. Do not share it.")
    if args.no_validate:
        return 0
    findings = validate_build(root, out, ocvalidate=args.ocvalidate, offline=args.offline)
    _print_findings(findings, quiet_info=False)
    return 1 if has_errors(findings) else 0


def cmd_validate(root: Path, args: argparse.Namespace) -> int:
    build_dir = _build_dir(root, args)
    findings = validate_build(root, build_dir, ocvalidate=args.ocvalidate, offline=args.offline)
    _print_findings(findings)
    return 1 if has_errors(findings) else 0


def cmd_package(root: Path, args: argparse.Namespace) -> int:
    build_dir = _build_dir(root, args)
    dist = Path(args.dist).resolve() if args.dist else root / "dist"
    out = package_build(root, build_dir, dist, offline=args.offline, ocvalidate=args.ocvalidate)
    print(f"packaged {relpath_for_display(out)}")
    print(out.with_name(out.name + ".sha256").read_text().strip())
    return 0


def cmd_report(root: Path, args: argparse.Namespace) -> int:
    if args.input:
        text = inventory_report(root, [Path(p) for p in args.input])
    else:
        text = environment_report(root)
    if args.output:
        Path(args.output).write_text(text)
        print(f"wrote {args.output}; review it before sharing")
    else:
        print(text)
    return 0


def cmd_scan_secrets(root: Path, args: argparse.Namespace) -> int:
    paths = [Path(p).resolve() for p in args.paths] if args.paths else candidate_files(root)
    files = []
    for p in paths:
        files.extend(sorted(x for x in p.rglob("*") if x.is_file()) if p.is_dir() else [p])
    hits = scan_paths(files, root)
    for hit in hits:
        print(hit)
    print(f"{len(hits)} potential identifier(s) in {len(files)} file(s)")
    return 1 if hits else 0


def cmd_profiles(root: Path, args: argparse.Namespace) -> int:
    for name in list_profiles(root):
        p = load_profile(root, name)
        print(f"{name:10} {p.status:10} darwin {p.darwin:<3} {p.smbios_model or '-':12} {p.title}")
    return 0


def _add_target(p: argparse.ArgumentParser) -> None:
    p.add_argument("--target", default="monterey", help="profile name (default: monterey)")
    p.add_argument("--flavor", choices=("release", "debug"), default="release")


def _add_ocvalidate(p: argparse.ArgumentParser, default: str = "auto") -> None:
    p.add_argument(
        "--ocvalidate",
        choices=("auto", "require", "skip"),
        default=default,
        help="run OpenCore's ocvalidate from the pinned release",
    )


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="skullintosh", description=__doc__.splitlines()[0])
    parser.add_argument("--version", action="version", version=f"skullintosh {__version__}")
    parser.add_argument("--root", help="repository root (default: auto-detect)")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("doctor", help="check tools, manifest, profiles and cache")

    p = sub.add_parser("fetch", help="download and verify pinned release assets")
    p.add_argument("packages", nargs="*", help="package ids (default: all)")
    p.add_argument("--offline", action="store_true", help="only verify what is cached")

    p = sub.add_parser("pin", help="maintainers: hash new release assets for the manifest")
    p.add_argument("packages", nargs="+")

    p = sub.add_parser("build", help="build an EFI for a profile into build/")
    _add_target(p)
    p.add_argument(
        "--set",
        action="append",
        metavar="FEATURE=VALUE",
        help="override a profile feature, e.g. --set wifi=airportitlwm",
    )
    p.add_argument(
        "--smbios",
        metavar="FILE",
        help="local TOML with your SMBIOS identity (keep it under local/)",
    )
    p.add_argument("--output", help="output directory (default: build/<profile>-<flavor>)")
    p.add_argument("--offline", action="store_true")
    p.add_argument(
        "--allow-research", action="store_true", help="build a research profile for experiments"
    )
    p.add_argument("--no-validate", action="store_true")
    _add_ocvalidate(p)

    p = sub.add_parser("validate", help="validate a build")
    _add_target(p)
    p.add_argument("--build-dir", help="explicit build directory")
    p.add_argument("--personal", action="store_true", help="validate the -personal build")
    p.add_argument("--offline", action="store_true")
    _add_ocvalidate(p)

    p = sub.add_parser("package", help="zip a validated, non-personal build into dist/")
    _add_target(p)
    p.add_argument("--build-dir")
    p.add_argument("--dist")
    p.add_argument("--offline", action="store_true")
    _add_ocvalidate(p, default="require")

    p = sub.add_parser("report", help="sanitized environment or hardware-inventory report")
    p.add_argument("--input", nargs="+", help="inventory files/directories to sanitize")
    p.add_argument("--output", help="write to a file instead of stdout")

    p = sub.add_parser("scan-secrets", help="look for serials, MACs and keys in files")
    p.add_argument("paths", nargs="*", help="files/directories (default: the repository)")

    sub.add_parser("profiles", help="list profiles and their status")
    return parser


COMMANDS = {
    "doctor": cmd_doctor,
    "fetch": cmd_fetch,
    "pin": cmd_pin,
    "build": cmd_build,
    "validate": cmd_validate,
    "package": cmd_package,
    "report": cmd_report,
    "scan-secrets": cmd_scan_secrets,
    "profiles": cmd_profiles,
}


def main(argv: list[str] | None = None) -> int:
    args = make_parser().parse_args(argv)
    try:
        root = Path(args.root).resolve() if args.root else find_repo_root()
        return COMMANDS[args.command](root, args)
    except SkullintoshError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        return 130
