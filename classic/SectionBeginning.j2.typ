== {{section_title}}
{% if entry_type in ["ReversedNumberedEntry"] %}

#reversed-numbered-entries(
  [
{% endif %}
{% if entry_type == "OneLineEntry" %}
// rendercv-balance:OneLineEntry
#block(height: 2.27cm)[#columns(2, gutter: 1.5em)[
{% endif %}
{% if entry_type == "BulletEntry" %}
// rendercv-balance:BulletEntry
#block(height: 0.68cm)[#columns(2, gutter: 1.5em)[
{% endif %}
