#!/usr/bin/env python3
"""
balance_columns.py

Renders a RenderCV YAML CV and iteratively tunes the height of one or more
"#block(height: Xcm)[#columns(2, ...)[ ... ]]" wrappers in a theme's
SectionBeginning.j2.typ template, so that each wrapped section splits into
two visually-even columns -- with the LEFT column kept the longer (or equal)
one whenever a perfectly even split isn't possible.

How it works
------------
Typst's `columns()` fills the first column top-to-bottom before spilling
into the second, so the only lever available from outside Typst is the
block's height: a taller block keeps more content in column 1, a shorter
one forces more of it into column 2. The relationship between "block
height" and "how much ends up in column 1 vs column 2" is a monotonic
step function (content moves in whole-entry/whole-line jumps), so this
script finds the best height with a bounded binary search:

  1. Render the CV.
  2. Measure the actual rendered height of column 1 and column 2 for the
     target section (by locating its heading and the next section's
     heading in the PDF, then looking at the vertical extent of text left
     and right of the page's horizontal midline in between).
  3. If column 2 is empty, or column 1 is noticeably longer than column 2,
     the block is too tall -- shrink it.
     If column 2 is longer than column 1, the block is too short (violates
     the "left column is the longer one" rule) -- grow it.
  4. Repeat, narrowing the search range, until both columns are within
     `--tolerance-cm` of each other (with column 1 >= column 2), or
     `--max-iterations` is reached.

This only works for sections that already use the block+columns wrapper,
gated on `entry_type`, with a marker comment identifying which entry type
each height belongs to:

    {% if entry_type == "OneLineEntry" %}
    // rendercv-balance:OneLineEntry
    #block(height: 2.4cm)[#columns(2, gutter: 1.5em)[
    {% endif %}

If your theme's SectionBeginning.j2.typ doesn't have this yet for a given
entry type, add it (and the matching `]]` + `{% endif %}` close in
SectionEnding.j2.typ) before running this script -- see the skill's
SKILL.md for the exact snippet.

Optional second lever: reordering entries
------------------------------------------
Height alone can only choose *where in the existing entry order* the split
falls -- it can't change *which* entries end up on which side. Sometimes
the closest achievable split that way still has column 2 longer than
column 1 (violating the left-is-longer rule), even though some other
grouping of the same entries -- just in a different order -- would balance
much better. Pass `--reorder ENTRY_TYPE SECTION_KEY` (SECTION_KEY being the
YAML key of that section under `cv.sections`, e.g. `skills`) to allow this:
before tuning the height, the script measures each entry's own rendered
height in isolation (at the real column width), solves for the grouping of
entries into two columns that comes closest to even while keeping column 1
>= column 2, and rewrites the section's entry order in the YAML so that
grouping falls out of a plain height cut. This *changes the order entries
appear in the user's CV content*, which is a bigger deal than a template
tweak -- always show the user the before/after order and get their sign-off
before treating it as final.
"""

import argparse
import glob
import json
import re
import subprocess
import sys
from pathlib import Path

POINTS_PER_CM = 28.3465


def cm(points):
    return points / POINTS_PER_CM


def pt(cm_value):
    return cm_value * POINTS_PER_CM


def read_text(path):
    # newline="" disables Python's universal-newline translation, so a file
    # using CRLF line endings (as `rendercv new` and most Windows editors
    # produce) round-trips exactly instead of silently becoming LF -- which
    # would otherwise make every line in the file look changed in a diff.
    # (Path.read_text() has no newline= parameter, unlike write_text(), so
    # this goes through plain open() instead.)
    with open(path, "r", newline="") as f:
        return f.read()


def write_text(path, text):
    with open(path, "w", newline="") as f:
        f.write(text)


