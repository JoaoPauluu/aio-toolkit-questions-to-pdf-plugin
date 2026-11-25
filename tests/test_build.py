import json

import pytest

from conftest import EXAMPLES, TECTONIC, needs_tectonic
from qtopdf.build import BuildError, build_pdf, list_templates
from qtopdf.schema import Exam

pytestmark = needs_tectonic


def load(name):
    return Exam.model_validate(json.loads((EXAMPLES / name).read_text(encoding="utf-8")))


@pytest.mark.parametrize("template", list_templates())
def test_compiles_every_template(template, tmp_path):
    uploads = {"graph.png": (EXAMPLES / "graph.png").read_bytes()}
    for name in ("exam.json", "exam_with_image.json"):
        pdf = build_pdf(load(name), template, uploads, name, tmp_path, TECTONIC)
        assert pdf.read_bytes().startswith(b"%PDF")


def test_keep_tex(tmp_path):
    build_pdf(load("exam.json"), "classic", {}, "x", tmp_path, TECTONIC, keep_tex=True)
    tex = (tmp_path / "x.tex").read_text()
    assert "%%QUESTION 4" in tex and "Ana Souza" in tex


def test_latex_error_points_to_question(tmp_path):
    exam = Exam.model_validate({"student_name": "A", "questions": [
        {"statement_tex": "fine"}, {"statement_tex": r"broken \undefinedmacro here"}]})
    with pytest.raises(BuildError, match=r"(?s)LaTeX error.*Undefined control sequence.*question 2"):
        build_pdf(exam, "classic", {}, "x", tmp_path, TECTONIC)


def test_missing_image(tmp_path):
    with pytest.raises(BuildError, match="graph.png"):
        build_pdf(load("exam_with_image.json"), "classic", {}, "x", tmp_path, TECTONIC)
