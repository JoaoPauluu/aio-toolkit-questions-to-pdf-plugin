"""Runs after install/update: fetch Tectonic + pydantic, then build the example once per template so the TeX
packages every template needs are downloaded now (cached in /data/cache) instead of on the first real job."""
import json
import tempfile
from pathlib import Path

import aio
import deps
import tectonic

deps.ensure()

from qtopdf.build import build_pdf, list_templates  # noqa: E402
from qtopdf.schema import Exam  # noqa: E402

exe = tectonic.binary()
aio.run([exe, "--version"])

exam = Exam.model_validate(json.loads(Path("examples/exam_sections.json").read_text(encoding="utf-8")))
graph = {"graph.png": Path("examples/graph.png").read_bytes()}
templates = list_templates()
with tempfile.TemporaryDirectory() as tmp:
    for n, name in enumerate(templates):
        aio.status(f"Preparing template '{name}' (downloads TeX packages the first time)…")
        aio.progress(100 * n / len(templates))
        build_pdf(exam, name, graph, name, Path(tmp), exe, answer_key="full")
aio.progress(100)
aio.status(f"Ready: {len(templates)} templates compiled with Tectonic at {exe}.")
