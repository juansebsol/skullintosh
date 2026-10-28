"""Download pinned release assets into a local cache and verify their checksums."""

from __future__ import annotations

import json
import os
import shutil
import tempfile
import urllib.request
from pathlib import Path

from skullintosh.errors import SkullintoshError
from skullintosh.manifest import Asset, Manifest
from skullintosh.util import sha256_file

USER_AGENT = "skullintosh-fetch"


def cache_dir(root: Path) -> Path:
    env = os.environ.get("SKULLINTOSH_CACHE")
    return Path(env) if env else root / ".cache" / "downloads"


def cached_path(cache: Path, asset: Asset) -> Path:
    return cache / asset.package / asset.name


def _download(url: str, dest: Path) -> None:
    if not url.startswith("https://github.com/"):
        raise SkullintoshError(f"refusing non-GitHub download URL {url}")
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})  # noqa: S310
    dest.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=dest.parent, prefix=".part-")
    try:
        with os.fdopen(fd, "wb") as out, urllib.request.urlopen(request, timeout=120) as resp:  # noqa: S310
            shutil.copyfileobj(resp, out)
        os.replace(tmp_name, dest)
    except BaseException:
        Path(tmp_name).unlink(missing_ok=True)
        raise


def ensure_asset(cache: Path, asset: Asset, *, offline: bool = False) -> Path:
    """Return the verified local path of ``asset``, downloading it if needed."""
    path = cached_path(cache, asset)
    if path.is_file() and sha256_file(path) == asset.sha256:
        return path
    if offline:
        raise SkullintoshError(f"{asset.name} is not in the cache and --offline was given")
    try:
        _download(asset.url, path)
    except OSError as exc:
        raise SkullintoshError(f"download failed for {asset.url}: {exc}") from exc
    actual = sha256_file(path)
    if actual != asset.sha256:
        bad = path.with_name(path.name + ".rejected")
        os.replace(path, bad)
        raise SkullintoshError(
            f"checksum mismatch for {asset.name}\n  expected {asset.sha256}\n  actual   {actual}\n"
            f"  the download was moved to {bad.name}; nothing from it will be used"
        )
    return path


def github_digest(repo: str, tag: str, name: str) -> str | None:
    """GitHub's published sha256 for a release asset, if it exposes one."""
    url = f"https://api.github.com/repos/{repo}/releases/tags/{tag}"
    request = urllib.request.Request(  # noqa: S310 - fixed https URL
        url, headers={"User-Agent": USER_AGENT, "Accept": "application/vnd.github+json"}
    )
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(request, timeout=60) as resp:  # noqa: S310
        release = json.load(resp)
    for asset in release.get("assets", []):
        if asset.get("name") == name:
            digest = asset.get("digest") or ""
            return digest.removeprefix("sha256:") or None
    raise SkullintoshError(f"{repo}@{tag} has no asset named {name}")


def pin_assets(manifest: Manifest, cache: Path, package_ids: list[str]) -> dict[str, dict]:
    """Download assets without a pinned hash and report the hashes to write into the manifest."""
    results: dict[str, dict] = {}
    for pid in package_ids:
        package = manifest.package(pid)
        for key, asset in package.assets.items():
            path = cached_path(cache, asset)
            _download(asset.url, path)
            local = sha256_file(path)
            published = github_digest(package.repo, package.tag, asset.name)
            if published and published != local:
                raise SkullintoshError(
                    f"{asset.name}: local sha256 {local} != GitHub digest {published}"
                )
            if asset.sha256 and asset.sha256 != local:
                raise SkullintoshError(
                    f"{asset.name}: pinned sha256 differs from the published file; "
                    "a release asset was replaced upstream - investigate before re-pinning"
                )
            results[f"{pid}.{key}"] = {
                "name": asset.name,
                "sha256": local,
                "github_digest": published or "not published",
            }
    return results
