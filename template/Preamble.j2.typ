// Import the rendercv function and all the refactored components
#import "@preview/rendercv:0.3.0": *

// Apply the rendercv template with custom configuration
#show: rendercv.with(
  name: "{{ cv._plain_name }}",
  title: "{{ settings.pdf_title }}",
  footer: {{ cv._footer }},
  top-note: [ {{ cv._top_note }} ],
  locale-catalog-language: "{{ locale.language_iso_639_1 }}",
  text-direction: {% if locale.is_rtl %}rtl{% else %}ltr{% endif %},
  page-size: "{{ design.page.size }}",
  page-top-margin: {{ design.page.top_margin }},
  page-bottom-margin: {{ design.page.bottom_margin }},
  page-left-margin: {{ design.page.left_margin }},
  page-right-margin: {{ design.page.right_margin }},
  page-show-footer: {{ design.page.show_footer|lower }},
  page-show-top-note: {{ design.page.show_top_note|lower }},
  colors-body: {{ design.colors.body.as_rgb() }},
  colors-name: {{ design.colors.name.as_rgb() }},
  colors-headline: {{ design.colors.headline.as_rgb() }},
  colors-connections: {{ design.colors.connections.as_rgb() }},
  colors-section-titles: {{ design.colors.section_titles.as_rgb() }},
  colors-links: {{ design.colors.links.as_rgb() }},
  colors-footer: {{ design.colors.footer.as_rgb() }},
  colors-top-note: {{ design.colors.top_note.as_rgb() }},
  typography-line-spacing: {{ design.typography.line_spacing }},
  typography-alignment: "{{ design.typography.alignment }}",
  typography-date-and-location-column-alignment: {{ design.typography.date_and_location_column_alignment }},
  typography-font-family-body: "{{ design.typography.font_family.body }}",
  typography-font-family-name: "{{ design.typography.font_family.name }}",
  typography-font-family-headline: "{{ design.typography.font_family.headline }}",
  typography-font-family-connections: "{{ design.typography.font_family.connections }}",
  typography-font-family-section-titles: "{{ design.typography.font_family.section_titles }}",
  typography-font-size-body: {{ design.typography.font_size.body }},
  typography-font-size-name: {{ design.typography.font_size.name }},
  typography-font-size-headline: {{ design.typography.font_size.headline }},
  typography-font-size-connections: {{ design.typography.font_size.connections }},
  typography-font-size-section-titles: {{ design.typography.font_size.section_titles }},
  typography-small-caps-name: {{ design.typography.small_caps.name|lower }},
  typography-small-caps-headline: {{ design.typography.small_caps.headline|lower }},
  typography-small-caps-connections: {{ design.typography.small_caps.connections|lower }},
  typography-small-caps-section-titles: {{ design.typography.small_caps.section_titles|lower }},
  typography-bold-name: {{ design.typography.bold.name|lower }},
  typography-bold-headline: {{ design.typography.bold.headline|lower }},
  typography-bold-connections: {{ design.typography.bold.connections|lower }},
  typography-bold-section-titles: {{ design.typography.bold.section_titles|lower }},
  links-underline: {{ design.links.underline|lower }},
  links-show-external-link-icon: {{ design.links.show_external_link_icon|lower }},
  header-alignment: {{ design.header.alignment }},
  header-photo-width: {{ design.header.photo_width }},
  header-space-below-name: {{ design.header.space_below_name }},
  header-space-below-headline: {{ design.header.space_below_headline }},
  header-space-below-connections: {{ design.header.space_below_connections }},
  header-connections-hyperlink: {{ design.header.connections.hyperlink|lower }},
  header-connections-show-icons: {{ design.header.connections.show_icons|lower }},
  header-connections-display-urls-instead-of-usernames: {{ design.header.connections.display_urls_instead_of_usernames|lower }},
  header-connections-separator: "{{ design.header.connections.separator }}",
  header-connections-space-between-connections: {{ design.header.connections.space_between_connections }},
  section-titles-type: "{{ design.section_titles.type }}",
  section-titles-line-thickness: {{ design.section_titles.line_thickness }},
  section-titles-space-above: {{ design.section_titles.space_above }},
  section-titles-space-below: {{ design.section_titles.space_below }},
  sections-allow-page-break: {{ design.sections.allow_page_break|lower }},
  sections-space-between-text-based-entries: {{ design.sections.space_between_text_based_entries }},
  sections-space-between-regular-entries: {{ design.sections.space_between_regular_entries }},
  entries-date-and-location-width: {{ design.entries.date_and_location_width }},
  entries-side-space: {{ design.entries.side_space }},
  entries-space-between-columns: {{ design.entries.space_between_columns }},
  entries-allow-page-break: {{ design.entries.allow_page_break|lower }},
  entries-short-second-row: {{ design.entries.short_second_row|lower }},
  entries-degree-width: {{ design.entries.degree_width }},
  entries-summary-space-left: {{ design.entries.summary.space_left }},
  entries-summary-space-above: {{ design.entries.summary.space_above }},
  entries-highlights-bullet: {% if design.entries.highlights.bullet == "●" %} text(13pt, [•], baseline: -0.6pt) {% else %} "{{ design.entries.highlights.bullet }}" {% endif %},
  entries-highlights-nested-bullet: {% if design.entries.highlights.nested_bullet == "●" %} text(13pt, [•], baseline: -0.6pt) {% else %} "{{ design.entries.highlights.nested_bullet }}" {% endif %},
  entries-highlights-space-left: {{ design.entries.highlights.space_left }},
  entries-highlights-space-above: {{ design.entries.highlights.space_above }},
  entries-highlights-space-between-items: {{ design.entries.highlights.space_between_items }},
  entries-highlights-space-between-bullet-and-text: {{ design.entries.highlights.space_between_bullet_and_text }},
  date: datetime(
    year: {{ settings._resolved_current_date.year }},
    month: {{ settings._resolved_current_date.month }},
    day: {{ settings._resolved_current_date.day }},
  ),
)

