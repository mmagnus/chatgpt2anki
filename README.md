# MathJax Helper

<img width="1326" height="1722" alt="sc 2026-08-05 at 17 18 42" src="https://github.com/user-attachments/assets/dbbef179-55e6-40fb-9901-38b49ef6a9e6" />

An Anki editor add-on for pasting AI chat answers (ChatGPT, Claude, etc.)
straight into a card. It adds an **Mx** button to the field toolbar that
scans the active field, wraps anything that looks like LaTeX math in
`\( ... \)` so Anki's MathJax renders it, and syntax-highlights any pasted
Python code — without mangling the code or the surrounding prose.

## The problem

Chat answers mix plain prose, math notation, and code in the same reply.
Pasted as-is into an Anki field, none of the LaTeX renders — you just see
raw text like `\sigma` or `\frac{5000}{351}\approx14.2`. Manually wrapping
every fragment in `\( \)` by hand is tedious and easy to get wrong.

## What it does

Click into a field, then click **Mx**. The add-on:

1. **Wraps whole equations.** A line that's essentially just math —
   `p = 0.5`, `N = 252000 + 242000`, `\sqrt{Np(1-p)}`, `\frac{5000}{351}\approx14.2`
   — gets the whole thing wrapped: `\(p = 0.5\)`. This works whether or not
   the line has an `=` sign, contains decimals, ends with a period, or has
   a trailing `(aside in parentheses)` — the aside is correctly left outside
   the math.

2. **Wraps only the fragment inside prose.** A sentence that merely
   *mentions* an equation — `"...is unlikely under p = 0.5, which
   explains..."` — only gets `p = 0.5` wrapped. The add-on won't swallow
   the whole sentence into one math block (which would otherwise render
   with all the word-spacing collapsed, since MathJax ignores plain
   whitespace in math mode).

3. **Wraps short inline symbols.** Bare Greek letters (`\sigma`, `\Gamma`),
   operators (`\sum`, `\prod_{i=1}^{n}`), subscripts (`x_i`, `f_s`), and
   `\hat`-notation get wrapped individually wherever they appear in text.

4. **Leaves code alone.** Anything that looks like source code — a Python
   `import`/`from...import`/`def`/`class`/`print(` line, or content inside
   a `<pre>`/`<code>` block — is left completely untouched by the math
   logic, so things like `b = 251_000` don't get corrupted into subscript
   notation (`251` with a tiny `0` under it).

5. **Syntax-highlights Python.** Code inside `<pre>` (including the common
   `<pre><code>...</code></pre>` nesting) gets keywords, numbers, strings,
   and comments colored, matching a typical dark-theme code block.

## Example

Paste this into a field:

```
The code computed
p = 0.5
N = 252000 + 242000

A 14-sigma event is extraordinarily unlikely under p = 0.5, which explains
why the PMF is essentially zero.
```

Click **Mx**, and it becomes:

```
The code computed
\(p = 0.5\)
\(N = 252000 + 242000\)

A 14-sigma event is extraordinarily unlikely under \(p = 0.5\), which
explains why the PMF is essentially zero.
```

...which MathJax then renders as proper typeset math, in place, with the
surrounding prose untouched.

## Usage

1. Click into the field you want to fix, in Anki's card editor.
2. Click the **Mx** button in the field toolbar.
3. The field is transformed in place and reloaded so you can check the
   result. If nothing looked like new LaTeX, you'll get a "no new LaTeX
   fragments found" notice instead.

## Notes

- The add-on only *adds* `\( \)` wrapping — it doesn't detect or remove
  incorrect wrapping from an earlier run. If a field was mangled before a
  fix, re-paste the original text and re-run Mx rather than expecting it
  to self-heal.
- Existing `\( \)`, `\[ \]`, and `$$ $$` math, and any `<pre>`/`<code>`
  block, is always protected and passed through as-is.
