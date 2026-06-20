#!/usr/bin/env python3
"""Install an APL wheel into sandbox temp storage and run adapter regression."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--wheel", required=True, type=Path)
    parser.add_argument(
        "--sandbox-root",
        type=Path,
        help="Sandbox root when this runner has not yet been copied there.",
    )
    parser.add_argument("--keep-temp", action="store_true")
    args = parser.parse_args()

    sandbox_root = (
        args.sandbox_root.expanduser().resolve()
        if args.sandbox_root
        else Path(__file__).resolve().parent
    )
    if not (sandbox_root / "adapters" / "subject_runtime.py").is_file():
        parser.error(
            "sandbox root is invalid; copy this runner to runtime_loop_mvp_sandbox/ "
            "or pass --sandbox-root"
        )
    workspace_root = sandbox_root.parent
    temp_root = sandbox_root / "tmp" / "adaptive_profile_adapter"
    site_dir = temp_root / "site"

    wheel = args.wheel.expanduser().resolve()
    if not wheel.is_file() or wheel.suffix != ".whl":
        parser.error(f"wheel not found: {wheel}")

    shutil.rmtree(temp_root, ignore_errors=True)
    site_dir.mkdir(parents=True)
    try:
        install = [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--no-deps",
            "--target",
            str(site_dir),
            str(wheel),
        ]
        subprocess.run(install, cwd=workspace_root, check=True)
        env = os.environ.copy()
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["PYTHONPATH"] = os.pathsep.join(
            [str(site_dir), str(sandbox_root), env.get("PYTHONPATH", "")]
        ).rstrip(os.pathsep)
        tests = [
            sys.executable,
            "-m",
            "pytest",
            str(sandbox_root / "tests" / "test_adaptive_profile_adapter.py"),
            str(sandbox_root / "tests" / "test_subject_mvp_integration.py"),
            str(sandbox_root / "tests" / "test_context_pressure.py"),
            "-q",
        ]
        return subprocess.run(
            tests,
            cwd=workspace_root,
            env=env,
            check=False,
        ).returncode
    finally:
        if not args.keep_temp:
            shutil.rmtree(temp_root, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
