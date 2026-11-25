import os
import shutil
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
EXAMPLES = ROOT / "examples"
TECTONIC = os.environ.get("TECTONIC") or shutil.which("tectonic")
AIO_SDK = os.environ.get("AIO_SDK")

needs_tectonic = pytest.mark.skipif(not TECTONIC, reason="set TECTONIC or put tectonic on PATH")
needs_sdk = pytest.mark.skipif(not (TECTONIC and AIO_SDK), reason="set TECTONIC and AIO_SDK (aio-toolkit/sdk/python)")
