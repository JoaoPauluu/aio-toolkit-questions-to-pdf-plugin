import pytest

from qtopdf.render import RenderError, render_body
from qtopdf.schema import Exam
from qtopdf.tex_safety import check_tex


@pytest.mark.parametrize("bad", [r"\input{/etc/passwd}", r"\includegraphics{x}", r"\^^5cinput",
                                 r"\csname in\endcsname", r"\usepackage{x}", r"\pdfshellescape"])
def test_forbidden(bad):
    with pytest.raises(ValueError):
        check_tex(bad)


def test_allowed():
    check_tex(r"R\$ 60,00 \\ input \(\frac{1}{2}\) \begin{enumerate}\item a\end{enumerate}")


def test_render_placeholders_and_unplaced_images():
    exam = Exam.model_validate({"student_name": "A", "questions": [{
        "statement_tex": "See {{image:a}}", "alternatives": ["x", {"content_tex": "y", "is_correct": True}],
        "items": ["one"], "images": ["a.png", {"key": "b", "file": "b.png", "width": 0.3}]}]})
    body = render_body(exam, {"a.png": "img1.png", "b.png": "img2.png"})
    assert r"\examimage{img1.png}{0.5}{}" in body            # placed by placeholder
    assert body.count(r"\examimage{img2.png}{0.3}{}") == 1    # unplaced: appended after the statement
    assert r"\begin{examalternatives}" in body and r"\begin{examparts}" in body


def test_unknown_placeholder():
    exam = Exam.model_validate({"student_name": "A", "questions": [{"statement_tex": "{{image:nope}}"}]})
    with pytest.raises(RenderError):
        render_body(exam, {})
