# Question format

Questions are **flat** and their text fields (names ending in `_tex`) are **LaTeX fragments**: the body
text you would type inside a document, not plain text. It is the same format as the Questions to PDF project,
so its exam JSON files work here unchanged.

## Fields

| Field | Where | Meaning |
|-------|-------|---------|
| `statement_tex` | question, item | The statement. Required. |
| `alternatives[]` | question | `{content_tex, is_correct}`. Labels A, B, C... are automatic. A plain string is accepted. |
| `items[]` | question | Flat sub-items a), b), c)...: `{statement_tex, points?, images?}`. A plain string is accepted. |
| `images[]` | question, item | `{key, file, width?, caption?, alt_text?}`. `"fig.png"` is accepted as shorthand (key = `fig`). |
| `points` | question, item | Optional. Printed with `\exampoints`. |


## Writing fragments

- **Escape special characters** outside math: `\%  \&  \#  \_  \$  \{  \}`. Currency is `R\$ 60,00`.
- **Math:** `\( ... \)` inline, `\[ ... \]` display (`$...$` also works in LaTeX, but `\(...\)` avoids
  ambiguity with currency).
- **Paragraphs:** a blank line. A single newline is only a space; use `\\` for a forced line break.
- **Tables:** use `examtable` (never `tabular`), so every template can style it:
  ```latex
  \begin{examtable}{3}{Table 1}
  \examth{Day} & \examth{Hours} & \examth{Usage} \\ \examhline
  Day 1 & 10 h & 14 kWh \\ \examhline
  \end{examtable}
  ```
- **Lists:** `enumerate` / `itemize`. Deeper sub-items inside an item:
  `\begin{enumerate}[label=\roman*)] ... \end{enumerate}`. Alternatives inside an item:
  `\begin{examalternatives} \item ... \end{examalternatives}`.
- **Images:** write `{{image:key}}` where the figure goes and give the image that `key`. Images with no
  placeholder follow the statement of the question/item that owns them. A figure is a block, so a
  placeholder in the middle of a sentence splits the paragraph. Item text can use both the item's own
  images and the question's images. Types: png, jpg, pdf (max 10 MB).
- **Rejected:** `\input`, `\include`, `\includegraphics`, `\usepackage`, `\documentclass`, `\write`,
  `\read`, `\openin`, `\csname`, `\catcode`, `\pdf...`, `\special`, `^^`. In JSON, double every backslash:
  `"\\(x^2\\)"`.

## Example (exam JSON)

```json
{
  "student_name": "Ana Souza",
  "questions": [
    { "statement_tex": "Solve:", "points": 4,
      "items": [ "\\(2x+3=11\\)", "\\(x^2-5x+6=0\\)" ] },
    { "statement_tex": "See {{image:fig}}. Is the root positive?",
      "alternatives": [ { "content_tex": "Yes", "is_correct": true }, "No" ],
      "images": [ { "key": "fig", "file": "graph.png", "width": 0.5, "caption": "Graph of \\(f\\)" } ] }
  ]
}
```
