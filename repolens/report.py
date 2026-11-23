"""Render scan results as text (R2, R3, R4, R9)."""

from typing import List, Optional

from repolens.scanner import FileStats

_HEADERS = ("File", "Lines", "Functions", "Classes")


def largest_files(stats: List[FileStats], n: int) -> List[FileStats]:
    """The n files with the most lines of code, highest first (R9).

    Equal LOC keeps path order, so the result is deterministic."""
    return sorted(stats, key=lambda s: (-s.loc, s.path))[:n]


def format_report(
    stats: List[FileStats], inaccessible_dirs: int = 0, top: Optional[int] = None
) -> str:
    lines = []
    # R9: the table may show only the largest files; the summary below always
    # uses every file in `stats`.
    shown = stats if top is None else largest_files(stats, top)
    if top is not None and stats:
        lines.append(
            "Showing the {} largest of {} files "
            "(ranked by lines of code).".format(len(shown), len(stats))
        )
        lines.append("")
    if shown:
        path_w = max(len(_HEADERS[0]), max(len(s.path) for s in shown))
        num_w = [len(h) for h in _HEADERS[1:]]
        lines.append(
            "{:<{pw}}  {:>{w0}}  {:>{w1}}  {:>{w2}}".format(
                *_HEADERS, pw=path_w, w0=num_w[0], w1=num_w[1], w2=num_w[2]
            )
        )
        lines.append("  ".join("-" * w for w in [path_w] + num_w))
        for s in shown:
            row = "{:<{pw}}  {:>{w0}}  {:>{w1}}  {:>{w2}}".format(
                s.path, s.loc, s.functions, s.classes,
                pw=path_w, w0=num_w[0], w1=num_w[1], w2=num_w[2],
            )
            if s.note:
                row += "  ({})".format(s.note)
            lines.append(row)
    else:
        lines.append("No Python files found.")

    lines.append("")
    lines.append("Summary")
    lines.append("  Files scanned:  {}".format(len(stats)))
    lines.append("  Lines of code:  {}".format(sum(s.loc for s in stats)))
    lines.append("  Functions:      {}".format(sum(s.functions for s in stats)))
    lines.append("  Classes:        {}".format(sum(s.classes for s in stats)))
    if inaccessible_dirs:
        # R7: tell the user the totals above are missing some folders.
        lines.append(
            "  Incomplete:     {} folder(s) could not be accessed "
            "(see warnings)".format(inaccessible_dirs)
        )
    return "\n".join(lines)
