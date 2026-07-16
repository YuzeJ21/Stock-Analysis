from pathlib import Path

from src.paths import (
    DATA_PROFILE_ENV,
    PROJECT_ROOT,
    path_context,
    profile_display_label,
    resolve_data_dir,
    resolve_data_profile,
    resolve_outputs_dir,
    resolve_project_root,
)


def test_default_paths_resolve_to_repo_root_not_cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    assert resolve_project_root() == PROJECT_ROOT
    assert resolve_data_dir() == PROJECT_ROOT / "data"
    assert resolve_outputs_dir() == PROJECT_ROOT / "outputs"


def test_explicit_project_root_supports_temp_fixtures(tmp_path):
    assert resolve_project_root(tmp_path) == tmp_path.resolve()
    assert resolve_data_dir("alt_data", tmp_path) == tmp_path.resolve() / "alt_data"
    assert resolve_outputs_dir("alt_outputs", tmp_path) == tmp_path.resolve() / "alt_outputs"


def test_path_context_is_json_friendly(tmp_path):
    context = path_context(tmp_path, "data", "outputs")

    assert context == {
        "project_root": str(tmp_path.resolve()),
        "data_dir": str(tmp_path.resolve() / "data"),
        "outputs_dir": str(tmp_path.resolve() / "outputs"),
    }


def test_data_profiles_keep_default_paths_and_offer_demo_and_local_roots(tmp_path, monkeypatch):
    monkeypatch.delenv(DATA_PROFILE_ENV, raising=False)

    default = resolve_data_profile(project_root=tmp_path)
    demo = resolve_data_profile("demo", tmp_path)
    local = resolve_data_profile("local", tmp_path)

    assert default.name == "default"
    assert default.data_dir == tmp_path / "data"
    assert default.outputs_dir == tmp_path / "outputs"
    assert demo.data_dir == tmp_path / "data" / "demo"
    assert demo.outputs_dir == tmp_path / "outputs" / "demo"
    assert local.data_dir == tmp_path / "data" / "local"
    assert local.outputs_dir == tmp_path / "outputs" / "local"


def test_environment_selected_profile_is_used_only_when_paths_are_not_explicit(tmp_path, monkeypatch):
    monkeypatch.setenv(DATA_PROFILE_ENV, "demo")

    assert resolve_data_dir(project_root=tmp_path) == tmp_path / "data" / "demo"
    assert resolve_outputs_dir(project_root=tmp_path) == tmp_path / "outputs" / "demo"
    assert resolve_data_dir("custom", tmp_path) == tmp_path / "custom"
    assert resolve_outputs_dir("custom_outputs", tmp_path) == tmp_path / "custom_outputs"


def test_profile_display_labels_are_stable_and_user_facing():
    assert profile_display_label("default") == "Default"
    assert profile_display_label("demo") == "Demo"
    assert profile_display_label("local") == "Local Research"


def test_profile_display_label_rejects_unknown_profile():
    try:
        profile_display_label("private")
    except ValueError as exc:
        assert "Unknown data profile 'private'" in str(exc)
    else:
        raise AssertionError("Expected unknown profile to fail closed")
