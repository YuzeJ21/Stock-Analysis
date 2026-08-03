from __future__ import annotations

import importlib
import os
from pathlib import Path
import subprocess
import sys

import pytest


def _guard_module():
    return importlib.import_module("src.no_write_artifact_guard")


def _protected_root(tmp_path: Path) -> Path:
    for relative in ("data", "outputs", "docs/assets"):
        (tmp_path / relative).mkdir(parents=True, exist_ok=True)
    return tmp_path


def _python(code: str, *args: Path | str) -> list[str]:
    return [sys.executable, "-c", code, *(str(arg) for arg in args)]


def test_stable_command_success_preserves_child_exit_code(tmp_path: Path):
    root = _protected_root(tmp_path)

    result = _guard_module().run_guarded_command(root, _python("raise SystemExit(0)"))

    assert result == 0


def test_stable_command_failure_preserves_child_exit_code(tmp_path: Path):
    root = _protected_root(tmp_path)

    result = _guard_module().run_guarded_command(root, _python("raise SystemExit(7)"))

    assert result == 7


@pytest.mark.parametrize(
    ("initial_kind", "mutation"),
    [
        (
            "file",
            "from pathlib import Path; Path(__import__('sys').argv[1]).write_bytes(b'after')",
        ),
        (
            "missing",
            "from pathlib import Path; Path(__import__('sys').argv[1]).write_bytes(b'new')",
        ),
        (
            "file",
            "from pathlib import Path; Path(__import__('sys').argv[1]).unlink()",
        ),
        (
            "file",
            "from pathlib import Path; p=Path(__import__('sys').argv[1]); p.unlink(); p.mkdir()",
        ),
    ],
    ids=("changed-bytes", "new-file", "deleted-file", "file-to-directory"),
)
def test_file_mutations_fail_with_exact_relative_path(
    tmp_path: Path,
    capsys,
    initial_kind: str,
    mutation: str,
):
    root = _protected_root(tmp_path)
    target = root / "data" / "watched.csv"
    if initial_kind == "file":
        target.write_bytes(b"before")

    result = _guard_module().run_guarded_command(root, _python(mutation, target))

    assert result == 3
    assert capsys.readouterr().err.splitlines()[-1] == "- data/watched.csv"


@pytest.mark.parametrize(
    ("initial_kind", "mutation"),
    [
        (
            "missing",
            "import os,sys; os.symlink(sys.argv[2], sys.argv[1])",
        ),
        (
            "symlink",
            "import os,sys; os.unlink(sys.argv[1]); os.symlink(sys.argv[2], sys.argv[1])",
        ),
        (
            "symlink",
            "from pathlib import Path; p=Path(__import__('sys').argv[1]); p.unlink(); p.write_bytes(b'file')",
        ),
        (
            "symlink",
            "from pathlib import Path; p=Path(__import__('sys').argv[1]); p.unlink(); p.mkdir()",
        ),
    ],
    ids=("new-symlink", "changed-target", "symlink-to-file", "symlink-to-directory"),
)
def test_symlink_mutations_fail_without_traversing_external_target(
    tmp_path: Path,
    capsys,
    initial_kind: str,
    mutation: str,
):
    root = _protected_root(tmp_path / "project")
    external_a = tmp_path / "external-a"
    external_b = tmp_path / "external-b"
    external_a.mkdir()
    external_b.mkdir()
    (external_a / "untouched.txt").write_text("outside-a", encoding="utf-8")
    (external_b / "untouched.txt").write_text("outside-b", encoding="utf-8")
    target = root / "outputs" / "external-link"
    if initial_kind == "symlink":
        target.symlink_to(external_a, target_is_directory=True)

    result = _guard_module().run_guarded_command(
        root,
        _python(mutation, target, external_b),
    )

    assert result == 3
    assert capsys.readouterr().err.splitlines()[-1] == "- outputs/external-link"
    assert (external_a / "untouched.txt").read_text(encoding="utf-8") == "outside-a"
    assert (external_b / "untouched.txt").read_text(encoding="utf-8") == "outside-b"


