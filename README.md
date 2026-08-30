# Curriculum Vitae (CV) - Joe Hitchen

This project holds the contents of my CV in `.yaml` files and generates PDFs of the content using [RenderCV](https://github.com/rendercv/rendercv), which leverages Typst under the hood.

## Rendering the PDF

There are two ways to render the CV to PDF.
```
rendercv render <content-file.yaml> --settings cv-settings.yaml
render.bat [content-file.yaml]
```
In the first command, the contents file is a required input, but for the second command it is optional and defaults to `cv-content.yaml`.
The second command also needs a virtual environment called `venv-CV` to be present and have the requirements installed.
Both commands produce a PDF at `output\Joe_Hitchen_CV.pdf`.

## Column Layout & Balancing

To allow more content to be displayed in the Skills & Publications sections, without taking up excessive page length, a custom template was introduced which allows content to be rendered to two columns.

This lives in `template/` and is a local override of the built-in `engineeringclassic` theme's Typst templates, exposed under the custom name `template`.
Be aware that naming is important – `design.theme` in `cv-design.yaml` must match this folder name exactly, and `template/__init__.py` reuses `engineeringclassic`'s full design schema.

The columns look best when they are as similar in length as possible, and with the left-hand column being the longer if perfect balance is not possible.
This tuning process is not automatic and the column heights are hard-coded for the current content – Adding, removing, or editing a skill or publication will likely unbalance it again.
The current values live in `template/SectionBeginning.j2.typ` under the `// rendercv-balance:` keys and a Claude skill has been provided to adjust the column sizing to get the best results.
The skill has been authorised to re-order content if just changing the column heights is not sufficient, but should always explicitly flag this.

## Known Failures Modes

- **Pre-3.12 Python** silently installs RenderCV 2.3 instead of 2.8, which drops unrecognised fields with no error.
- **A theme override folder name that doesn't match `design.theme`** is silently ignored -- the CV renders with the stock theme instead of the custom two-column layout, no warning.
- **`template/__init__.py`** imports `rendercv.schema.models.design.classic_theme.ClassicTheme`, an internal (non-public) RenderCV module. A future RenderCV upgrade could move it and silently break the custom theme.
