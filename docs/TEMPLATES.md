# Writing a template

A template is one `.tex` file in the plugin's `templates/` folder; its file name (without `.tex`) is the value of the
`template` input. To add one, drop the file in `templates/` **and** add it to the `template` options in
`plugin.yaml` (the server only accepts listed values; `tests/test_templates.py` checks the two match).
The software never edits your layout. It does two things:

1. fills a few `<<placeholders>>`, and
2. writes the questions as LaTeX using a **fixed set of macros and environments that the template defines**.

Question text itself is LaTeX written by the question author (see `docs/QUESTION_FORMAT.md`). The same
fragments must therefore compile in every template, so the contract below is strict. To change how
something looks, **define or `\renewcommand` the contract macros in your template**; the software and the
stored questions stay the same.

## 1. Placeholders

Written as `<<name>>` anywhere in the file (preamble included, e.g. in headers).

| Placeholder        | Required | Content                                                                           |
|--------------------|----------|-----------------------------------------------------------------------------------|
| `<<student_name>>` | yes      | Student name. Plain text, already escaped for LaTeX                               |
| `<<body>>`         | yes      | All questions, generated with the macros below. Use it once, inside `document`    |
| `<<title>>`        | no       | `title` from the JSON (plain text, escaped; may be empty)                         |
| `<<date>>`         | no       | `date` from the JSON, or today's date (plain text, escaped)                       |

Unknown placeholders are rejected. A placeholder may be used several times. Do not edit or wrap `<<body>>`
in a way that drops the `%%QUESTION n` comment lines inside it: they are used to tell you which question a
LaTeX error came from.

## 2. The contract

Every template must define all of these.

| Name | Kind | Emitted by | Meaning |
|------|------|-----------|---------|
| `examquestion` | environment | software | One question. Starts with the statement, then the points, unplaced images, alternatives and parts. **Numbering is the template's job.** |
| `examalternatives` | list environment | software, and authors | Multiple-choice options, each an `\item`. Must be usable inside `examparts` items. |
| `examparts` | list environment | software | Flat sub-items (a, b, c...), each an `\item`. |
| `\examimage{file}{width}{caption}` | command | software | A figure. `file` is in the build folder; `width` is a number 0-1 = fraction of `\linewidth`; `caption` is a LaTeX fragment and may be empty. |
| `\exampoints{value}` | command | software | Printed after the text of a question/item that has `points` (only emitted when set). |
| `examtable{ncols}{caption}` | environment | authors | A table. Body = rows: cells separated by `&`, each row ending `\\ \examhline`. It must wrap its own `tabular` and should use wrapping (`p`) columns so long cells do not overflow. `caption` may be empty. |
| `\examth{text}` | command | authors | One header cell. Format only its argument: no `&` or `\\` inside. |
| `\examhline` | command | authors, template | Rule after every table row (the template also calls it at the table top). `\hline` gives a grid; `\relax` gives none. |

**Packages.** Question fragments may use ordinary math, lists and tables, so every template must load at
least `amsmath`, `amssymb`, `graphicx`, `enumitem` and `array`, and
`\usepackage[utf8]{inputenc}` and `\usepackage[T1]{fontenc}` so the template also compiles with pdflatex.

The easiest start is to copy the block marked `STANDARD CONTRACT` in `templates/classic.tex` and restyle it.

## 3. What the software generates

```latex
%%QUESTION 2
\begin{examquestion}
Look at the figure \examimage{img1.png}{0.5}{Figure 1} and solve:
\exampoints{4}
\begin{examalternatives}
\item \(x=1\)
\item \(x=2\)
\end{examalternatives}
\begin{examparts}
\item Compute \(2x+3\).
\exampoints{2}
\item Observe:
\begin{examtable}{2}{}
\examth{A} & \examth{B} \\ \examhline
1 & 2 \\ \examhline
\end{examtable}
\end{examparts}
\end{examquestion}
```

Rules the generator follows:

- Fragments are inserted **verbatim**: nothing is escaped. Only `<<student_name>>`, `<<title>>` and `<<date>>`
  (plain text) are escaped.
- `{{image:key}}` inside a fragment becomes `\examimage{...}{...}{...}`. An image that no placeholder
  mentions is appended right after its owner's statement.
- Alternatives belong to the question, items are one flat level. Anything deeper is written inside the
  fragment with `enumerate`, `itemize` or `examalternatives`.

## 4. Customizing: redefine the macros

Everything visual is yours. Examples:

```latex
\renewcommand{\examhline}{\relax}                        % tables without rules
\renewcommand{\theexamq}{\arabic{examq}}                 % question numbers as 1, 2, 3
\setlist[examalternatives]{label=(\alph*),leftmargin=2em}% options as (a) (b) (c)
\renewcommand{\examth}[1]{\textsc{#1}}                   % small-caps table headers
\newcommand{\exampoints}[1]{\hfill\fbox{#1}}             % boxed points
```

## 5. Engine, safety and compilation

- **Engine:** templates are compiled with [Tectonic](https://tectonic-typesetting.github.io/) (XeTeX). A
  `% engine: ...` line is accepted for compatibility with Questions to PDF and ignored. pdflatex-style preambles
  (`inputenc`, `fontenc`, `helvet`, ...) work. Packages are downloaded on first use and cached in `/data/cache`.
- **Sandboxing:** Tectonic runs with `--untrusted` (no shell escape) in a temporary folder holding only
  `main.tex` and the images, with a 300 s timeout. It reruns TeX until references settle (so `\pageref`/`lastpage` work).
- **Forbidden in fragments** (checked when saving and again when compiling): `\input`, `\include`,
  `\includegraphics`, `\usepackage`, `\documentclass`, `\write`, `\read`, `\openin`, `\csname`, `\catcode`,
  `\pdf...` primitives, `\special`, `^^` sequences and `\begin{document}`. These limits apply to fragments,
  not to your template.
- **Self-contained:** the template must compile alone in an empty folder (TeX Live/CTAN packages are fine, local
  `.sty` files are not). Use `<<body>>` once.

## 6. Validation

Every time a template is used it is checked for the required placeholders, unknown placeholders, the eight
required names above and the required packages. A missing item is reported by name in the job error. If LaTeX
itself fails you see the first error lines and the question the error was found in.

## 7. Migrating older templates

Templates written before raw-LaTeX questions need `examtable`, `\examth` and `\examhline` (copy them from
`classic.tex`) and the package list in section 2.

## 8. Minimal skeleton

```latex
% engine: pdflatex
\documentclass{article}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{amsmath,amssymb,graphicx,enumitem,array}

\newcounter{examq}
\newenvironment{examquestion}{\par\medskip\refstepcounter{examq}\textbf{\theexamq.} }{\par}
\newlist{examalternatives}{enumerate}{2}\setlist[examalternatives]{label=\Alph*)}
\newlist{examparts}{enumerate}{3}\setlist[examparts]{label=\alph*)}
\newcommand{\examimage}[3]{\begin{center}\includegraphics[width=#2\linewidth]{#1}\end{center}}
\newcommand{\exampoints}[1]{(#1 pts)}
\newcommand{\examhline}{\hline}
\newcommand{\examth}[1]{\textbf{#1}}
\newenvironment{examtable}[2]
  {\begin{center}\begin{tabular}{|*{#1}{c|}}\examhline}{\end{tabular}\end{center}}

\begin{document}
<<student_name>> -- <<date>>

<<body>>
\end{document}
```
