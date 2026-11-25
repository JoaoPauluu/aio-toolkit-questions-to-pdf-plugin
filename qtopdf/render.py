"""Exam model -> LaTeX body. Text fields are raw LaTeX fragments; only the structure is generated here,
using the standard template macros (see docs/TEMPLATES.md)."""
from __future__ import annotations

import re
from string import ascii_uppercase
from typing import TYPE_CHECKING

from .tex_safety import check_tex

if TYPE_CHECKING:
    from .schema import Exam, Image, Question

IMAGE_PLACEHOLDER = re.compile(r"\{\{image:([A-Za-z0-9_-]+)\}\}")
_SPECIAL = {
    "\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#",
    "_": r"\_", "{": r"\{", "}": r"\}", "~": r"\textasciitilde{}", "^": r"\textasciicircum{}",
}


class RenderError(ValueError):
    pass


def escape_plain(text: str) -> str:
    """For plain-text metadata (student name, title, date). Question text is NOT escaped."""
    return "".join(_SPECIAL.get(c, c) for c in text.strip())


def all_images(q: Question) -> list[Image]:
    return [*q.images, *(im for it in q.items for im in it.images)]


def referenced_images(exam: Exam) -> set[str]:
    return {im.file for q in exam.all_questions() for im in all_images(q)}


def _image_tex(im: Image, aliases: dict[str, str]) -> str:
    return rf"\examimage{{{aliases[im.file]}}}{{{im.width:g}}}{{{im.caption}}}"


def _formatter(aliases: dict[str, str], used: set[int]):
    """fmt(text, scope): check a fragment and replace its {{image:key}} placeholders (ids go into `used`)."""
    def fmt(text: str, scope: dict[str, Image]) -> str:
        check_tex(text)

        def sub(m: re.Match) -> str:
            if m[1] not in scope:
                raise RenderError(f"unknown image placeholder {{{{image:{m[1]}}}}}")
            used.add(id(scope[m[1]]))
            return _image_tex(scope[m[1]], aliases)

        return IMAGE_PLACEHOLDER.sub(sub, text.strip())
    return fmt


def render_question(q: Question, aliases: dict[str, str]) -> str:
    used: set[int] = set()
    fmt = _formatter(aliases, used)
    qscope = {im.key: im for im in q.images}
    stmt = fmt(q.statement_tex, qscope)
    alts = [fmt(a.content_tex, qscope) for a in q.alternatives]
    items = [(it, fmt(it.statement_tex, {**qscope, **{im.key: im for im in it.images}})) for it in q.items]

    def unplaced(images: list[Image]) -> list[str]:  # images without a placeholder follow the text
        return [_image_tex(im, aliases) for im in images if id(im) not in used]

    def points(p: float | None) -> list[str]:
        return [rf"\exampoints{{{p:g}}}"] if p is not None else []

    out = [stmt, *points(q.points), *unplaced(q.images)]
    if alts:
        out += [r"\begin{examalternatives}", *(rf"\item {a}" for a in alts), r"\end{examalternatives}"]
    if items:
        out.append(r"\begin{examparts}")
        for it, text in items:
            out.append("\n".join([r"\item " + text, *points(it.points), *unplaced(it.images)]))
        out.append(r"\end{examparts}")
    return "\n".join(out)


# ---------- sections ----------
# Optional macros: a template defines them (\newcommand) to style sections; these defaults make any template work.
SECTION_DEFAULTS = "\n".join([
    r"\providecommand{\examsection}[2]{\par\bigskip{\large\bfseries #1}\par"
    r"\if\relax\detokenize{#2}\relax\else\smallskip #2\par\fi\medskip}",
])


def _blocks(exam: Exam, render, intros: bool = True) -> str:
    """One examquestion per question (numbered continuously), with an examsection before each section."""
    groups = [(None, exam.questions)] if exam.questions else [(s, s.questions) for s in exam.sections]
    blocks, n = [SECTION_DEFAULTS] if exam.sections else [], 0
    for section, questions in groups:
        if section is not None:
            try:
                intro = check_tex(section.intro_tex).strip() if intros else ""
            except ValueError as e:
                raise RenderError(f"Section '{section.title}': {e}") from e
            blocks.append(f"%%SECTION\n\\examsection{{{escape_plain(section.title)}}}{{{intro}}}")
        for q in questions:
            try:
                body = render(q, n)
            except ValueError as e:  # RenderError or forbidden LaTeX
                raise RenderError(f"Question {n + 1}: {e}") from e
            n += 1
            blocks.append(f"%%QUESTION {n}\n\\begin{{examquestion}}\n{body}\n\\end{{examquestion}}")
    return "\n\n".join(blocks)


def render_body(exam: Exam, aliases: dict[str, str]) -> str:
    return _blocks(exam, lambda q, n: render_question(q, aliases))


# ---------- answer key ----------
# Optional macros: a template may define them (\newcommand) to restyle or translate the answer key.
KEY_DEFAULTS = "\n".join([
    r"\providecommand{\examkeytitle}[1]{\begin{center}{\Large\bfseries #1}\end{center}}",
    r"\providecommand{\examkeysetup}{}",
    r"\providecommand{\examcorrect}[1]{\textbf{Correct alternative:} #1\par}",
    r"\providecommand{\examanswer}[1]{\textbf{Answer:} #1\par}",
    r"\providecommand{\examexplanation}[1]{\textbf{Solution:} #1\par}",
    r"\providecommand{\examnoanswer}{\textit{(no answer given)}\par}",
])


def render_key_question(q: Question, aliases: dict[str, str], explanations: bool) -> str:
    """Answers of one question, taken from the JSON: is_correct, answer_tex, explanation_tex."""
    fmt = _formatter(aliases, set())
    qscope = {im.key: im for im in q.images}

    def lines(answer: str | None, expl: str | None, scope) -> list[str]:
        out = []
        if answer and answer.strip():
            out.append(rf"\examanswer{{{fmt(answer, scope)}}}")
        if explanations and expl and expl.strip():
            out.append(rf"\examexplanation{{{fmt(expl, scope)}}}")
        return out

    correct = [ascii_uppercase[i] for i, a in enumerate(q.alternatives) if a.is_correct]
    out = [rf"\examcorrect{{{', '.join(correct)}}}"] if correct else []
    out += lines(q.answer_tex, q.explanation_tex, qscope)
    if q.items:
        parts = [r"\item " + ("\n".join(lines(it.answer_tex, it.explanation_tex,
                                              {**qscope, **{im.key: im for im in it.images}}))
                              or r"\examnoanswer") for it in q.items]
        out += [r"\begin{examparts}", *parts, r"\end{examparts}"]
    return "\n".join(out) or r"\examnoanswer"


def render_key_body(exam: Exam, aliases: dict[str, str], explanations: bool = True,
                    title: str = "Gabarito") -> str:
    """Answer key: same sections and numbering as the exam, holding only the answers."""
    head = [KEY_DEFAULTS, rf"\examkeytitle{{{escape_plain(title)}}}", r"\ifcsname c@examq\endcsname\setcounter{examq}{0}\fi", r"\examkeysetup"]
    return "\n".join(head) + "\n\n" + _blocks(exam, lambda q, n: render_key_question(q, aliases, explanations), intros=False)
