import pytest

from skullintosh.errors import SkullintoshError
from skullintosh.manifest import load_manifest
from skullintosh.profiles import (
    check_profile_against_manifest,
    list_profiles,
    load_profile,
    resolve_features,
)


def test_expected_profiles_exist(root):
    assert set(list_profiles(root)) >= {"monterey", "ventura", "sonoma", "sequoia", "tahoe"}


def test_only_monterey_is_buildable_today(root):
    statuses = {name: load_profile(root, name).status for name in list_profiles(root)}
    assert statuses["monterey"] == "candidate"
    assert all(s == "research" for n, s in statuses.items() if n != "monterey")
    assert "verified" not in statuses.values(), "verified needs hardware evidence"


@pytest.mark.parametrize("name", ["monterey", "ventura", "sonoma", "sequoia", "tahoe"])
def test_profiles_match_manifest(root, name):
    manifest = load_manifest(root / "manifests" / "dependencies.toml")
    profile = load_profile(root, name)
    assert check_profile_against_manifest(profile, manifest) == []


@pytest.mark.parametrize("name", ["monterey", "ventura", "sonoma", "sequoia", "tahoe"])
def test_every_wifi_choice_selects_at_most_one_kext(root, name):
    profile = load_profile(root, name)
    for choice in profile.feature_choices.get("wifi", ()):
        features = resolve_features(profile, [f"wifi={choice}"])
        chosen = [
            k.name
            for k in profile.kexts
            if k.selected(features, "release") and ("itlwm" in k.name.lower())
        ]
        assert len(chosen) == (0 if choice == "none" else 1), (choice, chosen)


def test_sequoia_and_tahoe_offer_no_airportitlwm(root):
    for name in ("sequoia", "tahoe"):
        assert "airportitlwm" not in load_profile(root, name).feature_choices["wifi"]


def test_feature_overrides_are_validated(root):
    profile = load_profile(root, "monterey")
    assert resolve_features(profile, ["bluetooth=false"])["bluetooth"] is False
    with pytest.raises(SkullintoshError):
        resolve_features(profile, ["bluetooth=maybe"])
    with pytest.raises(SkullintoshError):
        resolve_features(profile, ["wifi=broadcom"])
    with pytest.raises(SkullintoshError):
        resolve_features(profile, ["turbo=true"])


def test_debug_only_tools(root):
    profile = load_profile(root, "monterey")
    tools = {t.name: t for t in profile.tools}
    assert not tools["OpenShell.efi"].selected(profile.features, "release")
    assert tools["OpenShell.efi"].selected(profile.features, "debug")
