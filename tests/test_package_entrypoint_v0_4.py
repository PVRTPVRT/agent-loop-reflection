import importlib
import tomllib
from pathlib import Path

from agentloop import main_v2


def test_python_module_entrypoint_uses_v2_dispatcher() -> None:
    package_main = importlib.import_module("agentloop.__main__")

    assert package_main.main is main_v2.main


def test_installed_console_script_uses_v2_dispatcher() -> None:
    project = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))

    assert project["project"]["scripts"]["agentloop"] == "agentloop.main_v2:main"