// Custom entry layout that spans the full text width, for entries that have
// no date/location column (e.g. Projects) so they don't reserve blank space
// on the right the way the built-in two-column `regular-entry` does.
#let full-width-entry(main-column, main-column-second-row: none) = {
  metadata("skip-content-area")

  context {
    let config = rendercv-config.get()
    let entries-highlights-bullet = config.at("entries-highlights-bullet")
    let entries-highlights-nested-bullet = config.at("entries-highlights-nested-bullet")
    let entries-highlights-space-between-items = config.at(
      "entries-highlights-space-between-items",
    )
    let entries-highlights-space-between-bullet-and-text = config.at(
      "entries-highlights-space-between-bullet-and-text",
    )
    let entries-highlights-space-above = config.at("entries-highlights-space-above")
    let typography-line-spacing = config.at("typography-line-spacing")
    let entries-allow-page-break = config.at("entries-allow-page-break")
    let sections-space-between-regular-entries = config.at("sections-space-between-regular-entries")
    let entries-side-space = config.at("entries-side-space")
    let justify = config.at("justify")
    let entries-highlights-space-left = config.at("entries-highlights-space-left")
    let start-align = config.at("start-align")

    set list(
      marker: (entries-highlights-bullet, entries-highlights-nested-bullet),
      indent: entries-highlights-space-left,
      spacing: entries-highlights-space-between-items + typography-line-spacing,
      body-indent: entries-highlights-space-between-bullet-and-text,
    )
    let list-depth = state("full-width-entry-list-depth", 0)
    show list.item: i => {
      list-depth.update(d => d + 1)
      i
      list-depth.update(d => d - 1)
    }
    show list: l => {
      context if list-depth.get() == 1 {
        v(entries-highlights-space-above)
      }
      context if list-depth.get() == 2 {
        v(entries-highlights-space-between-items)
      }
      l
    }
    set par(
      spacing: typography-line-spacing,
      leading: typography-line-spacing,
      justify: justify,
    )
    block(
      {
        set align(start-align)
        main-column
        main-column-second-row
      },
      breakable: entries-allow-page-break,
      below: sections-space-between-regular-entries + typography-line-spacing,
      inset: (
        left: entries-side-space,
        right: entries-side-space,
      ),
      width: 100%,
    )
  }
}
