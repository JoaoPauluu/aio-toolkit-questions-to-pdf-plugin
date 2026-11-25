"""Exam model -> LaTeX body. Text fields are raw LaTeX fragments; only the structure is generated here,
using the standard template macros (see docs/TEMPLATES.md)."""
from __future__ import annotations

import re
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
    return {im.file for q in exam.questions for im in all_images(q)}


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


def _blocks(exam: Exam, render) -> str:
    blocks = []
    for n, q in enumerate(exam.questions):
        try:
            body = render(q, n)
        except ValueError as e:  # RenderError or forbidden LaTeX
            raise RenderError(f"Question {n + 1}: {e}") from e
        blocks.append(f"%%QUESTION {n + 1}\n\\begin{{examquestion}}\n{body}\n\\end{{examquestion}}")
    return "\n\n".join(blocks)


def render_body(exam: Exam, aliases: dict[str, str]) -> str:
    return _blocks(exam, lambda q, n: render_question(q, aliases))
