"""
Device Runner — Install APK, launch app, collect logcat.
"""

from __future__ import annotations
import subprocess
import time
from pathlib import Path

from aadh.core.models import DeviceResult


def run_on_device(
    apk_path: str,
    main_activity: str,
    wait_cmd: str,
    install_cmd_tpl: str,
    launch_cmd_tpl: str,
    logcat_cmd: str,
    clear_logcat_cmd: str,
    run_dir: Path,
) -> tuple[DeviceResult, str]:
    """
    Install and launch the APK.
    Returns (DeviceResult, logcat_text).
    """
    log_lines: list[str] = []

    def run(cmd: str) -> subprocess.CompletedProcess:
        result = subprocess.run(
            cmd, shell=True, capture_output=True,
            text=True, encoding="utf-8", errors="replace",
        )
        log_lines.append(f"$ {cmd}")
        log_lines.append(result.stdout)
        if result.stderr:
            log_lines.append(result.stderr)
        return result

    # Wait for device
    run(wait_cmd)

    # Clear old logcat
    run(clear_logcat_cmd)

    # Install APK
    install_cmd = install_cmd_tpl.format(apk_path=apk_path, main_activity=main_activity)
    install_result = run(install_cmd)
    if install_result.returncode != 0:
        return DeviceResult(success=False, log="\n".join(log_lines)), ""

    # Launch app
    launch_cmd = launch_cmd_tpl.format(apk_path=apk_path, main_activity=main_activity)
    run(launch_cmd)

    # Give app time to start
    time.sleep(2)

    # Collect logcat
    logcat_result = run(logcat_cmd)
    logcat_text = logcat_result.stdout

    return DeviceResult(success=True, log="\n".join(log_lines)), logcat_text
