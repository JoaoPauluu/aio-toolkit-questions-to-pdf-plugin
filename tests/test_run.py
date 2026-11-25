"""Runs run.py the way AIO Toolkit does: AIO_* env vars + params.json, SDK on PYTHONPATH."""
import base64
import json
import os
import shutil
import subprocess
import sys

from conftest import AIO_SDK, EXAMPLES, ROOT, TECTONIC, needs_sdk

pytestmark = needs_sdk


def run(tmp_path, params, files=()):
    inp, out, job = tmp_path / "in", tmp_path / "out", tmp_path / "job"
    for d in (inp, out, job):
        d.mkdir()
    paths = []
    for i, f in enumerate(files, 1):
        dst = inp / f"{i:03d}_{f.name}"
        shutil.copy(f, dst)
        paths.append(str(dst))
    if paths:
        params = {**params, "files": paths}
    (tmp_path / "params.json").write_text(json.dumps(params))
    env = {**os.environ, "AIO_PARAMS": str(tmp_path / "params.json"), "AIO_IN": str(inp), "AIO_OUT": str(out),
           "AIO_JOB_DIR": str(job), "AIO_DATA": str(tmp_path), "AIO_PLUGIN_DATA": str(tmp_path / "pd"),
           "TECTONIC": TECTONIC, "PYTHONPATH": os.pathsep.join([AIO_SDK, str(ROOT)])}
    proc = subprocess.run([sys.executable, "run.py"], cwd=ROOT, env=env, capture_output=True, text=True)
    return proc, sorted(p.name for p in out.iterdir())


def test_files_and_images(tmp_path):
    proc, outs = run(tmp_path, {"template": "blue_continuous", "output_name": "lista"},
                     [EXAMPLES / "exam_with_image.json", EXAMPLES / "graph.png"])
    assert proc.returncode == 0, proc.stdout
    assert outs == ["lista.pdf"]


def test_json_only_with_base64_images(tmp_path):
    exam = json.loads((EXAMPLES / "exam_with_image.json").read_text())
    b64 = base64.b64encode((EXAMPLES / "graph.png").read_bytes()).decode()
    proc, outs = run(tmp_path, {"exam": exam, "images": {"graph.png": "data:image/png;base64," + b64},
                                "template": "classic", "output_name": "exam", "keep_tex": True})
    assert proc.returncode == 0, proc.stdout
    assert outs == ["exam.pdf", "exam.tex"]


def test_several_exams_one_pdf_each(tmp_path):
    exam = json.loads((EXAMPLES / "exam.json").read_text())
    proc, outs = run(tmp_path, {"exam": [exam, {**exam, "student_name": "Bia"}], "output_name": "prova"})
    assert proc.returncode == 0, proc.stdout
    assert outs == ["prova_Ana_Souza.pdf", "prova_Bia.pdf"]


def test_errors_are_reported(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text('{"student_name": "X", "questions": []}')
    proc, outs = run(tmp_path, {"output_name": "e"}, [EXAMPLES / "exam_with_image.json", bad])
    assert proc.returncode == 1
    err = [line for line in proc.stdout.splitlines() if line.startswith("::error")]
    assert err and "bad.json" in err[0] and "graph.png" in err[0]
    assert outs == []


def test_no_exam(tmp_path):
    proc, _ = run(tmp_path, {})
    assert proc.returncode == 1 and "::error Add at least one .json" in proc.stdout
