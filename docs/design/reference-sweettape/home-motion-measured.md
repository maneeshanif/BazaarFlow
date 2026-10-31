# SweetTape home page: opening, hero, cursor, menu and scroll sequence (measured 2026-10-31)

Recorded with the Playwright MCP server at 1440x810 against https://sweet-tape.com/. The page is 13,965 px tall and uses
Lenis smooth scrolling, GSAP-style scrubbed scenes and a custom cursor. Sections, in order (class names from the DOM):
`hero-section` (0-2565), `wave-band`, `tape-slider-parent` (2565-3548), `giant-pinning` (3400-12127), `make-it-stick`,
`site-footer`.

## 1. Opening (first visit, about 3 s)

1. Plain lime screen (#B6FE00).
2. Dark-green badge logo fades and scales in at the centre, slightly tilted, small (about 200 px wide). It holds.
3. The lime screen lifts off upward with a curved (elliptical) bottom edge. Behind it, bands follow in order: coral,
   orange, sunny yellow, lime, sky, indigo, each a little later than the last, each with its own curved edge. The
   rainbow sweeps off the top and the hero is underneath.
4. The hero text is already in place when the arcs clear. (The same arcs are reused for page changes.)

## 2. Hero

- Ground: crumpled lime paper texture. Scrollbar is a thin lime bar on forest.
- Top-left: two-line tagline in the condensed display face with a dotted vertical rule on its left.
- Top centre: a small row "WE'RE [logo badge] HERE TO" in the display face, about 32 px.
- Centre: two lines of very large hand-cut capitals ("STICK / BY YOU"), about 25 vw, forest green. Every letter has its own
  small rotation and vertical offset, so the word looks cut from paper.
- Bottom centre: a product (tape roll) rising from behind a forest-green curved seam. The seam is the top edge of the
  next section, an ellipse wider than the screen.
- Top-right: a cream paper tab with a dotted line across its top, the words "PULL ME" and a notched (swallow-tail) lower
  edge. It is the menu handle.
- Bottom-right: a small pill toggle for sound.
- Cursor: the system cursor is hidden. A cream arrow with a soft white outline, rotated about 7 degrees, follows the
  pointer with a short lag. Over links and buttons it becomes a pointing hand. It is a `div.cursor-arrow` moved by
  transform; `html` gets the class `has-cursor`.

## 3. Menu (the pull tab)

- Click the tab: a cream paper sheet drops down from the top-right, about 450 px wide, and the tab travels down with its
  lower edge, so the tab is the handle of the sheet. About 0.9 s.
- Four items (About, Our Family, News, Contact) in very large condensed capitals, each on a row with a dotted rule above
  it and a small lime circle with an arrow at the right. The letters of each item drop in one by one, staggered, with a
  small bounce.
- Hover on a row: the arrow circle grows. Click the tab again to retract.

## 4. Scroll sequence

1. **Forest board** (dark green crumpled paper, scrolls up from the hero seam). Loose objects are taped or clipped to it,
   each at its own angle: a yellow sticky note (a to-do list with three circles) with a binder clip, a kraft-paper card
   with a long block of brown condensed capitals, a clear tape strip hanging down, a lemon illustration card with a
   masking-tape strip, a gift box. They move at different speeds as the page scrolls (parallax), so the board
   appears to slide past the camera. The kraft card's text appears line by line; the last lines have their letters
   jumping up and down before they settle.
2. **Wave band**: a curved, wavy lime ribbon crosses the screen carrying huge capitals ("...GETS MESSY, SOMETHING HA...")
   and a small round product badge. The text slides sideways as the page scrolls, following the wave.
3. **Chapter on orange** ("THE CREATIVE"): giant outlined word behind a round product disc in the centre. A white round
   "EXPLORE" button with a dotted ring sits at the disc's upper right. To the left: three small tag chips (labelling,
   paint work, bundling) and two lines of description. To the right: a vertical stack of small discs (the other
   products) to switch to. Two tilted taped photos float either side. The background colour changes with the product.
4. **Why we exist** on lime: small dark chip "WHY WE EXIST", then a three-line centred statement.
5. **Giant pinned sequence** (about 8,700 px of scrolling): the screen stays still while a very long line of huge capitals
   ("TO CREATE", "TO FIX", "TO PROTECT") slides across horizontally as you scroll. Tilted taped photos, round
   product discs and handwritten notes with arrows sit between the words and drift up and down at different speeds. A
   small hand-drawn circled number (1), (2), (3) marks each word.
