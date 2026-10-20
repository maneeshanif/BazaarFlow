# Tokens (measured from computed styles)

## Colour

| Role | Value | Where |
| --- | --- | --- |
| Lime (primary brand, hero ground) | `rgb(182,254,0)` `#B6FE00` | Hero, CTA band, footer text, filter active, round icon buttons (18 elements) |
| Lime, deeper | `rgb(167,239,0)` `#A7EF00` | Filter list text |
| Forest (body ground) | `rgb(3,65,2)` `#034102` | `body`, footer |
| Forest, darker | `rgb(11,47,7)` `#0B2F07` | News sections behind cards |
| Ink green (text on light/lime) | `rgb(1,57,0)` `#013900` | Nav links, headings on lime |
| Ink green, body | `rgb(13,71,12)` `#0D470C` | Most text (142 elements) |
| Ink green, muted | `rgb(26,82,17)` `#1A5211` | Secondary text |
| Cream (card) | `rgb(253,251,232)` `#FDFBE8` | News cards, highlight panel |
| Off-white | `rgb(244,243,239)` `#F4F3EF` | "Pull me" ribbon |
| Kraft brown text | about `#7A4A0C` (read from screenshot) | Home statement block on cardboard texture |
| Arc stripes (intro and page transition) | coral `#FF7B5F`, orange `#FA8005`, yellow `#F7D000`, lime `#B6FE00`, sky `#50CBFF`, indigo `#2E3EAC` | Rainbow arcs sweeping in on every route change |

Product-colour system: each tape owns one colour pair (stationery red/peach, OPP lime/yellow, cloth indigo/lilac, masking orange/yellow, double-sided sky/blue). Sections change background to the product colour as you scroll.

Texture: crumpled-paper overlay on lime and forest grounds, kraft-card texture on the statement block.

## Type

| Role | Family | Size and weight | Notes |
| --- | --- | --- | --- |
| Display and UI labels | `futura-pt-condensed` (Adobe Fonts) | Uppercase, very large, heavy; 491 elements use it | Headings are split into per-letter spans and tilted/jittered |
| Body and card titles | `Inter Tight Variable` | 16px base; card titles bold at about 24px | News card titles use sentence case |
| Handwritten accent | `Nothing You Could Do` | Sticky-note text only | 50 elements |

Heading text is rendered twice (visible plus an aria copy) and split per letter for animation. Keep a single accessible text node when we rebuild.

## Radii

| Value | Used for |
| --- | --- |
| `50%` | Round icon buttons, tape rolls, social circles |
| `26.7px` | Small tags and chips |
| `42.7px` | News cards, highlight panel, photo frames |
| `106.7px` | Large stadium/pill rows on About |
| `999px` | Skip link, nav pills |

## Components

- **Tag chip**: small rounded rectangle, three-dot grip glyph on the left, condensed uppercase label ("HIGHLIGHT", "NEWS"). On lime: dark green fill with lime text. On cream: tan fill `#DED7B5` with green text.
- **Round arrow button**: 32px lime circle, dark arrow pointing up-right; sits bottom-right of cards.
- **Dotted rule**: dotted lines under card headings and under footer nav labels, like ruled notepaper.
- **Tape strips**: translucent kraft tape pieces stuck across photo corners.
- **Pull ribbon**: off-white paper ribbon fixed top-right with dotted top edge and the label "PULL ME".
- **Audio pill**: fixed bottom-right toggle (white pill, knob, speaker icon).
- **Sound/accessibility**: a "Skip to content" link is the first focus stop (forest fill, lime text, pill).

## Spacing and frame

- Page gutter about 22px at 1536px. Cards nearly touch the edges.
- Section vertical padding is large, about 100 to 200px.
- Curved section joins: every colour change is an elliptical arc, not a straight edge.

## Motion

- Route change: stacked coloured arcs sweep across (the screenshots caught it mid-play on each page).
- Headings: letters rise and settle with a stagger.
- Scroll: photos in tilted rounded frames drift in; pinned sections change colour per product.
- Cards on `/news` fade up as they enter.
