"""Template loading/validation and compilation with Tectonic."""
from __future__ import annotations

import os
import re
import subprocess
import tempfile
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING

from .render import RenderError, escape_plain, referenced_images, render_body, render_key_body

if TYPE_CHECKING:
    from .schema import Exam

ROOT = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = ROOT / "templates"

PLACEHOLDERS = {"student_name", "title", "date", "body"}
REQUIRED_PLACEHOLDERS = ("student_name", "body")
# Macros/environments the template must define, and packages question fragments may rely on.
REQUIRED_NAMES = ("examquestion", "examalternatives", "examparts", "examimage", "exampoints",
                  "examtable", "examth", "examhline")
REQUIRED_PACKAGES = ("amsmath", "amssymb", "graphicx", "enumitem", "array")
IMAGE_TYPES = {".png", ".jpg", ".jpeg", ".pdf"}
TIMEOUT = 300  # seconds; the first build of a template may download TeX packages


class BuildError(Exception):
    pass


def slug(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", text).strip("._") or "output"


def output_names(base: str, students: list[str], multi: bool | None = None) -> list[str]:
    """One file name per student: `base` alone for a single sheet, else base_<student> (collisions get _2)."""
    base, used, out = slug(base), set(), []
    multi = len(students) > 1 if multi is None else multi
    for s in students:
        name = f"{base}_{slug(s)}" if multi else base
        while name in used:
            name += "_2"
        used.add(name)
        out.append(name)
    return out


def list_templates() -> list[str]:
    return sorted(p.stem for p in TEMPLATES_DIR.glob("*.tex"))


def load_template(name: str) -> str:
    path = TEMPLATES_DIR / f"{Path(name).name}.tex"
    if not path.is_file():
        raise BuildError(f"Template '{name}' not found in templates/.")
    tex = path.read_text(encoding="utf-8")
    found = set(re.findall(r"<<(\w+)>>", tex))
    if found - PLACEHOLDERS:
        raise BuildError(f"Template '{name}' uses unknown placeholder(s): {sorted(found - PLACEHOLDERS)}")
    missing = [f"<<{p}>>" for p in REQUIRED_PLACEHOLDERS if p not in found]
    missing += [n for n in REQUIRED_NAMES if n not in tex]
    missing += [f"package {p}" for p in REQUIRED_PACKAGES if p not in tex]
    if missing:
        raise BuildError(f"Template '{name}' is missing {', '.join(missing)} (see docs/TEMPLATES.md).")
    return tex


def _locate(source: str, log: str) -> str:
    """Map a LaTeX error line back to the question that produced it."""
    m = re.search(r"^l\.(\d+)", log, re.M)
    marker = None
    for i, line in enumerate(source.splitlines(), 1):
        if m and i > int(m[1]):
            break
        if line.startswith("%%QUESTION "):
            marker = line.split()[1]
    return f"\n(near question {marker} of the exam)" if m and marker else ""


KEY_MODES = ("none", "answers", "full")
KEY_OUTPUTS = ("append", "separate")


def render_source(exam: Exam, template: str, body: str) -> str:
    tex = load_template(template)
    values = {
        "student_name": escape_plain(exam.student_name),
        "title": escape_plain(exam.title),
        "date": escape_plain(exam.date or date.today().strftime("%d/%m/%Y")),
        "body": body,
    }
    return re.sub(r"<<(\w+)>>", lambda m: values[m[1]], tex)


def _compile(source: str, aliases: dict[str, str], uploads: dict[str, bytes], dest: Path,
             tectonic: str | Path) -> Path:
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp = Path(tmp_dir)
        (tmp / "main.tex").write_text(source, encoding="utf-8")
        for name, alias in aliases.items():
            (tmp / alias).write_bytes(uploads[name])
        # --untrusted: no shell escape or other insecure features. Tectonic reruns TeX until refs settle.
        cmd = [str(tectonic), "-X", "compile", "--untrusted", "--keep-logs", "--outdir", str(tmp), "main.tex"]
        try:
            proc = subprocess.run(cmd, cwd=tmp, capture_output=True, text=True, errors="replace",
                                  timeout=TIMEOUT, env={**os.environ, "TECTONIC_UNTRUSTED_MODE": "1"})
        except subprocess.TimeoutExpired:
            raise BuildError(f"LaTeX took too long ({TIMEOUT} s) and was stopped.") from None
        pdf = tmp / "main.pdf"
        if proc.returncode != 0 or not pdf.exists():
            log_file = tmp / "main.log"
            log = log_file.read_text(errors="replace") if log_file.exists() else ""
            errs = re.findall(r"^!.*(?:\n.*){0,2}", log, re.M)[:3]
            detail = "\n".join(errs) or "\n".join((proc.stderr or proc.stdout).strip().splitlines()[-8:])
            raise BuildError("LaTeX error:\n" + detail + _locate(source, log))
        dest.write_bytes(pdf.read_bytes())
    return dest


def build_pdf(exam: Exam, template: str, uploads: dict[str, bytes], out_name: str, out_dir: Path,
              tectonic: str | Path, keep_tex: bool = False, answer_key: str = "none",
              key_output: str = "append", key_title: str = "Gabarito") -> list[Path]:
    """uploads maps each Image.file to its bytes. Writes <out_name>.pdf, plus <out_name>_answer_key.pdf when
    answer_key is "answers"/"full" and key_output is "separate" (with "append" the key follows the exam).
    Returns the PDFs written."""
    if answer_key not in KEY_MODES:
        raise BuildError(f"answer_key must be one of {', '.join(KEY_MODES)}")
    if key_output not in KEY_OUTPUTS:
        raise BuildError(f"key_output must be one of {', '.join(KEY_OUTPUTS)}")
    needed = referenced_images(exam)
    if missing := sorted(needed - uploads.keys()):
        raise BuildError("Image(s) referenced in the JSON but not available: " + ", ".join(missing))
    if bad := sorted(n for n in needed if Path(n).suffix.lower() not in IMAGE_TYPES):
        raise BuildError(f"Unsupported image type: {', '.join(bad)} (use png, jpg or pdf).")

    # Names may contain spaces/underscores that break LaTeX: use safe aliases.
    aliases = {n: f"img{i}{Path(n).suffix.lower()}" for i, n in enumerate(sorted(needed), 1)}
    try:
        bodies = {out_name: render_body(exam, aliases)}
        if answer_key != "none":
            key = render_key_body(exam, aliases, answer_key == "full", key_title.strip() or "Gabarito")
            if key_output == "append":
                bodies[out_name] += "\n\n\\clearpage\n" + key
            else:
                bodies[f"{out_name}_answer_key"] = key
    except RenderError as e:
        raise BuildError(str(e)) from e

    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for name, body in bodies.items():
        source = render_source(exam, template, body)
        if keep_tex:
            (out_dir / f"{name}.tex").write_text(source, encoding="utf-8")
        written.append(_compile(source, aliases, uploads, out_dir / f"{name}.pdf", tectonic))
    return written
