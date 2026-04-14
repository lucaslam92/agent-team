"""
Codex Bridge — wraps the `codex` CLI in non-interactive exec mode.

Strategy
--------
One QQ message = one `codex exec` invocation.

  codex exec --cwd <workdir> [--image <path> ...] -- <prompt>

stdout + stderr are captured together and returned as a single string.
The process is killed after `timeout` seconds to prevent hanging.

Image handling
--------------
If the user attached images (already downloaded to local paths), they are
passed via `--image <path>` flags.  Video support is evaluated separately
(phase 4) so for now we skip video attachments with a warning.

Output post-processing
----------------------
The raw output may contain ANSI escape sequences from codex's rich output.
We strip those before returning so QQ sees clean text.
"""
from __future__ import annotations

import asyncio
import logging
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

log = logging.getLogger(__name__)

# Strip ANSI escape codes
_ANSI_RE = re.compile(r"\x1b\[[0-9;]*[mGKHF]")


@dataclass
class ExecResult:
    stdout: str
    stderr: str
    returncode: int
    timed_out: bool = False

    @property
    def combined(self) -> str:
        """Merged output, stderr appended only if non-empty."""
        out = self.stdout
        if self.stderr.strip():
            out = out + "\n[stderr]\n" + self.stderr if out.strip() else self.stderr
        return out.strip()

    @property
    def success(self) -> bool:
        return self.returncode == 0 and not self.timed_out


def _strip_ansi(text: str) -> str:
    return _ANSI_RE.sub("", text)


def _find_codex(binary: str) -> str:
    """Resolve codex binary path; raise if not found."""
    path = shutil.which(binary)
    if path is None:
        raise FileNotFoundError(
            f"codex binary not found: '{binary}'. "
            "Install via: npm install -g @openai/codex"
        )
    return path


async def exec_codex(
    *,
    prompt: str,
    workdir: str,
    binary: str = "codex",
    image_paths: Optional[List[str]] = None,
    timeout: int = 120,
) -> ExecResult:
    """
    Run `codex exec` non-interactively and return the result.

    Parameters
    ----------
    prompt:
        The user's instruction text.
    workdir:
        Working directory for the codex process.
    binary:
        Path or name of the codex executable.
    image_paths:
        Local paths of downloaded images to pass as --image flags.
    timeout:
        Seconds before the process is force-killed.
    """
    codex_bin = _find_codex(binary)

    cmd: List[str] = [codex_bin, "exec", "--cwd", workdir]

    for img in (image_paths or []):
        p = Path(img)
        if p.exists():
            cmd += ["--image", str(p)]
        else:
            log.warning("Image path not found, skipping: %s", img)

    cmd += ["--", prompt]

    log.info("Running: %s", " ".join(cmd))

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(), timeout=timeout
            )
            timed_out = False
        except asyncio.TimeoutError:
            log.warning("codex exec timed out after %ds — killing process", timeout)
            proc.kill()
            stdout_bytes, stderr_bytes = await proc.communicate()
            timed_out = True

        returncode = proc.returncode or 0

        stdout = _strip_ansi(stdout_bytes.decode("utf-8", errors="replace"))
        stderr = _strip_ansi(stderr_bytes.decode("utf-8", errors="replace"))

        return ExecResult(
            stdout=stdout,
            stderr=stderr,
            returncode=returncode,
            timed_out=timed_out,
        )

    except FileNotFoundError as exc:
        log.error("codex not found: %s", exc)
        return ExecResult(
            stdout="",
            stderr=str(exc),
            returncode=127,
        )
    except Exception as exc:
        log.exception("Unexpected error running codex")
        return ExecResult(
            stdout="",
            stderr=f"Bridge error: {exc}",
            returncode=1,
        )


async def download_attachment(url: str, dest_dir: str) -> Optional[str]:
    """
    Download a QQ attachment URL to a local temp directory.
    Returns the local path on success, None on failure.
    """
    import aiohttp
    import os

    Path(dest_dir).mkdir(parents=True, exist_ok=True)

    filename = url.split("/")[-1].split("?")[0] or "attachment"
    local_path = os.path.join(dest_dir, filename)

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status != 200:
                    log.warning("Failed to download %s: HTTP %s", url, resp.status)
                    return None
                with open(local_path, "wb") as f:
                    async for chunk in resp.content.iter_chunked(8192):
                        f.write(chunk)
        log.info("Downloaded attachment to %s", local_path)
        return local_path
    except Exception as exc:
        log.error("Download failed for %s: %s", url, exc)
        return None
