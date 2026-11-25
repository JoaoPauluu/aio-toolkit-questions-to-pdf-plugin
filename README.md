# Assignment PDF Maker (AIO Toolkit community plugin)

Turns exam/assignment JSON (+ images) into a PDF through LaTeX templates. It is the deterministic part of
*Questions to PDF* packaged as an [AIO Toolkit](https://github.com/JoaoPauluu/aio-toolkit) plugin: same JSON
format, same templates, no AI and no question bank.

- **Engine:** [Tectonic](https://tectonic-typesetting.github.io/) 0.17 (static musl build), downloaded by
  `setup.py` at install time. The Docker image is not changed.
- **TeX packages** are fetched on first use and cached in `/data/cache`. Setup compiles the example once with every
  template, so the download happens at install time (the first install takes a few minutes).

## Install

In AIO Toolkit, open **Community plugins** and paste:

```
https://github.com/JoaoPauluu/aio-toolkit-questions-to-pdf-plugin
```

## Use

**Web UI:** drop one or more `.json` files together with the images they reference, pick a template and click
**Build PDF**. Each JSON gives one PDF (`<output>.pdf`, or `<output>_<student>.pdf` when there are several).

**HTTP API:** `POST /api/plugins/assignment-pdf/run?wait=5m&output=file` returns the PDF itself (a zip with
several PDFs, `422` + job JSON with the error if it fails).

```sh
# Files: JSON + images (multipart)
curl -F files=@examples/exam_with_image.json -F files=@examples/graph.png -F template=blue_continuous \
     'http://aio-toolkit:8080/api/plugins/assignment-pdf/run?wait=5m&output=file' -o exam.pdf

# Pure JSON request: the exam inline, images as base64
curl -H 'Content-Type: application/json' \
     -d "{\"template\": \"classic\", \"exam\": $(cat examples/exam_with_image.json),
          \"images\": {\"graph.png\": \"$(base64 -w0 examples/graph.png)\"}}" \
     'http://aio-toolkit:8080/api/plugins/assignment-pdf/run?wait=5m&output=file' -o exam.pdf
```

| Input | Type | Meaning |
|---|---|---|
| `files` | files | `.json` exams and the images (png, jpg, pdf) their `file` fields name |
| `exam` | JSON | one exam object or a list of them |
| `images` | JSON | `{"graph.png": "<base64 or data: URL>"}` |
| `template` | select | `classic` (default), `compact`, `blue_continuous`, `blue_page_break` |
| `output_name` | text | base name of the PDF(s), default `exam` |
| `keep_tex` | checkbox | also return the generated `.tex` |

From another plugin: `aio.call("assignment-pdf", {"exam": {...}, "images": {...}})` or
`aio.find("assignment.pdf")`.

## Exam JSON

```json
{
  "student_name": "Ana Souza",
  "title": "Algebra - Midterm",
  "date": "25/11/2026",
  "questions": [
    { "statement_tex": "Pick one: \\(2+2=\\)", "alternatives": ["3", {"content_tex": "4", "is_correct": true}] },
    { "statement_tex": "Solve:", "points": 4, "items": ["\\(2x=4\\)", "\\(x^2=9\\)"] },
    { "statement_tex": "See {{image:fig}}.",
      "images": [ { "key": "fig", "file": "graph.png", "width": 0.5, "caption": "Figure 1" } ] }
  ]
}
```

Text fields ending in `_tex` are LaTeX fragments. The full guide is in [docs/QUESTION_FORMAT.md](docs/QUESTION_FORMAT.md).

## Templates

The templates are `templates/*.tex`; the contract is in [docs/TEMPLATES.md](docs/TEMPLATES.md). To add one, put
the `.tex` file in `templates/` and add its name to the `template` options in `plugin.yaml`.

## Development

```sh
uv sync
TECTONIC=/path/to/tectonic AIO_SDK=/path/to/aio-toolkit/sdk/python uv run pytest
```

Without `TECTONIC` the compile tests are skipped. Without `AIO_SDK` the `run.py` tests are skipped. To try it in
a running toolkit, copy this folder into the toolkit's `./plugins/assignment-pdf/`. `setup.py` only runs on a
community install, so `run.py` also fetches Tectonic and pydantic on its first run.