def test_external_changes_behind_directory_symlink_are_not_followed(tmp_path: Path):
    root = _protected_root(tmp_path / "project")
    external = tmp_path / "external"
    external.mkdir()
    external_file = external / "outside.txt"
    external_file.write_text("before", encoding="utf-8")
    (root / "data" / "external-link").symlink_to(external, target_is_directory=True)

    result = _guard_module().run_guarded_command(
        root,
        _python(
            "from pathlib import Path; Path(__import__('sys').argv[1]).write_text('after')",
            external_file,
        ),
    )

    assert result == 0
    assert external_file.read_text(encoding="utf-8") == "after"


@pytest.mark.parametrize(
    "relative_path",
    (
        "outputs/local/derived/default/new.csv",
        "outputs/staging/new.json",
        "data/local/new.csv",
        "docs/assets/new.png",
    ),
)
def test_all_protected_subtrees_reject_new_files(tmp_path: Path, capsys, relative_path: str):
    root = _protected_root(tmp_path)
    target = root / relative_path

    result = _guard_module().run_guarded_command(
        root,
        _python(
            "from pathlib import Path; p=Path(__import__('sys').argv[1]); p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(b'new')",
            target,
        ),
    )

    assert result == 3
    assert capsys.readouterr().err.splitlines()[-1] == f"- {relative_path}"


def test_manifest_is_an_in_memory_tuple_and_creates_no_manifest_file(tmp_path: Path):
    root = _protected_root(tmp_path)
    before = {path.relative_to(root).as_posix() for path in root.rglob("*")}

    manifest = _guard_module().capture_artifact_manifest(root)

    assert isinstance(manifest, tuple)
    assert {state.relative_path for state in manifest} == {"data", "docs/assets", "outputs"}
    assert {path.relative_to(root).as_posix() for path in root.rglob("*")} == before


def test_transient_write_restored_before_exit_is_outside_manifest_detection(tmp_path: Path):
    """Writer-spy suites, not this end-state manifest, cover transient writer invocation."""
    root = _protected_root(tmp_path)
    target = root / "data" / "restored.csv"
    target.write_bytes(b"original")

    result = _guard_module().run_guarded_command(
        root,
        _python(
            "from pathlib import Path; p=Path(__import__('sys').argv[1]); original=p.read_bytes(); p.write_bytes(b'transient'); p.write_bytes(original)",
            target,
        ),
    )

    assert result == 0
    assert target.read_bytes() == b"original"


def test_module_cli_returns_three_for_persistent_mutation(tmp_path: Path):
    root = _protected_root(tmp_path)
    target = root / "data" / "created.csv"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "src.no_write_artifact_guard",
            "--project-root",
            str(root),
            "--",
            *_python(
                "from pathlib import Path; Path(__import__('sys').argv[1]).write_bytes(b'new')",
                target,
            ),
        ],
        cwd=Path.cwd(),
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 3
    assert result.stderr.splitlines()[-1] == "- data/created.csv"


def test_module_cli_preserves_stable_child_failure(tmp_path: Path):
    root = _protected_root(tmp_path)

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "src.no_write_artifact_guard",
            "--project-root",
            str(root),
            "--",
            *_python("raise SystemExit(9)"),
        ],
        cwd=Path.cwd(),
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 9


@pytest.mark.parametrize(
    "arguments",
    (
        ("--project-root", "."),
        ("--", sys.executable, "-c", "raise SystemExit(0)"),
        ("--project-root", ".", sys.executable, "-c", "raise SystemExit(0)"),
    ),
)
def test_module_cli_rejects_commands_without_exact_boundary(arguments: tuple[str, ...]):
    result = subprocess.run(
        [sys.executable, "-m", "src.no_write_artifact_guard", *arguments],
        cwd=Path.cwd(),
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 2
