"""Assignment PDF Maker: exam JSON (+ images) -> LaTeX template -> PDF.

params:
  files:       [path, ...]   .json exams and the images they reference (matched by original file name)
  exam:        object | [object, ...] | null   exams sent directly (API)
  images:      {name: base64 | data URL} | null images sent directly (API)
  template:    template name (templates/<name>.tex)
  output_name: base name of the PDF(s)
  keep_tex:    also write the generated .tex
  answer_key:  none | answers | full (answers + explanations)
  key_output:  append (after the exam, same PDF) | separate (<name>_answer_key.pdf)
  key_title:   heading of the answer key
"""
import base64
import binascii
import json
from pathlib import Path

import aio
import deps
import tectonic

deps.ensure()

from pydantic import ValidationError  # noqa: E402

from qtopdf.build import BuildError, build_pdf, output_names  # noqa: E402
from qtopdf.schema import Exam  # noqa: E402

p = aio.params()
template = p.get("template") or "classic"
output_name = (p.get("output_name") or "exam").strip() or "exam"
keep_tex = bool(p.get("keep_tex"))
answer_key = p.get("answer_key") or "none"
key_output = p.get("key_output") or "append"
key_title = p.get("key_title") or "Gabarito"

# ---- collect exams and images ----
sources: list[tuple[str, object]] = []   # (label, raw JSON value)
uploads: dict[str, bytes] = {}
for path in p.get("files") or []:
    name = Path(aio.original_name(path)).name
    data = Path(path).read_bytes()
    if name.lower().endswith(".json"):
        try:
            sources.append((name, json.loads(data)))
        except ValueError as e:
            sources.append((name, e))
    else:
        uploads[name] = data

direct = p.get("exam")
if isinstance(direct, list):
    sources += [(f"exam[{i}]", x) for i, x in enumerate(direct)]
elif direct is not None:
    sources.append(("exam", direct))

inline = p.get("images")
if inline is not None and not isinstance(inline, dict):
    aio.fail('"images" must be an object: {"file name": "<base64>"}')
for name, b64 in (inline or {}).items():
    if not isinstance(b64, str):
        aio.fail(f'images["{name}"] must be a base64 string')
    if b64.startswith("data:"):
        b64 = b64.partition(",")[2]
    try:
        uploads[Path(name).name] = base64.b64decode(b64, validate=True)
    except (binascii.Error, ValueError):
        aio.fail(f'images["{name}"] is not valid base64')

if not sources:
    aio.fail('Add at least one .json file (or send "exam" in the request).')

# ---- validate ----
errors: list[str] = []
parsed: list[tuple[str, Exam]] = []
for label, raw in sources:
    if isinstance(raw, Exception):
        errors.append(f"{label}: invalid JSON: {raw}")
        continue
    try:
        parsed.append((label, Exam.model_validate(raw)))
    except ValidationError as e:
        msg = "; ".join(f"{'.'.join(map(str, x['loc']))}: {x['msg']}" for x in e.errors())
        errors.append(f"{label}: invalid JSON structure: {msg}")

# ---- build ----
if not parsed:
    aio.fail(" | ".join(errors))
exe = tectonic.binary()
names = output_names(output_name, [ex.student_name for _, ex in parsed], multi=len(sources) > 1)
aio.title(f"{names[0]}.pdf" if len(names) == 1 else f"{output_name} ({len(names)} PDFs)")
built = 0
for n, ((label, exam), name) in enumerate(zip(parsed, names)):
    aio.status(f"Compiling {name}.pdf with '{template}' ({n + 1}/{len(parsed)})")
    aio.progress(100 * n / max(len(parsed), 1))
    try:
        for dest in build_pdf(exam, template, uploads, name, aio.OUT, exe, keep_tex,
                              answer_key, key_output, key_title):
            aio.log(f"{label} -> {dest.name} ({aio.human(dest.stat().st_size)})")
            built += 1
    except BuildError as e:
        aio.log(f"{label}: {e}")
        errors.append(f"{label}: {e}")

aio.progress(100)
if errors:
    aio.fail(f"{built} PDF(s) built, {len(errors)} failed. " + " | ".join(errors))
aio.status(f"Built {built} PDF(s) with template '{template}'")
