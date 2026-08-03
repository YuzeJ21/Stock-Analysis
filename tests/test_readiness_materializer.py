import inspect
import os
from pathlib import Path

import pandas as pd
import pytest

import src.readiness_materializer as readiness_materializer
from src.readiness_materializer import (
    ReadinessMaterializationError,
    materialize_readiness_snapshot,
)


EXPECTED_REPORT_NAMES = (
    "universe_coverage_report",
    "price_coverage_report",
    "fundamentals_coverage_report",
    "dcf_readiness_report",
    "peer_readiness_report",
    "earnings_readiness_report",
    "analyst_estimates_readiness_report",
    "ticker_readiness_report",
    "feature_readiness_summary",
    "peer_unlock_worklist",
    "data_source_status",
)
EXPECTED_FILENAMES = tuple(f"{name}.csv" for name in EXPECTED_REPORT_NAMES)


def _profile_dir(root: Path, profile: str) -> Path:
    return root / {"default": "data", "demo": "data/demo", "local": "data/local"}[profile]


def _write_fixture(root: Path, profile: str = "default") -> Path:
    data_dir = _profile_dir(root, profile)
    data_dir.mkdir(parents=True)
    pd.DataFrame(
        [
            {
                "ticker": "AAA",
                "name": "Alpha Corp",
                "exchange": "NYSE",
                "asset_type": "company",
                "source": "test_fixture",
            }
        ]
    ).to_csv(data_dir / "universe_master.csv", index=False)
    pd.DataFrame([{"ticker": "AAA", "scope": "active_research", "theme": "Test"}]).to_csv(
        data_dir / "universe_active.csv", index=False
    )
    pd.DataFrame(columns=["ticker", "shares"]).to_csv(data_dir / "holdings.csv", index=False)
    pd.DataFrame(columns=["ticker", "date", "close"]).to_csv(data_dir / "prices.csv", index=False)
    pd.DataFrame(columns=["ticker", "source"]).to_csv(data_dir / "fundamentals.csv", index=False)
    pd.DataFrame(columns=["ticker", "source"]).to_csv(data_dir / "earnings.csv", index=False)
    pd.DataFrame(columns=["ticker", "source"]).to_csv(data_dir / "analyst_estimates.csv", index=False)
    pd.DataFrame(columns=["ticker", "peer_ticker", "peer_group", "source"]).to_csv(
        data_dir / "peers.csv", index=False
    )
    return data_dir


def _frames(value: str = "new") -> dict[str, pd.DataFrame]:
    return {name: pd.DataFrame([{"marker": value}]) for name in EXPECTED_REPORT_NAMES}


def _manifest(root: Path) -> dict[str, tuple[str, bytes | None]]:
    manifest = {".": ("directory", None)}
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            manifest[relative] = ("symlink", os.readlink(path).encode())
        elif path.is_dir():
            manifest[relative] = ("directory", None)
        else:
            manifest[relative] = ("file", path.read_bytes())
    return manifest


def _snapshot_values(destination: Path) -> set[str]:
    if not destination.exists():
        return set()
    return {
        str(pd.read_csv(path).loc[0, "marker"])
        for path in destination.glob("*.csv")
        if path.is_file()
    }


def _install_builder(monkeypatch: pytest.MonkeyPatch, frames: dict[str, pd.DataFrame]):
    calls: list[dict[str, object]] = []

    def build(root, **kwargs):
        calls.append({"root": root, **kwargs})
        return frames

    monkeypatch.setattr(readiness_materializer, "build_ticker_readiness_report", build)
    return calls


def test_missing_confirmation_fails_before_creating_outputs(tmp_path: Path):
    _write_fixture(tmp_path)

    with pytest.raises(ReadinessMaterializationError, match="confirm_materialize=True"):
        materialize_readiness_snapshot(tmp_path, profile="default")

    assert not (tmp_path / "outputs").exists()


@pytest.mark.parametrize("profile", ["", "unknown", " default", "DEMO"])
def test_empty_or_unknown_profile_fails_closed(tmp_path: Path, profile: str):
    _write_fixture(tmp_path)

    with pytest.raises(ReadinessMaterializationError, match="default, demo, local"):
        materialize_readiness_snapshot(tmp_path, profile=profile, confirm_materialize=True)

    assert not (tmp_path / "outputs").exists()


