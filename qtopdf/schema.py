"""Exam JSON format: flat questions whose text fields are LaTeX fragments (suffix _tex)."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Annotated

from pydantic import AfterValidator, BaseModel, Field, field_validator, model_validator

from .tex_safety import check_tex

TexStr = Annotated[str, AfterValidator(check_tex)]   # a LaTeX fragment, checked for forbidden commands
KEY_PATTERN = r"^[A-Za-z0-9_-]+$"


class Image(BaseModel):
    key: str = Field(pattern=KEY_PATTERN, max_length=64)   # used as {{image:key}} in the text
    file: str                                              # uploaded file name (or stored path)
    width: float = Field(0.5, gt=0, le=1)                  # fraction of the text width
    caption: TexStr = ""
    alt_text: str = ""


class Alternative(BaseModel):
    content_tex: TexStr
    is_correct: bool = False


class Item(BaseModel):
    """Flat sub-question: a), b), c)..."""
    statement_tex: TexStr
    points: float | None = None
    images: list[Image] = []
    answer_tex: TexStr | None = None          # answer key only
    explanation_tex: TexStr | None = None     # answer key with solutions only

    _images = field_validator("images", mode="before")(lambda cls, v: _image_shorthand(v))

    @model_validator(mode="after")
    def _unique_keys(self):
        _check_keys(self.images)
        return self


class Question(BaseModel):
    statement_tex: TexStr
    points: float | None = None
    alternatives: list[Alternative] = Field([], max_length=26)
    items: list[Item] = Field([], max_length=26)
    images: list[Image] = []
    answer_tex: TexStr | None = None          # answer key only
    explanation_tex: TexStr | None = None     # answer key with solutions only

    _images = field_validator("images", mode="before")(lambda cls, v: _image_shorthand(v))

    @field_validator("alternatives", "items", mode="before")
    @classmethod
    def _text_shorthand(cls, v, info):
        field = "content_tex" if info.field_name == "alternatives" else "statement_tex"
        return [{field: x} if isinstance(x, str) else x for x in v or []]

    @model_validator(mode="after")
    def _unique_keys(self):
        _check_keys(self.images)
        return self


class Section(BaseModel):
    """A titled group of questions. Numbering continues across sections."""
    title: str = Field(max_length=200)                      # plain text (escaped)
    intro_tex: TexStr = ""
    questions: list[Question] = Field(min_length=1)


class Exam(BaseModel):
    student_name: str
    title: str = ""
    date: str = ""                                          # defaults to today
    questions: list[Question] = []                          # either questions...
    sections: list[Section] = []                            # ...or sections, not both

    @model_validator(mode="after")
    def _questions_or_sections(self):
        if bool(self.questions) == bool(self.sections):
            raise ValueError("Give either 'questions' or 'sections' (with at least one question), not both.")
        return self

    def all_questions(self) -> list[Question]:
        return self.questions or [q for s in self.sections for q in s.questions]


def _image_shorthand(v):
    """'graph.png' is accepted as {"file": "graph.png", "key": "graph"}."""
    return [
        {"file": i, "key": re.sub(r"[^A-Za-z0-9_-]", "_", Path(i).stem) or "img"} if isinstance(i, str) else i
        for i in v or []
    ]


def _check_keys(images: list[Image]) -> None:
    keys = [i.key for i in images]
    if len(keys) != len(set(keys)):
        raise ValueError("Image keys must be unique within a question or item.")
