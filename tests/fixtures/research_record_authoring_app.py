import os
from pathlib import Path

import streamlit as st

from src.research_record_authoring import AuthoringPaths
from src.research_record_authoring_ui import render_research_record_authoring


root = Path(os.environ["RESEARCH_AUTHORING_FIXTURE_DIR"]).resolve()
if not root.is_dir() or "pytest-" not in str(root):
    raise RuntimeError("The authoring fixture requires a pytest temporary directory.")

paths = AuthoringPaths(root / "journal.csv", root / "catalysts.csv", root / "outcomes.csv")
if any(path.parent.resolve() != root for path in paths.all()):
    raise RuntimeError("The authoring fixture refuses paths outside its temporary directory.")

render_research_record_authoring(
    st_api=st,
    profile_key="demo",
    ticker="SYN1",
    paths=paths,
)
