import subprocess
import sys
from pathlib import Path

PACKAGE = Path(__file__).resolve().parent.parent


def test_the_app_imports_without_any_configuration(tmp_path):
    proc = subprocess.run(
        [
            sys.executable,
            "-c",
            "import app.models, app.routes.voice, app.routes.dashboard, app.main",
        ],
        cwd=tmp_path,
        env={"PYTHONPATH": str(PACKAGE)},
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
