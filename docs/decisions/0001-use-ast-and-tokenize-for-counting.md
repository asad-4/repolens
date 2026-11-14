# 0001 — Use `ast` and `tokenize` instead of line-based regex for counting

- Status: accepted
- Date: 2026-11-14
- Requirements: R2, R3

## Decision (Y-statement)

In the context of **counting lines of code (R2) and functions/classes (R3) in
arbitrary Python files**,
facing **the need to tell real code from comments, strings and docstrings, and to
count `def`, `async def` and `class` correctly at any nesting level**,
we decided for **Python's own standard-library `ast` module (for definitions) and
`tokenize` module (for lines of code), with a simple line-based fallback for
LOC when tokenizing fails**,
and neglected **regular expressions / string matching on each line**, and
**a third-party parser such as `libcst` or `radon`**,
to achieve **counts that agree with how Python itself reads the file (e.g. a `#`
inside a string is not a comment; `def` inside a docstring is not a function;
async functions and methods are always found)**,
accepting that **a file with a syntax error cannot be parsed by `ast`, so its
function and class counts are reported as 0 with a `(parse error)` marker, and
that parsing is slower than a regex scan**.

## Alternatives considered

| Option | Pros | Cons |
|---|---|---|
| **`ast` + `tokenize` (chosen)** | Exact: uses Python's own grammar. Handles strings, docstrings, decorators, nested and async defs. Standard library, so it meets the "stdlib + pytest only" rule. | Fails on files with syntax errors. Behaviour depends on the Python version running repolens (e.g. 3.9 cannot parse 3.10 `match` syntax). |
| Regex per line (`^\s*(async\s+)?def\s`, `^\s*class\s`, `^\s*#`) | Simple, fast, works on broken files. | Wrong on `def`/`class`/`#` inside multi-line strings, and on lines like `x = "#"`. Needs its own handling for multi-line strings, which is a home-made tokenizer. |
| Third-party parser (`libcst`, `radon`) | Tolerant parsing, richer metrics. | Breaks the "standard library plus pytest only" rule in CLAUDE.md. |

## Consequences

- Files in the scanned project that use syntax newer than the running interpreter
  will show `(parse error)`. This is visible in the output rather than silently
  miscounted.
- Docstrings count as lines of code, because to the tokenizer they are string
  tokens, not comments. `spec.md` R2 states this explicitly.
- If tokenizing fails (e.g. an unterminated triple-quoted string), LOC falls back
  to "non-blank lines not starting with `#`", so LOC is still reported.
