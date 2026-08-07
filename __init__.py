
import html
import re
from anki.hooks import addHook
from aqt.utils import tooltip, showInfo

MATH_PATTERNS = [
    re.compile(r"\\\([\s\S]*?\\\)"),
    re.compile(r"\\\[[\s\S]*?\\\]"),
    re.compile(r"\$\$[\s\S]*?\$\$"),
]

# Syntax-highlighted code blocks wrap each line/token in its own <span>, which
# fragments TAG_SPLIT's output and strips the surrounding context (e.g. an
# "import" line) that would otherwise mark a fragment like "N = 10" as code.
# Protect these blocks whole, before any tag-splitting happens.
CODE_BLOCK_PATTERNS = [
    re.compile(r"<pre\b[\s\S]*?</pre>", re.IGNORECASE),
    re.compile(r"<code\b[\s\S]*?</code>", re.IGNORECASE),
]

# Lightweight Python syntax highlighting for <pre> blocks, styled to resemble
# common dark-theme code blocks (purple keywords, orange numbers, grey comments).
PY_TOKEN = re.compile(
    r"(?P<comment>#[^\n]*)"
    r"|(?P<string>'''[\s\S]*?'''|\"\"\"[\s\S]*?\"\"\"|'(?:\\.|[^'\\\n])*'|\"(?:\\.|[^\"\\\n])*\")"
    r"|(?P<number>\b\d[\d_]*(?:\.[\d_]+)?(?:[eE][+-]?\d+)?\b)"
    r"|(?P<keyword>\b(?:False|None|True|and|as|assert|async|await|break|class|"
    r"continue|def|del|elif|else|except|finally|for|from|global|if|import|in|"
    r"is|lambda|nonlocal|not|or|pass|raise|return|try|while|with|yield)\b)"
)

PY_TOKEN_STYLES = {
    "comment": "color:#7f848e;font-style:italic",
    "string": "color:#98c379",
    "number": "color:#d19a66",
    "keyword": "color:#c678dd",
}

PRE_BLOCK = re.compile(r"(<pre\b[^>]*>)([\s\S]*?)(</pre>)", re.IGNORECASE)

# <pre><code>...</code></pre> is a common nesting (e.g. from pasted markdown);
# the inner tag must be preserved as a real tag, not escaped as code text.
INNER_CODE_TAG = re.compile(r"^\s*(<code\b[^>]*>)([\s\S]*?)(</code>)\s*$", re.IGNORECASE)


def _highlight_python(code):
    escaped = html.escape(code, quote=False)

    def repl(match):
        style = PY_TOKEN_STYLES.get(match.lastgroup)
        if not style:
            return match.group(0)
        return f'<span style="{style}">{match.group(0)}</span>'

    return PY_TOKEN.sub(repl, escaped)


def _highlight_code_blocks(field_html):
    def repl(match):
        open_tag, body, close_tag = match.group(1), match.group(2), match.group(3)
        inner = INNER_CODE_TAG.match(body)
        if inner:
            code_open, code_body, code_close = inner.groups()
            return f"{open_tag}{code_open}{_highlight_python(code_body)}{code_close}{close_tag}"
        return f"{open_tag}{_highlight_python(body)}{close_tag}"

    return PRE_BLOCK.sub(repl, field_html)


TAG_SPLIT = re.compile(r"(<[^>]+>)")

# Matches short inline LaTeX expressions such as \sigma, x_i, f_s, \hat r.
INLINE_LATEX = re.compile(
    r"(?<![A-Za-z])("
    r"\\(?:"
    r"alpha|beta|gamma|delta|epsilon|zeta|eta|theta|iota|kappa|lambda|mu|"
    r"nu|xi|pi|rho|sigma|tau|upsilon|phi|chi|psi|omega|"
    r"Gamma|Delta|Theta|Lambda|Xi|Pi|Sigma|Upsilon|Phi|Psi|Omega|"
    r"sum|prod|int|oint|lim|max|min|sup|inf|log|ln|exp|det|gcd|arg"
    r")(?:_\{?[A-Za-z0-9+\-=]+\}?|\^\{?[A-Za-z0-9+\-=]+\}?)*"
    r"|\\hat\s*\{?[A-Za-z]\}?"
    r"|[A-Za-z](?:_\{?[A-Za-z0-9+\-=]+\}?|\^\{?[A-Za-z0-9+\-=]+\}?)+"
    r"|[A-Za-z](?:_\{?[A-Za-z0-9]+\}?)?\s*=\s*[+-]?\d(?:[\d,]*\d)?(?:\.\d+)?"
    r")(?![A-Za-z])"
)

