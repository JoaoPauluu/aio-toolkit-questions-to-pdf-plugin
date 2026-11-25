"""Shared by setup.py and run.py: where to get Tectonic (static musl builds, the container is Alpine)."""
import os

import aio

VERSION = "0.17.0"
BASE = f"https://github.com/tectonic-typesetting/tectonic/releases/download/tectonic%40{VERSION}/tectonic-{VERSION}"
URLS = {
    "amd64": f"{BASE}-x86_64-unknown-linux-musl.tar.gz",
    "arm64": f"{BASE}-aarch64-unknown-linux-musl.tar.gz",
}


def binary():
    """$TECTONIC overrides the download (useful for local development)."""
    return os.environ.get("TECTONIC") or aio.ensure_binary("tectonic", URLS, version=VERSION)