def read_height(template_text, entry_type):
    pattern = re.compile(
        r"(// rendercv-balance:" + re.escape(entry_type) + r"\s*\n\s*#block\(height:\s*)"
        r"([\d.]+)"
        r"(cm\)\[#columns)"
    )
    match = pattern.search(template_text)
    if not match:
        return None
    return float(match.group(2))


def write_height(template_text, entry_type, new_height_cm):
    pattern = re.compile(
        r"(// rendercv-balance:" + re.escape(entry_type) + r"\s*\n\s*#block\(height:\s*)"
        r"([\d.]+)"
        r"(cm\)\[#columns)"
    )
    replacement = r"\g<1>" + f"{new_height_cm:.2f}" + r"\g<3>"
    new_text, count = pattern.subn(replacement, template_text)
    if count != 1:
        raise ValueError(
            f"Expected exactly one '// rendercv-balance:{entry_type}' marker, found {count}."
        )
    return new_text


def run_rendercv(rendercv_cmd, yaml_path, locale, design, settings, output_dir):
    cmd = [rendercv_cmd, "render", str(yaml_path)]
    if locale:
        cmd += ["--locale-catalog", str(locale)]
    if design:
        cmd += ["--design", str(design)]
    if settings:
        cmd += ["--settings", str(settings)]
    cmd += ["-o", str(output_dir)]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"rendercv render failed (exit {result.returncode}):\n{result.stdout}\n{result.stderr}"
        )
    pdfs = glob.glob(str(Path(output_dir) / "*.pdf"))
    if not pdfs:
        raise RuntimeError(f"No PDF produced in {output_dir}")
    return pdfs[0]


def measure_columns(pdf_path, heading_text, next_heading_text):
    import pymupdf

    doc = pymupdf.open(pdf_path)

    heading_loc = None  # (page_index, bottom_y)
    next_heading_loc = None  # (page_index, top_y)
    page_width = None

    for page_index in range(len(doc)):
        page = doc[page_index]
        if page_width is None:
            page_width = page.rect.width
        text_dict = page.get_text("dict")
        for block in text_dict.get("blocks", []):
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    text = span["text"].strip()
                    if not text:
                        continue
                    if heading_loc is None and text == heading_text:
                        heading_loc = (page_index, span["bbox"][3])
                    elif (
                        heading_loc is not None
                        and next_heading_text
                        and next_heading_loc is None
                        and text == next_heading_text
                    ):
                        next_heading_loc = (page_index, span["bbox"][1])

    if heading_loc is None:
        raise RuntimeError(f"Could not find heading '{heading_text}' in {pdf_path}")

    start_page, top_y = heading_loc
    if next_heading_loc is not None:
        end_page, bottom_y = next_heading_loc
    else:
        end_page, bottom_y = start_page, None  # to end of content

    if end_page != start_page:
        # Section wraps across a page break -- bail out with a clear signal
        # rather than guessing.
        return {
            "warning": (
                f"Section starting with '{heading_text}' appears to continue past a "
                "page break; automatic balancing isn't reliable here."
            ),
            "col1_height_cm": None,
            "col2_height_cm": None,
        }

    page = doc[start_page]
    midline = page_width / 2

    text_dict = page.get_text("dict")
    candidates = []  # (y0, y1, x0)
    for block in text_dict.get("blocks", []):
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                text = span["text"].strip()
                if not text:
                    continue
                y0, y1 = span["bbox"][1], span["bbox"][3]
                if y0 < top_y:
                    continue
                if bottom_y is not None and y0 >= bottom_y:
                    continue
                if text == heading_text or text == next_heading_text:
                    continue
                candidates.append((y0, y1, span["bbox"][0]))

    if bottom_y is None and candidates:
        # No next heading to bound this section -- it's the last thing on
        # the page, which means a page footer sits somewhere below it.
        # Normal line-to-line and entry-to-entry gaps within a resume
        # section are small (well under half a line height's worth of
        # points); a footer sits much further down. Cut the section off at
        # the first gap that's clearly bigger than ordinary line spacing,
        # rather than trying to infer a "typical" gap from very few samples
        # (fragile with only 2-3 lines).
        FOOTER_GAP_THRESHOLD_PT = 30
        candidates.sort(key=lambda c: c[0])
        line_tops = sorted({round(c[0], 1) for c in candidates})
        cutoff = None
        for i in range(len(line_tops) - 1):
            gap = line_tops[i + 1] - line_tops[i]
            if gap > FOOTER_GAP_THRESHOLD_PT:
                cutoff = line_tops[i]
                break
        if cutoff is not None:
            candidates = [c for c in candidates if c[0] <= cutoff]

    col1_bottom = top_y
    col2_bottom = top_y
    for y0, y1, x0 in candidates:
        if x0 < midline:
            col1_bottom = max(col1_bottom, y1)
        else:
            col2_bottom = max(col2_bottom, y1)

    return {
        "warning": None,
        "col1_height_cm": round(cm(col1_bottom - top_y), 3),
        "col2_height_cm": round(cm(col2_bottom - top_y), 3),
    }