# A char that can't end a sentence: anything but .!?, or a decimal point (0.5, 10.0)
# that's followed by another digit rather than ending the clause.
_EQ_CHAR = r"(?:[^.!?]|\.(?=\d))"

# Whole-line equations only. Ordinary prose containing \sigma is no longer wrapped.
WHOLE_EQUATION = re.compile(
    r"^\s*"
    r"(?:"
    rf"[A-Za-z\\]{_EQ_CHAR}{{0,240}}\s*=\s*{_EQ_CHAR}{{1,240}}"
    r"|\\frac\s*\{[\s\S]+\}\s*\{[\s\S]+\}"
    r")"
    r"\s*$"
)

# Recognized LaTeX macros that mark a line as "definitely math" even with no
# "=" sign at all, e.g. "\sqrt{Np(1-p)}" or "\frac{5000}{351}\approx14.2".
_KNOWN_LATEX_CMD = (
    r"\\(?:frac|sqrt|binom|sum|prod|int|oint|lim|max|min|sup|inf|log|ln|exp|det|gcd|arg|"
    r"times|approx|le|leq|ge|geq|neq|ne|cdot|pm|sim|propto|equiv|subset|supset|in|notin|forall|exists|"
    r"to|infty|cdots|ldots|dots|partial|nabla|hat|bar|vec|"
    r"text|mid|Pr|left|right|quad|qquad|"
    r"rightarrow|Rightarrow|leftarrow|Leftarrow|leftrightarrow|Leftrightarrow|implies|iff|"
    r"mathbb|mathcal|overline|underline|"
    r"alpha|beta|gamma|delta|epsilon|zeta|eta|theta|iota|kappa|lambda|mu|nu|xi|pi|rho|sigma|"
    r"tau|upsilon|phi|chi|psi|omega|"
    r"Gamma|Delta|Theta|Lambda|Xi|Pi|Sigma|Upsilon|Phi|Psi|Omega)(?![A-Za-z])"
)

# A line made entirely of math-safe characters, containing at least one
# recognized LaTeX command, needs no "=" to be treated as a whole equation.
BARE_LATEX = re.compile(
    rf"^(?=[\s\S]*{_KNOWN_LATEX_CMD})[A-Za-z0-9+\-*/^_(){{}}|,.\\\s]+$"
)

POLISH_LETTERS = re.compile(r"[ąćęłńóśźżĄĆĘŁŃÓŚŹŻ]")

# An ordinary English word (4+ letters, not a "\command"). A line with two or
# more of these is prose that happens to contain "=", not a bare equation
# ("is extraordinarily unlikely under p = 0.5, which explains..."), so the
# whole line must not be wrapped -- only the actual equation fragment should be.
PROSE_WORD = re.compile(r"(?<!\\)\b[A-Za-z]{4,}\b")

# \text{...} exists specifically to embed English words inside math mode
# (e.g. "P(\text{data}\mid p)"), so words inside it must not count as prose.
TEXT_ARG = re.compile(r"\\text\{[^{}]*\}")

# A trailing "(...)" comment attached with a space, e.g. 'g = 242,000 ("failures")'
# -- an aside about the equation, not part of it. No space before "(" (as in
# "P(X=6)") means the parens are part of the math, so this is left alone.
TRAILING_ASIDE = re.compile(r"^(.*\S)(\s+)(\([^()]*\))$")


def _looks_like_prose(core):
    checked = TEXT_ARG.sub("", core)
    if len(PROSE_WORD.findall(checked)) >= 2:
        return True
    # A multi-word left-hand side ("probability of boy = p") is a descriptive
    # label, not an equation identifier -- real ones are short ("p", "E[X]",
    # or a LaTeX construct like "\hat p", which is one unit despite the space).
    eq_pos = checked.find("=")
    if eq_pos != -1:
        lhs = checked[:eq_pos]
        if "\\" not in lhs and len(lhs.split()) >= 2:
            return True
    return False

