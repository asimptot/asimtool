"""Build + publish asimtool to PyPI using the credentials in ``.env``.

Usage
-----
    python scripts/publish.py            # build, check, upload
    python scripts/publish.py --dry-run  # build + check only
    python scripts/publish.py --test     # verify the token against the PyPI API

Credentials are read from the repo-root ``.env`` file, which is git-ignored and
never committed. See ``.env.example`` for the expected keys.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = ROOT / ".env"


def load_env(path: Path = ENV_FILE) -> dict[str, str]:
    """Parse a simple ``KEY=value`` .env file (no external dependencies)."""
    if not path.exists():
        sys.exit(f"[!] {path} not found. Copy .env.example to .env and fill it in.")

    values: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def run(cmd: list[str], **kwargs) -> int:
    print(f"$ {' '.join(cmd)}")
    return subprocess.call(cmd, cwd=str(ROOT), **kwargs)


def verify_token(username: str, token: str) -> bool:
    """Check the credentials against the PyPI JSON API."""
    import base64
    import json
    import urllib.request

    creds = base64.b64encode(f"{username}:{token}".encode()).decode()
    req = urllib.request.Request(
        "https://pypi.org/pypi/asimtool/json",
        headers={"Authorization": f"Basic {creds}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.load(resp)
        print(f"[+] PyPI kimlik dogrulama basarili. Su anki surum: {data['info']['version']}")
        return True
    except Exception as exc:  # noqa: BLE001 - report any auth/network failure
        print(f"[!] PyPI dogrulama basarisiz: {exc}")
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Publish asimtool to PyPI")
    parser.add_argument("--dry-run", action="store_true", help="build + check only, no upload")
    parser.add_argument("--test", action="store_true", help="only verify the stored token")
    parser.add_argument(
        "--password-only",
        action="store_true",
        help="authenticate with PYPI_ACCOUNT/PYPI_PASSWORD instead of the API token "
             "(PyPI rejects password uploads since 2024 — kept for reference)",
    )
    args = parser.parse_args()

    env = load_env()
    package = env.get("PYPI_PACKAGE", "asimtool")

    if args.password_only:
        username = env.get("PYPI_ACCOUNT", "")
        secret = env.get("PYPI_PASSWORD", "")
        if not username or not secret:
            sys.exit("[!] PYPI_ACCOUNT ve PYPI_PASSWORD .env icinde tanimli degil.")
        label = "password"
    else:
        username = env.get("PYPI_USERNAME", "__token__")
        secret = env.get("PYPI_TOKEN", "")
        label = "token"
        if not secret or secret.startswith("pypi-XXXX"):
            sys.exit("[!] PYPI_TOKEN .env icinde tanimli degil veya placeholder.")

    if args.test:
        return 0 if verify_token(username, secret) else 1

    version = ""
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    for line in pyproject.splitlines():
        if line.strip().startswith("version"):
            version = line.split("=", 1)[1].strip().strip('"')
            break
    print(f"[+] {package} {version} yayinlanacak")

    if run([sys.executable, "-m", "build"]) != 0:
        return 1

    dist = sorted((ROOT / "dist").glob(f"{package}-{version}-*"))
    if not dist:
        sys.exit(f"[!] dist/{package}-{version}-* bulunamadi.")
    print("[+] " + ", ".join(p.name for p in dist))

    if run([sys.executable, "-m", "twine", "check", *map(str, dist)]) != 0:
        return 1

    if args.dry_run:
        print("[+] dry-run bitti, yukleme yapilmadi.")
        return 0

    os.environ["TWINE_USERNAME"] = username
    os.environ["TWINE_PASSWORD"] = secret
    print(f"[+] {label} ile yukleniyor: {username}")
    return run([sys.executable, "-m", "twine", "upload", "--skip-existing", *map(str, dist)])


if __name__ == "__main__":
    raise SystemExit(main())
