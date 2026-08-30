from typing import Literal

from rendercv.schema.models.design.classic_theme import ClassicTheme


class TemplateTheme(ClassicTheme):
    theme: Literal["template"] = "template"
