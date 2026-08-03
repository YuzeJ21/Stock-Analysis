import os
from pathlib import Path

import pytest

from src.readiness_source_boundary import (
    ReadinessSourceBoundaryError,
    validate_readiness_source_boundary,
)


NAMED_READINESS_INPUTS = (
    "universe.csv",
    "universe_master.csv",
    "universe_active.csv",
    "holdings.csv",
    "prices.csv",
    "fundamentals.csv",
    "earnings.csv",
    "analyst_estimates.csv",
    "peers.csv",
    "peer_candidates.csv",
)


def _profile_dir(root: Path, profile: str) -> Path:
    return root / {"default": "data", "demo": "data/demo", "local": "data/local"}[profile]


def _make_profile(root: Path, profile: str = "default") -> Path:
    data_dir = _profile_dir(root, profile)
    data_dir.mkdir(parents=True)
    return data_dir


def _replace_with_symlink(path: Path, target: Path) -> None:
    if path.is_dir() and not path.is_symlink():
        path.rmdir()
    elif path.exists() or path.is_symlink():
        path.unlink()
    path.symlink_to(target, target_is_directory=target.is_dir())


@pytest.mark.parametrize(
    ("profile", "expected_data", "expected_outputs"),
    [
        ("default", "data", "outputs"),
        ("demo", "data/demo", "outputs/demo"),
        ("local", "data/local", "outputs/local"),
    ],
)
def test_source_boundary_returns_only_validated_named_profile_paths(
    tmp_path: Path, profile: str, expected_data: str, expected_outputs: str
):
    _make_profile(tmp_path, profile)

    selected = validate_readiness_source_boundary(tmp_path, profile)

    assert selected.name == profile
    assert selected.data_dir == (tmp_path / expected_data).resolve()
    assert selected.outputs_dir == (tmp_path / expected_outputs).resolve()


@pytest.mark.parametrize("profile", ["", "unknown", " default", "DEMO"])
def test_source_boundary_rejects_any_profile_name_outside_the_exact_allowlist(tmp_path: Path, profile: str):
    _make_profile(tmp_path)

    with pytest.raises(ReadinessSourceBoundaryError, match="default, demo, local"):
        validate_readiness_source_boundary(tmp_path, profile)


def test_source_boundary_keeps_missing_optional_named_inputs_explicitly_absent(tmp_path: Path):
    data_dir = _make_profile(tmp_path)

    selected = validate_readiness_source_boundary(tmp_path, "default")

    assert selected.data_dir == data_dir
    assert all(not (selected.data_dir / name).exists() for name in NAMED_READINESS_INPUTS)


@pytest.mark.parametrize("profile", ["default", "demo", "local"])
@pytest.mark.parametrize("target_scope", ["inside", "outside"])
def test_source_boundary_rejects_symlinked_profile_directory_before_resolving(
    tmp_path: Path, profile: str, target_scope: str
):
    data_dir = _make_profile(tmp_path, profile)
    target = tmp_path / ("inside-target" if target_scope == "inside" else "../outside-target")
    target.mkdir(parents=True, exist_ok=True)
    _replace_with_symlink(data_dir, target)

    with pytest.raises(ReadinessSourceBoundaryError, match="symbolic link"):
        validate_readiness_source_boundary(tmp_path, profile)


@pytest.mark.parametrize("target_scope", ["inside", "outside"])
def test_source_boundary_rejects_symlinked_repository_data_component(tmp_path: Path, target_scope: str):
    target = tmp_path / ("inside-data" if target_scope == "inside" else "../outside-data")
    target.mkdir(parents=True)
    (tmp_path / "data").symlink_to(target, target_is_directory=True)

    with pytest.raises(ReadinessSourceBoundaryError, match="symbolic link"):
        validate_readiness_source_boundary(tmp_path, "default")


@pytest.mark.parametrize("name", NAMED_READINESS_INPUTS)
@pytest.mark.parametrize("target_scope", ["inside", "outside"])
def test_source_boundary_rejects_every_named_input_symlink_without_following_it(
    tmp_path: Path, name: str, target_scope: str
):
    data_dir = _make_profile(tmp_path)
    target_root = tmp_path if target_scope == "inside" else tmp_path.parent
    target = target_root / f"target-{name}"
    target.write_text("ticker\n", encoding="utf-8")
    (data_dir / name).symlink_to(target)

    with pytest.raises(ReadinessSourceBoundaryError, match=name):
        validate_readiness_source_boundary(tmp_path, "default")


@pytest.mark.parametrize("target_scope", ["inside", "outside"])
def test_source_boundary_rejects_symlinked_intermediate_staged_component(tmp_path: Path, target_scope: str):
    data_dir = _make_profile(tmp_path)
    staged = data_dir / "staged"
    staged.mkdir()
    target_root = tmp_path if target_scope == "inside" else tmp_path.parent
    target = target_root / f"staged-prices-{target_scope}"
    target.mkdir(exist_ok=True)
    (staged / "prices").symlink_to(target, target_is_directory=True)

    with pytest.raises(ReadinessSourceBoundaryError, match="symbolic link"):
        validate_readiness_source_boundary(tmp_path, "default")


@pytest.mark.parametrize("kind", ["directory", "fifo"])
def test_source_boundary_rejects_existing_named_inputs_that_are_not_regular_files(
    tmp_path: Path, kind: str
):
    data_dir = _make_profile(tmp_path)
    source = data_dir / "prices.csv"
    if kind == "directory":
        source.mkdir()
    else:
        os.mkfifo(source)

    with pytest.raises(ReadinessSourceBoundaryError, match="regular file"):
        validate_readiness_source_boundary(tmp_path, "default")
