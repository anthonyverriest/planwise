<ui_ux_guidelines>
Based on Refactoring UI by Adam Wathan and Steve Schoger, and established UI/UX best practices.

<visual_hierarchy>
- Use size, weight, and color together to communicate importance — never rely on font size alone.
- Apply a three-tier text color system: dark (primary content), medium grey (secondary), light grey (tertiary).
- De-emphasize competing elements rather than over-emphasizing the focal element.
- Never use grey text on colored backgrounds; use same-hue color with adjusted saturation/lightness.
- Treat labels as a last resort; combine label and value into a single unit (e.g., "12 left in stock" not "Stock: 12").
- Baseline-align mixed font sizes, not center-align.
- Design in grayscale first to force correct hierarchy through spacing, contrast, and size before adding color.
</visual_hierarchy>

<layout_and_spacing>
- Use a non-linear spacing scale: 4, 8, 12, 16, 24, 32, 48, 64, 96, 128, 192, 256 (px). Never use arbitrary values.
- Start with too much white space, then reduce — you almost always need more than you think.
- Apply proximity grouping: more space between groups than within groups to show which elements belong together.
- Don't fill the screen; give elements only the space they need.
- Start designs at mobile width (~400px) and adapt upward.
- Responsive scaling is not proportional: large elements shrink faster than small elements across breakpoints.
- Use fixed widths when flexibility isn't needed; don't make everything fluid by default.
- Optimal line length: 45–75 characters per line (20–35em).
</layout_and_spacing>

<typography>
- Use a hand-picked font size scale: 12, 14, 16, 18, 20, 24, 30, 36, 48, 64 (px). Prefer hand-picked values over blind modular scales — mathematical ratios produce awkward middle values.
- Use px or rem units only; never use em for type scale (prevents compounding from nesting).
- Line-height is inversely proportional to font size: body 1.5–2.0, headlines 1.0–1.2.
- Never use font weights below 400 for UI work; use 400–500 for body, 600–700 for emphasis.
- Tighten letter-spacing for headlines; increase letter-spacing for ALL-CAPS text.
- Left-align text longer than 2–3 lines; never center long-form content.
- Right-align numbers in tables and data displays.
</typography>

<color>
- Use HSL for color reasoning (Hue 0–360, Saturation 0–100%, Lightness 0–100%).
- Build a structured palette: 8–10 grey shades, 5–10 shades per primary color, 5–10 shades per semantic color (danger, warning, success). 9 shades per color is the sweet spot.
- Use very dark grey instead of true black — pure black is visually harsh.
- As lightness moves away from 50%, increase saturation to prevent washed-out appearance.
- Rotate hue 20–30° toward nearest bright hue (yellow/cyan/magenta) for lighter/darker shades instead of only adjusting lightness.
- Add 5–15% saturation to greys for personality: blue-tinted = cool, yellow/orange-tinted = warm.
- Limit gradient hue spread to 30° max on the color wheel.
- Meet WCAG contrast minimums: 4.5:1 for normal text, 3:1 for large text (18px+ bold or 24px+).
</color>

<shadows_and_depth>
- Define a 5-level shadow elevation system from subtle (button lift) to prominent (modals).
- Use two shadows per element: large-blur primary (direct light) + tight-blur secondary (ambient light).
- Use element-hue-tinted shadow color, not pure black.
- Reduce shadow on press/click to simulate pushing down.
- Prefer box shadows over borders for separating elements — borders add visual clutter.
</shadows_and_depth>

<borders_and_separation>
- Avoid borders for element separation; prefer box shadows, background color differences, or extra spacing.
- Use accent borders on one edge (left or top) of cards/sections for visual flair without clutter.
</borders_and_separation>

<buttons_and_actions>
- Primary action: solid, high-contrast background.
- Secondary action: outline style or low-contrast background.
- Tertiary action: styled as a plain link.
- Destructive actions: use secondary/tertiary styling by default; only use bold red on confirmation dialogs where destruction IS the primary action.
</buttons_and_actions>

<border_radius>
- Pick one approach and apply everywhere: small = neutral, large = playful, none = serious/formal.
- Never mix square and rounded corners in the same interface.
</border_radius>

<images_and_icons>
- Control icon size with width/height, not font-size.
- Never scale icons beyond 3–4x their intended size; enclose small icons in a shaped container instead.
- Never scale down screenshots more than ~50%; show at smaller screen size or crop instead.
- Place user-uploaded images in fixed-size containers with object-fit: cover; use inset box-shadow instead of border.
- For text on images: add semi-transparent overlay, lower contrast/brightness 20–30%, or add text-shadow with large blur radius.
</images_and_icons>

<forms>
- Keep forms concise — only ask for essential information.
- Label fields and buttons with descriptive text; avoid generic "Submit".
- Apply visual hierarchy to form fields: prominent primary fields, de-emphasized optional fields.
</forms>

<search_and_navigation>
- Sync search queries, filters, pagination, and sort order to URL query parameters — enables sharing, bookmarking, and browser back/forward navigation.
- Debounce search input (200–300ms) to avoid excessive requests on every keystroke.
- Show inline results as the user types; avoid full-page reloads for search.
- Preserve scroll position on back navigation; restore previous state from URL params.
- Provide clear visual feedback for active filters and an easy way to clear them all.
- Use optimistic URL updates — push to history immediately, fetch data in the background.
</search_and_navigation>

<loading>
- Use skeleton screens (placeholder shapes mimicking content layout) instead of spinners or circular progress indicators — skeletons reduce perceived wait time and prevent layout shift.
- Match skeleton shapes to the actual content dimensions (text lines, avatars, cards) so the transition feels seamless.
- Animate skeletons with a subtle shimmer/pulse to indicate activity; avoid static grey blocks.
</loading>

<empty_states_and_polish>
- Design empty states as a priority, not an afterthought; include illustration, clear CTA, and hide unnecessary UI when there's no content.
- Replace bullet points with icons for lists that benefit from visual interest.
- Challenge default component conventions — reimagine dropdowns, tables, and radio buttons when a different form serves the UX better.
</empty_states_and_polish>

</ui_ux_guidelines>