# Signals that a block is source code (e.g. a pasted Python snippet), not an
# equation, even though "b = 251_000" has the exact same shape as real math.
CODE_MARKER = re.compile(
    r"^\s*(?:"
    r"import\s+\w|from\s+\w+(?:\.\w+)*\s+import\b|"
    r"def\s+\w+\s*\(|class\s+\w+\b|print\s*\("
    r")",
    re.MULTILINE,
)


def _protect_math(text):
    saved = []

    def repl(match):
        token = f"ANKIMATHPLACEHOLDER{len(saved)}TOKEN"
        saved.append(match.group(0))
        return token

    for pattern in CODE_BLOCK_PATTERNS + MATH_PATTERNS:
        text = pattern.sub(repl, text)
    return text, saved


def _restore_math(text, saved):
    def repl(match):
        return saved[int(match.group(1))]
    return re.sub(r"ANKIMATHPLACEHOLDER(\d+)TOKEN", repl, text)


def _transform_text_segment(text):
    if not text or "ANKIMATHPLACEHOLDER" in text:
        return text

    # Leave whole blocks of source code untouched. "b = 251_000" has the same
    # shape WHOLE_EQUATION looks for, but it's code, not math to typeset.
    if CODE_MARKER.search(text):
        return text

    # Equation-matching must never span a line break, or unrelated
    # statements on separate lines get fused into one "equation".
    if "\n" in text:
        return "\n".join(_transform_text_segment(line) for line in text.split("\n"))

    stripped = text.strip()
    if not stripped:
        return text

    # A single trailing sentence-ending mark (e.g. "x = 5.") shouldn't stop
    # the line from being recognized as an equation; just keep it outside \( \).
    core, punct = stripped, ""
    if stripped[-1] in ".!?":
        core, punct = stripped[:-1].rstrip(), stripped[-1]

    # A trailing "(aside)" describing the equation shouldn't be pulled into
    # the math wrapper either.
    aside = ""
    aside_match = TRAILING_ASIDE.match(core)
    if aside_match:
        core, aside = aside_match.group(1), aside_match.group(2) + aside_match.group(3)

    # Wrap the entire node only when it is clearly an equation, not a prose
    # sentence that merely contains one.
    if (
        (WHOLE_EQUATION.match(core) or BARE_LATEX.match(core))
        and not POLISH_LETTERS.search(core)
        and not _looks_like_prose(core)
    ):
        lead = text[: len(text) - len(text.lstrip())]
        tail = text[len(text.rstrip()):]
        return f"{lead}\\({core}\\){aside}{punct}{tail}"

    # Otherwise wrap only short inline mathematical fragments.
    return INLINE_LATEX.sub(lambda m: f"\\({m.group(1)}\\)", text)


def transform_field_html(field_html):
    field_html = _highlight_code_blocks(field_html)
    protected, saved = _protect_math(field_html)
    parts = TAG_SPLIT.split(protected)

    for i, part in enumerate(parts):
        if not part.startswith("<"):
            parts[i] = _transform_text_segment(part)

    return _restore_math("".join(parts), saved)


def run_mathjax_helper(editor):
    field_index = getattr(editor, "currentField", None)

    if field_index is None or field_index < 0:
        showInfo("Click into a card field first, then click Mx.")
        return

    if editor.note is None:
        showInfo("There is no active note to edit.")
        return

    try:
        original = editor.note.fields[field_index]
    except Exception:
        showInfo("Could not read the active field.")
        return

    transformed = transform_field_html(original)

    if transformed == original:
        tooltip("No new LaTeX fragments found.", period=2200)
        return

    editor.note.fields[field_index] = transformed

    refreshed = False
    for method_name in ("loadNoteKeepingFocus", "loadNote"):
        method = getattr(editor, method_name, None)
        if callable(method):
            try:
                method()
                refreshed = True
                break
            except TypeError:
                try:
                    method(focusTo=field_index)
                    refreshed = True
                    break
                except Exception:
                    pass
            except Exception:
                pass

    if not refreshed:
        method = getattr(editor, "setNote", None)
        if callable(method):
            try:
                method(editor.note, focusTo=field_index)
            except Exception:
                pass

    tooltip("Processed the active field. Check the result.", period=2200)


def add_mathjax_button(buttons, editor):
    editor._links["mathjax_helper"] = run_mathjax_helper
    button = editor._addButton(
        None,
        "mathjax_helper",
        "Detect LaTeX and add MathJax markers",
        label="Mx",
    )
    return buttons + [button]


addHook("setupEditorButtons", add_mathjax_button)
