# ADR 0005: Playful identity for the public site and the whole application

Status: accepted (owner instruction, 2026-10-21)
Date: 2026-10-21

## Context
PRD section 33 left the visual identity open, and `context/ui-tokens.md` / `context/ui-rules.md` described a dense,
neutral back-office look "optimised for density, scanability and long-session legibility, not marketing impact".
The owner judged the result poor and asked for the identity studied in `docs/design/reference-sweettape/`
(lime and forest green, heavy condensed display type, curved seams, tilted taped photo frames, arc page transitions)
to apply to everything: the public site, sign-in, the shell and every dashboard, list and form.

## Decision
- The identity is applied everywhere. The owner explicitly accepted that this changes the density rules.
- Tokens stay the single source (ADR 0002): colours, radii, type and layout dimensions change as variable values in
  `app/global.css`; new tokens are added for the playful parts (radii `card`/`pill`, product accents, display font).
- Superseded in `context/ui-rules.md`: "Full width / 24px padding", 36px/28px grid rows, 34px controls, KPI value
  size, "no marketing impact". New defaults: rounded 2.67rem cards, 44px minimum control height, display type for page
  titles and KPI values, rows 48px.
- Unchanged: the PRD's information architecture, fields, roles and workflows; the four states on every list; keyboard
  focus rings; WCAG AA text contrast (`tests/ui/contrast.test.ts` stays and now guards the new palette); 360px with no
  horizontal page scroll; logical CSS properties for Urdu/RTL; `prefers-reduced-motion` turns all motion off.
- Motion: GSAP (+ ScrollTrigger) and Lenis for the public site's scroll scenes, `three` / `@react-three/fiber` for one
  hero object, CSS and GSAP entrances in the app. No scroll-jacking inside the signed-in app. Nothing new to install.
- Fonts (Google Fonts, free): Anton (display, standing in for the reference's paid Futura PT Condensed), Inter Tight
  (body), Nothing You Could Do (handwritten accents). Swapping in a licensed face later is one token value.
- Images, logo and icons are supplied by the owner from prompts in `docs/design/asset-prompts.md` and live in
  `public/brand/`. Until a file exists the components draw a coloured placeholder. SweetTape's own artwork, logo and
  copy are not used.

## Alternatives rejected
Restyling only the public site (owner wants one identity); keeping the dense rules and only recolouring (owner wants a
different UI, not a recolour).

## Consequences
Screens are less dense by default; wide tables rely on their own horizontal scroll. The Urdu review, the role rules
(managers do not see margin or payables) and every API rule are unchanged. If a screen becomes unusable at the new
density, record it in `context/progress-tracker.md` rather than reverting a token.
