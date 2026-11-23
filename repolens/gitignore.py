"""Parse .gitignore files and decide whether a path is ignored (R5, Round 4).

Standard library only; git is not needed. See docs/decisions/0004 for why
RepoLens has its own matcher, and spec.md "R5 (changed in Round 4)" for the
exact rules implemented here.
"""

import re
from dataclasses import dataclass
from typing import List, Optional, Pattern, Tuple


@dataclass
class Rule:
    base: str  # folder holding the .gitignore, relative to the scan root ('' = root)
    regex: Pattern  # matched against the name (unanchored) or relative path
    anchored: bool  # True: match the path relative to base; False: the name
    negate: bool  # "!pattern": a match means "not ignored"
    dir_only: bool  # "pattern/": only folders match


def _strip_trailing_spaces(line: str) -> str:
    """Drop trailing spaces unless the last one is escaped with a backslash."""
    stripped = line.rstrip(" ")
    if stripped != line and _ends_with_escape(stripped):
        # Keep exactly one escaped space; the backslash is handled later.
        return stripped + " "
    return stripped


def _ends_with_escape(text: str) -> bool:
    """True if text ends with an odd number of backslashes."""
    count = len(text) - len(text.rstrip("\\"))
    return count % 2 == 1


class _Unmatchable(Exception):
    """The pattern can never match (as in git, e.g. an unclosed '[')."""


def _translate(pattern: str) -> str:
    """Turn a gitignore glob (no leading '!' or trailing '/') into a regex.

    Raises _Unmatchable for a '[' without a closing ']'.
    """
    out = []
    i = 0
    n = len(pattern)
    while i < n:
        c = pattern[i]
        if c == "*":
            if pattern.startswith("**", i):
                at_start = i == 0
                after = i + 2
                if at_start and pattern.startswith("/", after):
                    out.append("(?:.*/)?")  # leading "**/": any folder
                    i = after + 1
                    continue
                if i > 0 and pattern[i - 1] == "/":
                    if after == n:
                        out.append(".*")  # trailing "/**": everything inside
                        i = after
                        continue
                    if pattern.startswith("/", after):
                        out.append("(?:.*/)?")  # "/**/": zero or more folders
                        i = after + 1
                        continue
                # Any other "**" behaves like "*".
                while i < n and pattern[i] == "*":
                    i += 1
                out.append("[^/]*")
                continue
            out.append("[^/]*")
            i += 1
        elif c == "?":
            out.append("[^/]")
            i += 1
        elif c == "[":
            end, cls = _char_class(pattern, i)
            if cls is None:
                raise _Unmatchable(pattern)
            out.append(cls)
            i = end
        elif c == "\\" and i + 1 < n:
            out.append(re.escape(pattern[i + 1]))
            i += 2
        else:
            out.append(re.escape(c))
            i += 1
    return "".join(out)


def _char_class(pattern: str, start: int) -> Tuple[int, Optional[str]]:
    """Parse "[...]" at start. Return (index after ']', regex) or (start, None)."""
    i = start + 1
    n = len(pattern)
    negate = False
    if i < n and pattern[i] in "!^":
        negate = True
        i += 1
    items = []
    first = True
    while i < n:
        c = pattern[i]
        if c == "]" and not first:
            body = "".join(items)
            if negate:
                return i + 1, "[^/" + body + "]"
            return i + 1, "(?!/)[" + body + "]"
        first = False
        if c == "\\" and i + 1 < n:
            items.append(re.escape(pattern[i + 1]))
            i += 2
        elif c == "-" and items and i + 1 < n and pattern[i + 1] != "]":
            items.append("-")
            i += 1
        else:
            items.append(re.escape(c))
            i += 1
    return start, None  # no closing "]"


def parse_gitignore(text: str, base: str) -> List[Rule]:
    """Return the rules in a .gitignore's text, in file order.

    base is the folder that holds the .gitignore, relative to the scan root,
    '/'-separated ('' for the root itself).
    """
    rules = []
    for raw in text.split("\n"):
        line = raw[:-1] if raw.endswith("\r") else raw
        line = _strip_trailing_spaces(line)
        if not line or line.startswith("#"):
            continue
        negate = line.startswith("!")
        if negate:
            line = line[1:]
        dir_only = line.endswith("/") and not _ends_with_escape(line[:-1])
        if dir_only:
            line = line.rstrip("/")
        if not line:
            continue
        anchored = "/" in line
        if line.startswith("/"):
            line = line[1:]
        if not line:
            continue
        try:
            regex = re.compile(_translate(line), re.DOTALL)
        except _Unmatchable:
            continue  # git never matches such a pattern
        rules.append(Rule(base, regex, anchored, negate, dir_only))
    return rules


def is_ignored(rules: List[Rule], rel_path: str, is_dir: bool) -> bool:
    """Apply rules (shallowest .gitignore first, file order) to rel_path.

    rel_path is relative to the scan root and '/'-separated. The last
    matching rule decides; no match means "not ignored".
    """
    name = rel_path.rsplit("/", 1)[-1]
    for rule in reversed(rules):
        if rule.dir_only and not is_dir:
            continue
        if rule.base:
            prefix = rule.base + "/"
            if not rel_path.startswith(prefix):
                continue
            sub = rel_path[len(prefix):]
        else:
            sub = rel_path
        target = sub if rule.anchored else name
        if rule.regex.fullmatch(target):
            return not rule.negate
    return False
