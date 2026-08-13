from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import stat
import subprocess
import sys
from typing import Literal, Sequence


PROTECTED_ROOTS = ("data", "outputs", "docs/assets")


@dataclass(frozen=True, order=True)
class ArtifactState:
    relative_path: str
    kind: Literal["file", "directory", "symlink"]
    digest_or_target: str


class _UnsupportedArtifactType(RuntimeError):
    def __init__(self, relative_path: str):
        super().__init__(f"Unsupported protected artifact type: {relative_path}")
        self.relative_path = relative_path


def _file_digest(path: Path) -> str:
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags)
    try:
        digest = hashlib.sha256()
        while chunk := os.read(descriptor, 1024 * 1024):
            digest.update(chunk)
        return digest.hexdigest()
    finally:
        os.close(descriptor)


def _capture_path(path: Path, project_root: Path, states: list[ArtifactState]) -> None:
    mode = path.lstat().st_mode
    relative_path = path.relative_to(project_root).as_posix()
    if stat.S_ISLNK(mode):
        states.append(ArtifactState(relative_path, "symlink", os.readlink(path)))
        return
    if stat.S_ISDIR(mode):
        states.append(ArtifactState(relative_path, "directory", ""))
        with os.scandir(path) as entries:
            children = sorted((Path(entry.path) for entry in entries), key=lambda child: child.name)
        for child in children:
            _capture_path(child, project_root, states)
        return
    if stat.S_ISREG(mode):
        states.append(ArtifactState(relative_path, "file", _file_digest(path)))
        return
    raise _UnsupportedArtifactType(relative_path)


def capture_artifact_manifest(project_root: Path) -> tuple[ArtifactState, ...]:
    root = Path(project_root).resolve()
    states: list[ArtifactState] = []
    for relative_root in PROTECTED_ROOTS:
        protected_root = root / relative_root
        try:
            protected_root.lstat()
        except FileNotFoundError:
            continue
        _capture_path(protected_root, root, states)
    return tuple(sorted(states))


def _changed_paths(
    before: tuple[ArtifactState, ...],
    after: tuple[ArtifactState, ...],
) -> list[str]:
    before_by_path = {state.relative_path: state for state in before}
    after_by_path = {state.relative_path: state for state in after}
    return sorted(
        relative_path
        for relative_path in before_by_path.keys() | after_by_path.keys()
        if before_by_path.get(relative_path) != after_by_path.get(relative_path)
    )


def _report_protected_mutations(relative_paths: Sequence[str]) -> None:
    print("Protected artifact mutation detected:", file=sys.stderr)
    for relative_path in relative_paths:
        print(f"- {relative_path}", file=sys.stderr)


def run_guarded_command(project_root: Path, command: Sequence[str]) -> int:
    if isinstance(command, (str, bytes)) or not command:
        raise ValueError("command must be a non-empty argv sequence")
    argv = list(command)
    if not all(isinstance(argument, str) for argument in argv):
        raise TypeError("every command argument must be a string")

    root = Path(project_root).resolve()
    try:
        before = capture_artifact_manifest(root)
    except _UnsupportedArtifactType as error:
        _report_protected_mutations([error.relative_path])
        return 3
    child_error: OSError | None = None
    try:
        child_exit_code = subprocess.run(
            argv,
            cwd=root,
            check=False,
            shell=False,
        ).returncode
    except OSError as error:
        child_error = error
        child_exit_code = 127
    try:
        after = capture_artifact_manifest(root)
    except _UnsupportedArtifactType as error:
        _report_protected_mutations([error.relative_path])
        return 3

    changed_paths = _changed_paths(before, after)
    if changed_paths:
        _report_protected_mutations(changed_paths)
        return 3
    if child_error is not None:
        print(f"Unable to run guarded command: {child_error}", file=sys.stderr)
    return child_exit_code


def _argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run one exact argv command and reject persistent protected-artifact mutation."
    )
    parser.add_argument("--project-root", required=True, help="Repository root containing protected artifact paths.")
    return parser


def main(argv: list[str] | None = None) -> int:
    raw_arguments = list(sys.argv[1:] if argv is None else argv)
    parser = _argument_parser()
    if "--" not in raw_arguments:
        parser.error("expected '--' before COMMAND")
    separator = raw_arguments.index("--")
    options = parser.parse_args(raw_arguments[:separator])
    command = raw_arguments[separator + 1 :]
    if not command:
        parser.error("COMMAND is required after '--'")
    return run_guarded_command(Path(options.project_root), command)


if __name__ == "__main__":
    raise SystemExit(main())
