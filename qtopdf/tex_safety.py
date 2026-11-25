"""Safety net for LaTeX fragments (question statements, alternatives, captions...).

Fragments are real LaTeX, so they are checked before they are stored or compiled. This is defense in
depth: the compiler also runs with shell-escape off and paranoid file access (see build.py).
Images only enter a document through {{image:key}} placeholders, never through \\includegraphics.
"""
import re

_FORBIDDEN = re.compile(
    r"\\(?:input|include|includeonly|InputIfFileExists|openin|openout|read|readline|write|immediate|"
    r"newwrite|newread|closein|closeout|catcode|csname|usepackage|RequirePackage|documentclass|"
    r"includegraphics|verbatiminput|lstinputlisting|special|directlua|latelua|luaescapestring|"
    r"pdf[A-Za-z@]*|XeTeX[A-Za-z@]*|ShellEscape|write18|scantokens|endlinechar|everyeof)(?![A-Za-z@])"
    r"|\^\^|\\(?:begin|end)\s*\{document\}"
)


def check_tex(text: str) -> str:
    """Return the text unchanged, or raise ValueError if it contains a forbidden construct."""
    probe = text.replace("\\\\", "  ")  # a forced line break "\\" followed by a word is not a command
    if m := _FORBIDDEN.search(probe):
        raise ValueError(f"Forbidden LaTeX in fragment: {m[0]!r}")
    return text