def find_section_block(text, section_key):
    """Locate a `section_key:` list under `cv.sections:` in the raw YAML
    text and return (before, after, items_text, item_indent) so the list's
    entries can be read and spliced back without touching anything else in
    the file -- no YAML parser involved, so nothing outside this one list
    ever gets reformatted."""
    lines = text.splitlines(keepends=True)
    key_pattern = re.compile(r"^([ \t]*)" + re.escape(section_key) + r":[ \t]*\r?\n?$")

    key_line_idx = key_indent = None
    for i, line in enumerate(lines):
        m = key_pattern.match(line)
        if m:
            key_line_idx, key_indent = i, len(m.group(1))
            break
    if key_line_idx is None:
        raise ValueError(f"Could not find a '{section_key}:' key in the YAML file.")

    j = key_line_idx + 1
    while j < len(lines) and lines[j].strip() == "":
        j += 1
    if j >= len(lines):
        raise ValueError(f"'{section_key}:' has no entries after it.")
    item_match = re.match(r"^([ \t]*)-\s", lines[j])
    if not item_match or len(item_match.group(1)) <= key_indent:
        raise ValueError(f"'{section_key}:' doesn't look like a YAML list of entries.")
    item_indent = len(item_match.group(1))

    end = j
    while end < len(lines):
        line = lines[end]
        if line.strip() != "":
            indent = len(line) - len(line.lstrip(" \t"))
            if indent <= key_indent:
                break
        end += 1

    before = "".join(lines[: j])
    items_text = "".join(lines[j:end])
    after = "".join(lines[end:])
    return before, after, items_text, item_indent


def split_entries(items_text, item_indent):
    """Split a list block's raw text into one chunk per entry, each chunk
    keeping that entry's exact original formatting (quoting, wrapping,
    inline comments, everything)."""
    prefix = " " * item_indent + "-"
    lines = items_text.splitlines(keepends=True)
    entries, current = [], []
    for line in lines:
        if line.startswith(prefix) and current:
            entries.append("".join(current))
            current = [line]
        else:
            current.append(line)
    if current:
        entries.append("".join(current))
    return entries


def entry_label(entry_text, entry_type):
    text = entry_text.strip()
    if entry_type == "OneLineEntry":
        m = re.search(r'label:\s*"?([^"\n]+)"?', text)
        return m.group(1).strip() if m else text.splitlines()[0][:60]
    if entry_type == "BulletEntry":
        m = re.search(r'bullet:\s*"(.+)"?\s*$', text, re.DOTALL)
        content = m.group(1) if m else text
        content = content.strip().rstrip('"')
        return (content[:60] + "...") if len(content) > 60 else content
    for key in ("name", "company", "institution"):
        m = re.search(rf'{key}:\s*"?([^"\n]+)"?', text)
        if m:
            return m.group(1).strip()
    return text.splitlines()[0][:60] if text else "(untitled entry)"