6. **Make it stick**: a tilted taped photo on the left and a big dark rounded panel with a three-line headline and one
   line of small text on the right.
7. **Footer**: dark green. Four nav labels spread across the top, each with a small lime dot underneath. A giant
   wordmark with the logo above it. Round product discs and lime circular social buttons lie piled in front of it, as
   if they had dropped in and landed.

## 5. What BazaarFlow takes and what it changes

Takes (structure and motion only): the opening, the paper hero with hand-cut capitals, the pull tab menu, the cursor, the
forest board with objects taped to it, the wavy ribbon, the product-disc slider, the pinned horizontal word sequence,
the closing panel and the pile footer.

Does not take: any image, the logo, the icons, the copy, the product names or the tape artwork. Every BazaarFlow image is
generated from `docs/design/asset-prompts.md`.

Changes for BazaarFlow (decided with the owner on 2026-10-31):

- Subject matter is a shop that sends out small orders: delivery parcels, small goods, packed food. Tape stays as a quiet
  detail (taped corners, tape strips that unroll as you scroll), not the subject.
- Tone is more serious: real, documentary-style photographs, fewer jokes, plain statements.
- The pull tab says "MENU" and holds the BazaarFlow links.

## 6. Round 2: small details, measured 2026-10-31 with Playwright (the owner asked for every small animation)

**Text is built from letters (and words) in clipping wrappers.** Every heading is `.clip > .char` (letters) and body copy is
`.body-clip > .body-rise` (words). On scroll they rise from `translate(0, 130%)` (letters) or `42%` (words) with a stagger,
the wrapper hiding what has not risen yet.

**Hover on a heading: the pointer's neighbours react.** Sampled on the hero title with the pointer over the "I": the letters
nearest it lifted by up to about 20 px (that is roughly 0.07 of the font size), tilted up to about 5 degrees *away* from the
pointer (letters on its left turn left, letters on its right turn right, the one under it stays upright) and grew by up to
7 percent. The effect fades with distance (about 4 letters each side) and everything settles within 300 ms of the pointer
leaving. Body-copy words carry the same hook with a smaller offset.

**Link hover: the label rolls.** Footer links (and similar) animate every letter with `footer-link-roll`: 0.45 s, 35 ms apart
from letter to letter; each letter slides up out of its clip (to -130%), re-enters from below (+130%) and settles.

**The logo sticker drops with squash and stretch** (`powers-mark-drop`): it falls about 96 px, lands (a 4 px overshoot), squashes
to 1.09 wide by 0.91 tall, springs back taller, and settles after two or three small bounces.

**The menu tab arrives from above** (`is-arriving`, `translate(0, -115%)` to 0) once the opening has gone.

**The long pinned scene is a camera path, not a straight slide.** About 8,700 px of scroll: the camera reads the first word,
swings down and to the right to the second word (which enters from the lower right), then up to the third (which enters from
the top). Photos, round discs and notes sit at different depths and move at different speeds relative to the words, and each
also bobs up and down on its own. Hand-drawn arrows between the words draw themselves (stroke offset) as the camera reaches
them. Small circled numbers (1), (2), (3) mark the words.

**The forest board's kraft card**: lines are revealed by the scroll itself, letter by letter, so a half-revealed line looks
sliced. Taped strips and the clear tape hanging from the top move at their own speed.

**The chapter word is set on an arc** ("CREATIVE" runs along a curve under the disc, "THE" above it) and the section changes
colour with the chosen product.

**Other pages** (all share the hero with a centred logo badge, a chip, a two-line hand-cut title and the same footer):
- About: the title's letters start scattered and assemble; a torn-paper card; a sentence on a wave over the forest board
  with four rounded "tab" cards floating at different heights; newspaper clippings.
- Our family (products): "PICK YOUR PLAYER" with six round discs in an overlapping row, each tilted; below it the footer.
- News: "WHAT'S ROLLING"; a highlighted card; a filter list (ALL, EVENT, NEWS with counts) beside a grid of dated cards.
- Contact: "LET'S STICK TOGETHER"; a cream panel with a dotted top edge and a form; a big vertical SEND button; a taped sticky
  note with the email and phone leaning on the panel's corner.

