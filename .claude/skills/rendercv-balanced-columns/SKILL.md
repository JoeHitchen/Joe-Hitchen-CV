---
name: rendercv-balanced-columns
description: Render a RenderCV YAML-based CV/resume to PDF and, in the same pass, automatically balance any two-column sections (e.g. Skills or Publications side-by-side) by tuning the Typst column-block heights and, if that's not enough, reordering the section's entries for a better left/right grouping -- re-rendering until the columns are as even as possible, with the left column kept the longer one whenever an exact split isn't achievable. Use whenever the user asks to render, regenerate, rebuild, or refresh a RenderCV CV with (or that should have) a two-column section, or to "balance", "even out", "fix the spacing/fill on", "tighten up", or "re-check" its columns, or to reorder skills/publications/entries to improve a column layout, or to add a new two-column section to a theme. Skip this for RenderCV CVs with no two-column sections -- plain `rendercv render` covers those.
---

# RenderCV: render + auto-balance two-column sections

RenderCV (https://github.com/rendercv/rendercv) renders a YAML CV to PDF via
Typst. Its themes don't have a built-in "two columns" design option, but a
section can be made two-column by overriding two small Typst templates
(`SectionBeginning.j2.typ` / `SectionEnding.j2.typ`) to wrap that section's
entries in `#block(height: Xcm)[#columns(2, ...)[ ... ]]`.

The catch: Typst's `columns()` fills column 1 top-to-bottom before spilling
into column 2, so getting an evenly split, good-looking result depends
entirely on picking the right block height -- and the "right" height
changes whenever the content changes (a skill added, a publication removed,
a font tweak). This skill re-checks that balance every time the CV is
rendered and adjusts the height automatically, instead of leaving a magic
number in the template that quietly goes stale.

## Prerequisites

- Python 3.12+ with `rendercv[full]` installed (`pip install "rendercv[full]"`).
  RenderCV 2.4+ requires Python 3.12 -- on 3.11 you're capped at RenderCV 2.3,
  which silently drops some fields (e.g. `custom_connections`, `headline`)
  without warning. Check `rendercv --version` and `python3 --version` if
  something looks off.
- `pip install pymupdf` for `scripts/balance_columns.py` (it reads the
  rendered PDF back to measure column heights). No other Python packages
  are needed -- reordering (Step 4a) edits the YAML with plain text
  splicing, not a YAML library, specifically so it never reformats
  anything outside the one list it's touching.
- The first render on a machine needs internet access once, so Typst can
  download the theme's package dependencies (e.g. `fontawesome`) -- normal
  on any machine with ordinary internet access.

## Step 1: Find the CV's files

You need: the main content YAML, and optionally separate `locale`,
`design`, and `rendercv_settings` YAML files if the user's project splits
them out (RenderCV supports this via `--locale-catalog`, `--design`,
`--settings` flags -- check the CV folder for files like
`cv-content.yaml`, `cv-locale.yaml`, etc., alongside a single
combined YAML as the more common alternative). Also look for a theme
override folder next to the YAML (named after the theme, e.g. `classic/`)
-- that's where the two-column wrapper lives.

## Step 2: Make sure the target sections are wired up for two columns

Open `<theme>/SectionBeginning.j2.typ`. Each section wraps its entries
based on `entry_type` (the Jinja variable RenderCV passes in -- it reflects
which entry template the section's items use, e.g. `OneLineEntry` for
`label`/`details` skill entries, `BulletEntry` for plain `bullet` entries,
`NormalEntry`/`ExperienceEntry`/`EducationEntry` for the rest). Figure out
which entry type the section the user wants balanced actually uses by
looking at its YAML (or by checking `<theme>/entries/*.j2.typ` for the
matching field names).

If a two-column wrapper for that entry type isn't there yet, add it. Each
one needs a `// rendercv-balance:<EntryType>` marker comment immediately
above its `#block(height: ...)` line -- `scripts/balance_columns.py` uses
that marker to find and rewrite the right height, and to tell sections
apart when more than one is being balanced. Pick a reasonable starting
height (doesn't need to be right -- the script will correct it):

```
{% if entry_type == "OneLineEntry" %}
// rendercv-balance:OneLineEntry
#block(height: 2.5cm)[#columns(2, gutter: 1.5em)[
{% endif %}
```

And the matching close in `SectionEnding.j2.typ` (no marker needed here,
just gate it the same way):

```
{% if entry_type == "OneLineEntry" %}
]]
{% endif %}
```

Do this for each entry type the user wants two-column. Leave every other
`entry_type` alone -- untouched sections render exactly as the theme
normally would.

## Step 3: Work out each section's rendered heading and its neighbor

The script locates a section in the rendered PDF by its heading text (the
literal, rendered section title -- RenderCV titles a section from its YAML
key, e.g. `additional_experience` becomes "Additional Experience"), and
needs to know what heading comes right after it so it knows where the
section's content ends. Read the CV's `cv.sections` keys in the order they
appear in the YAML, convert each to its rendered title, and note which
heading immediately follows each section you're balancing. The very last
section in the CV has no "next heading" -- leave it unmapped; the script
handles a trailing section (and the page footer that sits below it) on its
own.

## Step 4: Run the balancer

```
python3 scripts/balance_columns.py \
  --yaml path/to/content.yaml \
  --locale path/to/locale.yaml \
  --template path/to/classic/SectionBeginning.j2.typ \
  --section OneLineEntry Skills \
  --section BulletEntry Publications \
  --next-heading Skills Publications \
  --output-dir path/to/rendercv_output \
  --rendercv-cmd rendercv
```

(Omit `--locale`/`--design`/`--rendercv-settings` if those aren't split out
into separate files. Add one `--section ENTRY_TYPE HEADING` per section
being balanced, and one `--next-heading HEADING NEXT_HEADING` for every
balanced section that has something after it on the page.)

This renders the CV, measures each targeted section's two columns from the
actual PDF, and repeatedly narrows in on the best block height for each --
shrinking it while column 2 is empty or column 1 is longer than necessary,
growing it if column 2 ever ends up longer than column 1 (which the left
column must never be shorter than). It leaves the template file and the
rendered output on disk in their final, best state, and prints a JSON
summary.

### Step 4a: When height alone can't get close enough -- reordering

Height tuning can only choose *where in the current entry order* to make
the cut. If the JSON comes back `balanced: false` with a `note` about not
finding a left-longer split, or the split it did find leaves one column
noticeably emptier than it needs to be, check whether some *other* grouping
of the same entries would balance better -- reordering can often find a
much tighter fit than the sequential cut ever could, because it isn't
restricted to a single contiguous split point.

Add `--reorder ENTRY_TYPE SECTION_KEY` for each section you want this tried
on, where `SECTION_KEY` is that section's key under `cv.sections` in the
YAML (e.g. `skills`, `publications`):

```
python3 scripts/balance_columns.py \
  ... \
  --section OneLineEntry Skills \
  --reorder OneLineEntry skills \
  ...
```

This measures each entry's own rendered height in isolation (at the real
column width -- not guessed from character counts), solves for the
grouping of entries into two columns that comes closest to even while
keeping column 1 >= column 2, rewrites the section's entry order in the
YAML to match that grouping, and then runs the normal height search on top
of the new order.

**This changes the order the user's actual skills/publications/etc. appear
in** -- a bigger deal than a template tweak, since they may have ordered
things by importance on purpose. The JSON's `reorder` block reports
`entries_before` and `entries_after` (and `changed_order`, which is `false`
when the original order was already optimal, so nothing to review). Always
show the user that before/after order and get their go-ahead before
treating it as final -- don't just silently ship a reordered CV. If they'd
rather keep their original order even at the cost of a wider gap between
columns, that's a completely reasonable answer; just fall back to Step 4's
plain height-only result.

## Step 5: Read the result and tell the user what happened

For each section, the JSON reports `balanced` (true if it landed within
tolerance with column 1 >= column 2), the final heights, and the height
history. A few things are worth surfacing to the user rather than staying
silent about:

- **`balanced: false` doesn't necessarily mean something's wrong.** Because
  content only moves between columns in whole-line jumps, sometimes the
  *closest* possible split (at the current entry order) has the right
  column very slightly longer -- which the "left column must be the longer
  one" rule then rejects in favor of a less-even but rule-compliant split.
  If that happens, say so, and mention reordering (Step 4a) as the more
  likely fix, rather than settling for the wider, rule-compliant-but-lopsided
  height-only result.
- **A section with only one entry, or one wildly longer than the rest,**
  can't be split sensibly -- the script falls back to a single filled
  column and says why in `note`. That's expected; it's not a bug to fix,
  and reordering won't help here either.
- **A "page break" warning** means the section's content spans two pages,
  which makes column measurement unreliable -- shorten the content or
  accept single-column there rather than trying to force a fix.

Show the user the final rendered PDF (or its page images) so they can see
the actual result, not just the JSON.

## Notes on the measurement approach

`scripts/balance_columns.py` measures real ink positions in the rendered
PDF (via PyMuPDF) rather than trusting the `height:` number literally --
Typst doesn't clip a `block`'s contents to its stated height, so a column
can visibly run past it. Measuring the actual rendered text is what makes
the balancing trustworthy regardless of that. If you ever need to debug a
measurement that looks wrong, dump the page's text spans (`page.get_text
("dict")`) and check where the script's assumptions (heading text match,
left/right split at the page's horizontal midline) might not hold for that
particular theme or layout.