def measure_entry_heights(
    yaml_path,
    section_key,
    entry_type,
    heading,
    next_heading,
    template_path,
    locale,
    design,
    settings,
    output_dir,
    rendercv_cmd,
    probe_height_cm=8.0,
):
    """Render each entry of a section on its own (at the real column width)
    to measure its true rendered height, isolated from the others."""
    original_yaml_text = read_text(yaml_path)
    before, after, items_text, item_indent = find_section_block(original_yaml_text, section_key)
    entries = split_entries(items_text, item_indent)
    n = len(entries)

    original_template_text = read_text(template_path)
    write_text(template_path, write_height(original_template_text, entry_type, probe_height_cm))

    heights = []
    try:
        for i in range(n):
            write_text(yaml_path, before + entries[i] + after)

            pdf_path = run_rendercv(rendercv_cmd, yaml_path, locale, design, settings, output_dir)
            measurement = measure_columns(pdf_path, heading, next_heading)
            if measurement["warning"] or measurement["col1_height_cm"] is None:
                raise RuntimeError(
                    f"Could not measure entry {i} ('{entry_label(entries[i], entry_type)}') "
                    f"of section '{section_key}': {measurement.get('warning')}"
                )
            heights.append(measurement["col1_height_cm"])
    finally:
        write_text(yaml_path, original_yaml_text)
        write_text(template_path, original_template_text)

    return heights, entries


def solve_partition(heights):
    """Choose which entries (by index) go in column 1 vs column 2 so the
    two groups' total heights are as close as possible, subject to
    column 1's total being >= column 2's. Returns (col1_indices, col2_indices),
    both sorted to preserve each group's original relative order."""
    n = len(heights)
    scaled = [max(1, round(h * 100)) for h in heights]  # hundredths of a cm
    total = sum(scaled)
    target = total / 2

    achievable = {0: ()}
    for idx, val in enumerate(scaled):
        for s, subset in list(achievable.items()):
            new_sum = s + val
            if new_sum not in achievable:
                achievable[new_sum] = subset + (idx,)

    best_sum, best_subset = None, None
    for s, subset in achievable.items():
        if s >= target and (best_sum is None or s < best_sum):
            best_sum, best_subset = s, subset

    if best_subset is None:
        best_subset = tuple(range(n))  # shouldn't happen; total always qualifies

    col1_indices = sorted(best_subset)
    col2_indices = sorted(i for i in range(n) if i not in best_subset)
    return col1_indices, col2_indices


def reorder_section_entries(yaml_path, section_key, col1_indices, col2_indices, entries):
    """Splice the section's entry chunks back in the new order. Everything
    in the file outside this one list -- including every other entry's own
    exact formatting -- is left completely untouched."""
    text = read_text(yaml_path)
    before, after, _items_text, _item_indent = find_section_block(text, section_key)
    new_items_text = "".join(entries[i] for i in col1_indices) + "".join(entries[i] for i in col2_indices)
    write_text(yaml_path, before + new_items_text + after)


def reorder_for_balance(
    entry_type,
    section_key,
    heading,
    next_heading,
    template_path,
    yaml_path,
    locale,
    design,
    settings,
    output_dir,
    rendercv_cmd,
):
    heights, entries = measure_entry_heights(
        yaml_path, section_key, entry_type, heading, next_heading,
        template_path, locale, design, settings, output_dir, rendercv_cmd,
    )
    col1_indices, col2_indices = solve_partition(heights)

    before_order = [entry_label(e, entry_type) for e in entries]
    after_order = (
        [entry_label(entries[i], entry_type) for i in col1_indices]
        + [entry_label(entries[i], entry_type) for i in col2_indices]
    )
    changed = before_order != after_order

    reorder_section_entries(yaml_path, section_key, col1_indices, col2_indices, entries)

    return {
        "section_key": section_key,
        "changed_order": changed,
        "entries_before": before_order,
        "entries_after": after_order,
        "left_column_entries": after_order[: len(col1_indices)],
        "right_column_entries": after_order[len(col1_indices):],
        "entry_heights_cm": {entry_label(e, entry_type): h for e, h in zip(entries, heights)},
    }


