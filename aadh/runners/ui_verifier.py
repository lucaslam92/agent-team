"""
UI Verifier — Writes Maestro flow to disk and executes it.
"""

from __future__ import annotations
import subprocess
import shutil
from pathlib import Path

from aadh.core.models import VerificationResult


def verify(
    maestro_flow_yaml: str,
    maestro_cmd_tpl: str,
    run_dir: Path,
) -> VerificationResult:
    if not maestro_flow_yaml.strip():
        return VerificationResult(
            success=False,
            log="No Maestro flow provided by planner.",
        )

    # Write flow to run directory
    flow_dir = run_dir / "maestro"
    flow_dir.mkdir(exist_ok=True)
    flow_path = flow_dir / "flow.yaml"
    flow_path.write_text(maestro_flow_yaml, encoding="utf-8")

    screenshots_dir = run_dir / "screenshots"
    screenshots_dir.mkdir(exist_ok=True)

    cmd = maestro_cmd_tpl.format(flow_path=str(flow_path))
    result = subprocess.run(
        cmd,
        shell=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env={**_os_env(), "MAESTRO_DRIVER_STARTUP_TIMEOUT": "30000"},
    )

    log = result.stdout + result.stderr

    # Collect screenshots Maestro may have written
    screenshots: list[Path] = []
    for pattern in ("*.png", "*.jpg"):
        screenshots.extend(screenshots_dir.glob(pattern))

    # Also check if Maestro put them in current dir
    import os
    for f in Path(".").glob("maestro_screenshots/*.png"):
        dest = screenshots_dir / f.name
        shutil.copy2(f, dest)
        screenshots.append(dest)

    success = result.returncode == 0 and "PASSED" in log.upper()

    return VerificationResult(
        success=success,
        log=log,
        screenshots=screenshots,
    )


def _os_env() -> dict:
    import os
    return dict(os.environ)
