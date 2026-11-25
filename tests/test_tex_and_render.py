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


from qtopdf.render import render_key_body  # noqa: E402

SECTIONED = {"student_name": "A", "sections": [
    {"title": "Parte A & B", "intro_tex": "Leia \\(x\\).", "questions": [
        {"statement_tex": "q1", "alternatives": ["x", {"content_tex": "y", "is_correct": True}],
         "explanation_tex": "because"},
        {"statement_tex": "q2", "items": [{"statement_tex": "i1", "answer_tex": "42"}, "i2"]}]},
    {"title": "Parte C", "questions": [{"statement_tex": "q3"}]}]}


def test_sections_render_with_continuous_numbering():
    body = render_body(Exam.model_validate(SECTIONED), {})
    assert r"\examsection{Parte A \& B}{Leia \(x\).}" in body and r"\examsection{Parte C}{}" in body
    assert [int(n) for n in __import__("re").findall(r"%%QUESTION (\d+)", body)] == [1, 2, 3]
    assert body.index("Parte C") < body.index("q3") and body.index("q2") < body.index("Parte C")
    assert r"\providecommand{\examsection}" in body


def test_flat_exam_unchanged():
    body = render_body(Exam.model_validate({"student_name": "A", "questions": [{"statement_tex": "q"}]}), {})
    assert "examsection" not in body and body.startswith("%%QUESTION 1")


@pytest.mark.parametrize("payload", [
    {"student_name": "A"},
    {"student_name": "A", "questions": [{"statement_tex": "q"}], "sections": [{"title": "s", "questions": [{"statement_tex": "q"}]}]},
    {"student_name": "A", "sections": [{"title": "s", "questions": []}]},
])
def test_questions_xor_sections(payload):
    with pytest.raises(ValueError):
        Exam.model_validate(payload)


def test_answer_key_body():
    exam = Exam.model_validate(SECTIONED)
    full = render_key_body(exam, {}, explanations=True, title="Gabarito")
    assert r"\examkeytitle{Gabarito}" in full and r"\examcorrect{B}" in full
    assert r"\examexplanation{because}" in full and r"\item \examanswer{42}" in full
    assert r"\item \examnoanswer" in full                      # item without an answer
    assert full.rstrip().endswith("\\examnoanswer\n\\end{examquestion}")   # q3: nothing given
    assert "Leia" not in full and r"\examsection{Parte C}{}" in full    # intros are left out of the key
    answers = render_key_body(exam, {}, explanations=False)
    assert "examexplanation{" not in answers and r"\examcorrect{B}" in answers


def test_forbidden_tex_in_answers_and_intro():
    with pytest.raises(ValueError):
        Exam.model_validate({"student_name": "A", "questions": [{"statement_tex": "q", "answer_tex": r"\input{x}"}]})
    with pytest.raises(ValueError):
        Exam.model_validate({"student_name": "A", "sections": [{"title": "s", "intro_tex": r"\write18", "questions": [{"statement_tex": "q"}]}]})