def balance_section(
    entry_type,
    heading,
    next_heading,
    template_path,
    yaml_path,
    locale,
    design,
    settings,
    output_dir,
    rendercv_cmd,
    tolerance_cm,
    max_iterations,
    min_height_cm,
    max_height_cm,
):
    template_text = read_text(template_path)
    current_height = read_height(template_text, entry_type)
    if current_height is None:
        return {
            "entry_type": entry_type,
            "heading": heading,
            "balanced": False,
            "error": (
                f"No '// rendercv-balance:{entry_type}' marker found in {template_path}. "
                "Add the block+columns wrapper with that marker first (see SKILL.md)."
            ),
        }

    lo, hi = min_height_cm, max(current_height, min_height_cm * 2)
    best = None
    history = []

    for iteration in range(max_iterations):
        candidate = round((lo + hi) / 2, 2)
        template_text = write_height(read_text(template_path), entry_type, candidate)
        write_text(template_path, template_text)

        pdf_path = run_rendercv(rendercv_cmd, yaml_path, locale, design, settings, output_dir)
        measurement = measure_columns(pdf_path, heading, next_heading)
        history.append({"height_cm": candidate, **measurement})

        if measurement["warning"]:
            # Can't measure reliably (e.g. page break) -- stop and report.
            break

        col1 = measurement["col1_height_cm"]
        col2 = measurement["col2_height_cm"]
        diff = col1 - col2

        if col2 == 0:
            # Everything still in column 1 -- shrink to force some spillover,
            # but this is a *valid* (if wasteful) state, so record it.
            if best is None or diff < best["diff"]:
                best = {"height_cm": candidate, "col1": col1, "col2": col2, "diff": diff}
            hi = candidate
        elif diff < 0:
            # Column 2 longer than column 1 -- violates the "left is longer"
            # rule. Grow the block.
            lo = candidate
            if hi - lo < 0.05 and hi < max_height_cm:
                # The search range was seeded from the file's existing
                # height (or has narrowed to one), and even the ceiling
                # doesn't produce a valid split -- push the ceiling out
                # instead of converging on a range that can't contain the
                # answer.
                hi = min(hi * 1.5, max_height_cm)
        else:
            # Valid split (col1 >= col2). Keep it as the best-so-far if it's
            # the closest to even, then try shrinking further to see if an
            # even tighter valid split exists.
            if best is None or diff < best["diff"]:
                best = {"height_cm": candidate, "col1": col1, "col2": col2, "diff": diff}
            hi = candidate

        if abs(diff) <= tolerance_cm and col2 > 0:
            break
        if hi - lo < 0.05:
            break

    if best is None:
        # Never found a single valid (col1 >= col2) split -- likely a
        # single entry, or two entries so unevenly sized that no split
        # balances them. Fall back to the largest height tried (safest:
        # keeps everything in column 1, i.e. effectively single-column).
        template_text = write_height(read_text(template_path), entry_type, hi)
        write_text(template_path, template_text)
        run_rendercv(rendercv_cmd, yaml_path, locale, design, settings, output_dir)
        return {
            "entry_type": entry_type,
            "heading": heading,
            "balanced": False,
            "final_height_cm": hi,
            "note": (
                "Could not find a two-column split where the left column is the "
                "longer one -- this section may have too few entries to split "
                "sensibly, or one entry is much longer than the rest. Left as a "
                "single filled column."
            ),
            "history": history,
        }

    # Re-render at the best height so the files on disk match the report.
    template_text = write_height(read_text(template_path), entry_type, best["height_cm"])
    write_text(template_path, template_text)
    run_rendercv(rendercv_cmd, yaml_path, locale, design, settings, output_dir)

    return {
        "entry_type": entry_type,
        "heading": heading,
        "balanced": abs(best["diff"]) <= tolerance_cm and best["col2"] > 0,
        "final_height_cm": best["height_cm"],
        "col1_height_cm": best["col1"],
        "col2_height_cm": best["col2"],
        "history": history,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--yaml", required=True, help="Path to the main RenderCV content YAML file")
    parser.add_argument("--locale", help="Path to the locale YAML file (optional)")
    parser.add_argument("--design", help="Path to the design YAML file (optional)")
    parser.add_argument("--rendercv-settings", dest="settings", help="Path to the rendercv_settings YAML file (optional)")
    parser.add_argument("--template", required=True, help="Path to SectionBeginning.j2.typ")
    parser.add_argument(
        "--section",
        nargs=2,
        action="append",
        metavar=("ENTRY_TYPE", "HEADING"),
        required=True,
        help="An entry type + its rendered section heading, e.g. --section OneLineEntry Skills. Repeatable.",
    )
    parser.add_argument(
        "--next-heading",
        nargs=2,
        action="append",
        metavar=("HEADING", "NEXT_HEADING"),
        default=[],
        help="Map a section heading to the heading that immediately follows it in the rendered CV, "
        "so the script knows where the section's content ends. Omit for a section that's last on its page.",
    )
    parser.add_argument("--output-dir", required=True, help="Output folder passed to `rendercv render -o`")
    parser.add_argument("--rendercv-cmd", default="rendercv", help="The rendercv executable to use (default: rendercv)")
    parser.add_argument("--tolerance-cm", type=float, default=0.15)
    parser.add_argument("--max-iterations", type=int, default=8)
    parser.add_argument("--min-height-cm", type=float, default=0.3)
    parser.add_argument("--max-height-cm", type=float, default=20.0)
    parser.add_argument(
        "--reorder",
        nargs=2,
        action="append",
        metavar=("ENTRY_TYPE", "SECTION_KEY"),
        default=[],
        help="Allow reordering this section's entries (its YAML key under cv.sections, e.g. 'skills') to "
        "find a better left/right grouping before tuning the height. This rewrites the entry order in "
        "--yaml -- review entries_before/entries_after in the output before treating it as final. Repeatable.",
    )
    args = parser.parse_args()

    next_heading_map = dict(args.next_heading)
    reorder_map = dict(args.reorder)
    template_path = Path(args.template)
    yaml_path = Path(args.yaml)
    locale = Path(args.locale) if args.locale else None
    design = Path(args.design) if args.design else None
    settings = Path(args.settings) if args.settings else None

    results = []
    for entry_type, heading in args.section:
        next_heading = next_heading_map.get(heading)
        section_key = reorder_map.get(entry_type)

        reorder_report = None
        if section_key:
            reorder_report = reorder_for_balance(
                entry_type=entry_type,
                section_key=section_key,
                heading=heading,
                next_heading=next_heading,
                template_path=template_path,
                yaml_path=yaml_path,
                locale=locale,
                design=design,
                settings=settings,
                output_dir=args.output_dir,
                rendercv_cmd=args.rendercv_cmd,
            )

        result = balance_section(
            entry_type=entry_type,
            heading=heading,
            next_heading=next_heading,
            template_path=template_path,
            yaml_path=yaml_path,
            locale=locale,
            design=design,
            settings=settings,
            output_dir=args.output_dir,
            rendercv_cmd=args.rendercv_cmd,
            tolerance_cm=args.tolerance_cm,
            max_iterations=args.max_iterations,
            min_height_cm=args.min_height_cm,
            max_height_cm=args.max_height_cm,
        )
        if reorder_report:
            result["reorder"] = reorder_report
        results.append(result)

    print(json.dumps({"sections": results}, indent=2))


if __name__ == "__main__":
    main()