def test_materializer_has_no_output_parameter_and_environment_cannot_redirect_destination(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    _write_fixture(tmp_path)
    redirected = tmp_path / "redirected"
    monkeypatch.setenv("STOCK_RESEARCH_OUTPUT_DIR", str(redirected))
    monkeypatch.setenv("OUTPUT_DIR", str(redirected))
    calls = _install_builder(monkeypatch, _frames())

    result = materialize_readiness_snapshot(tmp_path, profile="default", confirm_materialize=True)

    assert "output_dir" not in inspect.signature(materialize_readiness_snapshot).parameters
    assert result.output_dir == (tmp_path / "outputs/local/derived/default").resolve()
    assert not redirected.exists()
    assert calls == [
        {
            "root": tmp_path.resolve(),
            "data_dir": (tmp_path / "data").resolve(),
            "output_dir": (tmp_path / "outputs").resolve(),
            "write_outputs": False,
        }
    ]


@pytest.mark.parametrize("profile", ["default", "demo", "local"])
def test_confirmed_materialization_writes_one_exact_eleven_file_local_package(
    tmp_path: Path, profile: str
):
    _write_fixture(tmp_path, profile)
    before = _manifest(tmp_path)

    result = materialize_readiness_snapshot(tmp_path, profile=profile, confirm_materialize=True)

    destination = tmp_path / "outputs/local/derived" / profile
    assert result.profile == profile
    assert result.output_dir == destination.resolve()
    assert result.files == tuple(sorted(destination.resolve() / name for name in EXPECTED_FILENAMES))
    assert set(result.row_counts) == set(EXPECTED_REPORT_NAMES)
    assert set(path.name for path in destination.iterdir()) == set(EXPECTED_FILENAMES)
    assert all(path.is_file() and not path.is_symlink() for path in destination.iterdir())
    after = _manifest(tmp_path)
    added = set(after) - set(before)
    expected_added = {
        "outputs",
        "outputs/local",
        "outputs/local/derived",
        f"outputs/local/derived/{profile}",
        *(f"outputs/local/derived/{profile}/{name}" for name in EXPECTED_FILENAMES),
    }
    assert added == expected_added
    assert {key: after[key] for key in before} == before
    assert not (data_dir := _profile_dir(tmp_path, profile) / "reports").exists()
    assert not (tmp_path / "outputs" / "feature_readiness_summary.csv").exists()
    assert not (tmp_path / "outputs" / "peer_unlock_worklist.csv").exists()


def test_second_run_reuses_fixed_paths_without_duplicate_or_backup_copy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    _write_fixture(tmp_path)
    _install_builder(monkeypatch, _frames("first"))
    first = materialize_readiness_snapshot(tmp_path, profile="default", confirm_materialize=True)
    monkeypatch.setattr(readiness_materializer, "build_ticker_readiness_report", lambda *_args, **_kwargs: _frames("second"))

    second = materialize_readiness_snapshot(tmp_path, profile="default", confirm_materialize=True)

    assert second.files == first.files
    assert _snapshot_values(second.output_dir) == {"second"}
    all_files = [path for path in (tmp_path / "outputs").rglob("*") if path.is_file()]
    assert len(all_files) == 11
    assert {path.name for path in all_files} == set(EXPECTED_FILENAMES)
    assert not any("backup" in path.name or "staging" in path.name for path in (tmp_path / "outputs").rglob("*"))


def test_unexpected_operator_file_in_fixed_destination_is_never_overwritten_or_removed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    _write_fixture(tmp_path)
    destination = tmp_path / "outputs/local/derived/default"
    destination.mkdir(parents=True)
    operator_file = destination / "operator-notes.txt"
    operator_file.write_text("keep me", encoding="utf-8")
    calls = _install_builder(monkeypatch, _frames())

    with pytest.raises(ReadinessMaterializationError, match="unexpected entry"):
        materialize_readiness_snapshot(tmp_path, profile="default", confirm_materialize=True)

    assert operator_file.read_text(encoding="utf-8") == "keep me"
    assert calls == []


def test_source_symlink_fails_before_builder_or_output_creation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    data_dir = _write_fixture(tmp_path)
    inside = tmp_path / "inside-prices.csv"
    inside.write_text("ticker,date,close\nAAA,2026-01-01,1\n", encoding="utf-8")
    (data_dir / "prices.csv").unlink()
    (data_dir / "prices.csv").symlink_to(inside)
    calls = _install_builder(monkeypatch, _frames())

    with pytest.raises(ReadinessMaterializationError, match="symbolic link"):
        materialize_readiness_snapshot(tmp_path, profile="default", confirm_materialize=True)

    assert calls == []
    assert not (tmp_path / "outputs").exists()


@pytest.mark.parametrize(
    "component",
    ["outputs", "local", "derived", "profile", "staging", "backup", "expected_file"],
)
@pytest.mark.parametrize("target_scope", ["inside", "outside"])
def test_every_destination_component_and_entry_rejects_symlinks_before_build(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, component: str, target_scope: str
):
    _write_fixture(tmp_path)
    root = tmp_path / "outputs"
    local = root / "local"
    derived = local / "derived"
    destination = derived / "default"
    staging = derived / ".default.readiness-staging"
    backup = derived / ".default.readiness-backup"
    target_root = tmp_path if target_scope == "inside" else tmp_path.parent
    target = target_root / f"destination-target-{component}-{target_scope}"
    if component == "expected_file":
        target.write_text("marker\noperator\n", encoding="utf-8")
    else:
        target.mkdir(exist_ok=True)
    path = {
        "outputs": root,
        "local": local,
        "derived": derived,
        "profile": destination,
        "staging": staging,
        "backup": backup,
        "expected_file": destination / EXPECTED_FILENAMES[0],
    }[component]
    path.parent.mkdir(parents=True, exist_ok=True)
    if component == "expected_file":
        for name in EXPECTED_FILENAMES[1:]:
            (destination / name).write_text("marker\nold\n", encoding="utf-8")
    path.symlink_to(target, target_is_directory=target.is_dir())
    calls = _install_builder(monkeypatch, _frames())

    with pytest.raises(ReadinessMaterializationError, match="symbolic link|recovery"):
        materialize_readiness_snapshot(tmp_path, profile="default", confirm_materialize=True)

    assert calls == []


def test_builder_report_contract_must_equal_all_eleven_names(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    _write_fixture(tmp_path)
    incomplete = _frames()
    incomplete.pop("data_source_status")
    _install_builder(monkeypatch, incomplete)

    with pytest.raises(ReadinessMaterializationError, match="report contract"):
        materialize_readiness_snapshot(tmp_path, profile="default", confirm_materialize=True)

    assert not (tmp_path / "outputs").exists()


def test_staging_residue_appearing_during_composition_fails_before_mutation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    _write_fixture(tmp_path)
    staging = tmp_path / "outputs/local/derived/.default.readiness-staging"
    operator_file = staging / "operator-recovery.txt"

    def build(*_args, **_kwargs):
        staging.mkdir(parents=True)
        operator_file.write_text("do not remove", encoding="utf-8")
        return _frames("new")

    serialize_calls = []
    original_serialize = readiness_materializer._serialize_staging

    def track_serialize(*args, **kwargs):
        serialize_calls.append((args, kwargs))
        return original_serialize(*args, **kwargs)

    monkeypatch.setattr(readiness_materializer, "build_ticker_readiness_report", build)
    monkeypatch.setattr(readiness_materializer, "_serialize_staging", track_serialize)

    with pytest.raises(ReadinessMaterializationError, match="operator recovery"):
        materialize_readiness_snapshot(tmp_path, profile="default", confirm_materialize=True)

    assert operator_file.read_text(encoding="utf-8") == "do not remove"
    assert serialize_calls == []
    assert not (staging.parent / "default").exists()


def test_operator_destination_entry_appearing_during_composition_fails_before_mutation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    _write_fixture(tmp_path)
    destination = tmp_path / "outputs/local/derived/default"
    operator_file = destination / "operator-notes.txt"

    def build(*_args, **_kwargs):
        destination.mkdir(parents=True)
        operator_file.write_text("keep me", encoding="utf-8")
        return _frames("new")

    serialize_calls = []
    original_serialize = readiness_materializer._serialize_staging

    def track_serialize(*args, **kwargs):
        serialize_calls.append((args, kwargs))
        return original_serialize(*args, **kwargs)

    monkeypatch.setattr(readiness_materializer, "build_ticker_readiness_report", build)
    monkeypatch.setattr(readiness_materializer, "_serialize_staging", track_serialize)

    with pytest.raises(ReadinessMaterializationError, match="unexpected entry"):
        materialize_readiness_snapshot(tmp_path, profile="default", confirm_materialize=True)

    assert operator_file.read_text(encoding="utf-8") == "keep me"
    assert serialize_calls == []
    assert not (destination.parent / ".default.readiness-staging").exists()


def test_complete_backup_cleanup_failure_rolls_back_to_prior_snapshot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    _write_fixture(tmp_path)
    _install_builder(monkeypatch, _frames("old"))
    first = materialize_readiness_snapshot(tmp_path, profile="default", confirm_materialize=True)
    monkeypatch.setattr(readiness_materializer, "build_ticker_readiness_report", lambda *_args, **_kwargs: _frames("new"))
    original_remove = readiness_materializer.shutil.rmtree

    def fail_complete_backup_cleanup(path, *args, **kwargs):
        if Path(path).name == ".default.readiness-backup":
            raise OSError("backup cleanup failed before removal")
        return original_remove(path, *args, **kwargs)

    monkeypatch.setattr(readiness_materializer.shutil, "rmtree", fail_complete_backup_cleanup)

    with pytest.raises(ReadinessMaterializationError, match="restored prior snapshot"):
        materialize_readiness_snapshot(tmp_path, profile="default", confirm_materialize=True)

    assert _snapshot_values(first.output_dir) == {"old"}
    assert set(path.name for path in first.output_dir.iterdir()) == set(EXPECTED_FILENAMES)
    assert not (first.output_dir.parent / ".default.readiness-staging").exists()
    assert not (first.output_dir.parent / ".default.readiness-backup").exists()


def test_partial_backup_cleanup_failure_preserves_complete_new_snapshot_and_residue(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    _write_fixture(tmp_path)
    _install_builder(monkeypatch, _frames("old"))
    first = materialize_readiness_snapshot(tmp_path, profile="default", confirm_materialize=True)
    monkeypatch.setattr(readiness_materializer, "build_ticker_readiness_report", lambda *_args, **_kwargs: _frames("new"))
    original_remove = readiness_materializer.shutil.rmtree

    def partially_remove_backup(path, *args, **kwargs):
        candidate = Path(path)
        if candidate.name == ".default.readiness-backup":
            (candidate / EXPECTED_FILENAMES[0]).unlink()
            raise OSError("backup cleanup failed after partial removal")
        return original_remove(path, *args, **kwargs)

    monkeypatch.setattr(readiness_materializer.shutil, "rmtree", partially_remove_backup)

    with pytest.raises(ReadinessMaterializationError, match="operator recovery"):
        materialize_readiness_snapshot(tmp_path, profile="default", confirm_materialize=True)

    backup = first.output_dir.parent / ".default.readiness-backup"
    assert set(path.name for path in first.output_dir.iterdir()) == set(EXPECTED_FILENAMES)
    assert _snapshot_values(first.output_dir) == {"new"}
    assert backup.exists()
    assert set(path.name for path in backup.iterdir()) == set(EXPECTED_FILENAMES[1:])
    assert not (first.output_dir.parent / ".default.readiness-staging").exists()
    with pytest.raises(ReadinessMaterializationError, match="operator recovery"):
        materialize_readiness_snapshot(tmp_path, profile="default", confirm_materialize=True)


def test_destination_change_immediately_before_backup_rename_is_preserved_and_not_published(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    _write_fixture(tmp_path)
    _install_builder(monkeypatch, _frames("old"))
    first = materialize_readiness_snapshot(tmp_path, profile="default", confirm_materialize=True)
    monkeypatch.setattr(readiness_materializer, "build_ticker_readiness_report", lambda *_args, **_kwargs: _frames("new"))
    operator_file = first.output_dir / "operator-race.txt"

    def inject_operator_entry(name: str) -> None:
        if name == "before_backup_rename":
            operator_file.write_text("preserve me", encoding="utf-8")

    monkeypatch.setattr(readiness_materializer, "_publication_checkpoint", inject_operator_entry)

    with pytest.raises(ReadinessMaterializationError, match="operator recovery"):
        materialize_readiness_snapshot(tmp_path, profile="default", confirm_materialize=True)

    assert operator_file.read_text(encoding="utf-8") == "preserve me"
    assert _snapshot_values(first.output_dir) == {"old"}
    assert not (first.output_dir.parent / ".default.readiness-backup").exists()


@pytest.mark.parametrize("raced_path", ["destination", "backup"])
def test_operator_path_appearing_immediately_before_publish_is_preserved_without_publish_rename(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, raced_path: str
):
    _write_fixture(tmp_path)
    destination = tmp_path / "outputs/local/derived/default"
    derived = destination.parent
    staging = derived / ".default.readiness-staging"
    backup = derived / ".default.readiness-backup"
    operator_root = destination if raced_path == "destination" else backup
    operator_file = operator_root / "operator-race.txt"
    _install_builder(monkeypatch, _frames("new"))
    publish_renames = []
    original_replace = readiness_materializer.os.replace

    def inject_operator_path(name: str) -> None:
        if name == "before_publish":
            operator_root.mkdir()
            operator_file.write_text("preserve me", encoding="utf-8")

    def track_replace(source, target):
        if Path(source) == staging and Path(target) == destination:
            publish_renames.append((Path(source), Path(target)))
        return original_replace(source, target)

    monkeypatch.setattr(readiness_materializer, "_publication_checkpoint", inject_operator_path)
    monkeypatch.setattr(readiness_materializer.os, "replace", track_replace)

    with pytest.raises(ReadinessMaterializationError, match="operator recovery"):
        materialize_readiness_snapshot(tmp_path, profile="default", confirm_materialize=True)

    assert operator_file.read_text(encoding="utf-8") == "preserve me"
    assert publish_renames == []
    assert not staging.exists()


def test_staging_swap_immediately_before_publish_is_never_followed_or_deleted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    _write_fixture(tmp_path)
    destination = tmp_path / "outputs/local/derived/default"
    staging = destination.parent / ".default.readiness-staging"
    displaced = destination.parent / "operator-displaced-complete-staging"
    replacement_file = staging / "operator-race.txt"
    _install_builder(monkeypatch, _frames("new"))

    def swap_staging(name: str) -> None:
        if name == "before_publish":
            staging.rename(displaced)
            staging.mkdir()
            replacement_file.write_text("preserve replacement", encoding="utf-8")

    monkeypatch.setattr(readiness_materializer, "_publication_checkpoint", swap_staging)

    with pytest.raises(ReadinessMaterializationError, match="operator recovery"):
        materialize_readiness_snapshot(tmp_path, profile="default", confirm_materialize=True)

    assert replacement_file.read_text(encoding="utf-8") == "preserve replacement"
    assert set(path.name for path in displaced.iterdir()) == set(EXPECTED_FILENAMES)
    assert not destination.exists()


def test_staging_swap_after_atomic_mkdir_is_not_written_or_removed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    _write_fixture(tmp_path)
    destination = tmp_path / "outputs/local/derived/default"
    staging = destination.parent / ".default.readiness-staging"
    displaced = destination.parent / "operator-displaced-empty-staging"
    replacement_file = staging / "operator-race.txt"
    _install_builder(monkeypatch, _frames("new"))

    def swap_after_create(name: str) -> None:
        if name == "after_staging_create":
            staging.rename(displaced)
            staging.mkdir()
            replacement_file.write_text("preserve replacement", encoding="utf-8")

    monkeypatch.setattr(readiness_materializer, "_publication_checkpoint", swap_after_create)

    with pytest.raises(ReadinessMaterializationError, match="operator recovery"):
        materialize_readiness_snapshot(tmp_path, profile="default", confirm_materialize=True)

    assert replacement_file.read_text(encoding="utf-8") == "preserve replacement"
    assert list(displaced.iterdir()) == []
    assert not destination.exists()


def test_staging_replacement_appearing_at_serialization_cleanup_is_not_deleted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    _write_fixture(tmp_path)
    destination = tmp_path / "outputs/local/derived/default"
    staging = destination.parent / ".default.readiness-staging"
    displaced = destination.parent / "operator-displaced-partial-staging"
    replacement_file = staging / "operator-race.txt"
    _install_builder(monkeypatch, _frames("new"))

    def fail_serialization(*_args, **_kwargs):
        raise OSError("serialize failure")

    def swap_before_cleanup(name: str) -> None:
        if name == "before_staging_cleanup":
            staging.rename(displaced)
            staging.mkdir()
            replacement_file.write_text("preserve replacement", encoding="utf-8")

    monkeypatch.setattr(pd.DataFrame, "to_csv", fail_serialization)
    monkeypatch.setattr(readiness_materializer, "_publication_checkpoint", swap_before_cleanup)

    with pytest.raises(ReadinessMaterializationError, match="operator recovery"):
        materialize_readiness_snapshot(tmp_path, profile="default", confirm_materialize=True)

    assert replacement_file.read_text(encoding="utf-8") == "preserve replacement"
    assert displaced.exists()
    assert not destination.exists()


def test_backup_replacement_appearing_at_cleanup_is_not_deleted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    _write_fixture(tmp_path)
    _install_builder(monkeypatch, _frames("old"))
    first = materialize_readiness_snapshot(tmp_path, profile="default", confirm_materialize=True)
    monkeypatch.setattr(readiness_materializer, "build_ticker_readiness_report", lambda *_args, **_kwargs: _frames("new"))
    backup = first.output_dir.parent / ".default.readiness-backup"
    displaced = first.output_dir.parent / "operator-displaced-complete-backup"
    replacement_file = backup / "operator-race.txt"

    def swap_before_cleanup(name: str) -> None:
        if name == "before_backup_cleanup":
            backup.rename(displaced)
            backup.mkdir()
            replacement_file.write_text("preserve replacement", encoding="utf-8")

    monkeypatch.setattr(readiness_materializer, "_publication_checkpoint", swap_before_cleanup)

    with pytest.raises(ReadinessMaterializationError, match="operator recovery"):
        materialize_readiness_snapshot(tmp_path, profile="default", confirm_materialize=True)

    assert replacement_file.read_text(encoding="utf-8") == "preserve replacement"
    assert set(path.name for path in displaced.iterdir()) == set(EXPECTED_FILENAMES)
    assert _snapshot_values(first.output_dir) == {"new"}
    assert not (first.output_dir.parent / ".default.readiness-staging").exists()


@pytest.mark.parametrize(
    "checkpoint",
    [
        "before_backup_rename",
        "after_backup_rename",
        "before_publish",
        "after_publish",
        "during_cleanup",
    ],
)
def test_handled_publication_failure_restores_prior_complete_snapshot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, checkpoint: str
):
    _write_fixture(tmp_path)
    _install_builder(monkeypatch, _frames("old"))
    first = materialize_readiness_snapshot(tmp_path, profile="default", confirm_materialize=True)
    monkeypatch.setattr(readiness_materializer, "build_ticker_readiness_report", lambda *_args, **_kwargs: _frames("new"))

    def fail_at(name: str) -> None:
        if name == checkpoint:
            raise OSError(f"handled failure at {name}")

    monkeypatch.setattr(readiness_materializer, "_publication_checkpoint", fail_at)

    with pytest.raises(ReadinessMaterializationError, match="restored prior snapshot"):
        materialize_readiness_snapshot(tmp_path, profile="default", confirm_materialize=True)

    assert _snapshot_values(first.output_dir) == {"old"}
    assert set(path.name for path in first.output_dir.iterdir()) == set(EXPECTED_FILENAMES)
    assert not (first.output_dir.parent / ".default.readiness-staging").exists()
    assert not (first.output_dir.parent / ".default.readiness-backup").exists()


class SimulatedCrash(BaseException):
    pass


@pytest.mark.parametrize(
    ("checkpoint", "canonical_values", "canonical_present"),
    [
        ("before_backup_rename", {"old"}, True),
        ("after_backup_rename", set(), False),
        ("before_publish", set(), False),
        ("after_publish", {"new"}, True),
        ("during_cleanup", {"new"}, True),
    ],
)
def test_unhandled_interruption_leaves_explicit_residue_and_never_a_mixed_snapshot(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    checkpoint: str,
    canonical_values: set[str],
    canonical_present: bool,
):
    _write_fixture(tmp_path)
    _install_builder(monkeypatch, _frames("old"))
    first = materialize_readiness_snapshot(tmp_path, profile="default", confirm_materialize=True)
    monkeypatch.setattr(readiness_materializer, "build_ticker_readiness_report", lambda *_args, **_kwargs: _frames("new"))

    def crash_at(name: str) -> None:
        if name == checkpoint:
            raise SimulatedCrash(name)

    monkeypatch.setattr(readiness_materializer, "_publication_checkpoint", crash_at)

    with pytest.raises(SimulatedCrash):
        materialize_readiness_snapshot(tmp_path, profile="default", confirm_materialize=True)

    assert first.output_dir.exists() is canonical_present
    assert _snapshot_values(first.output_dir) == canonical_values
    assert canonical_values in ({"old"}, {"new"}, set())
    staging = first.output_dir.parent / ".default.readiness-staging"
    backup = first.output_dir.parent / ".default.readiness-backup"
    assert staging.exists() or backup.exists()

    monkeypatch.setattr(readiness_materializer, "_publication_checkpoint", lambda _name: None)
    with pytest.raises(ReadinessMaterializationError, match="operator recovery"):
        materialize_readiness_snapshot(tmp_path, profile="default", confirm_materialize=True)
