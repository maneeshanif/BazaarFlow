# Asset prompts

Generate these in your image tool and drop the files into `frontend/public/brand/` using the exact filenames below.
The site shows a coloured placeholder for any missing file, so you can add them in any order.

BazaarFlow is for small shops that pack and send out orders: delivery parcels, small goods and packed food (tiffins,
bakery boxes, grocery bags, sweets, spices). Tape is only a quiet detail (a taped corner, a sealed flap). Photos are
documentary and serious, like a good magazine feature on a working shop, not stock-photo smiles and not cartoons.
Updated 2026-10-31 (the first version was tape-themed).

**Photo style line** (add to every photo prompt): *Documentary photograph, natural light, real working shop in
Pakistan, honest and unposed, slightly warm colour, shallow depth of field, no watermarks, no readable brand names, no
text. People are shown from the side, from behind or by the hands, no staring into the lens. Original, not based on any
existing brand or photo.*

**Graphic style line** (add to every logo, disc, icon and illustration prompt): *Flat, bold, printed look with a slight
paper grain and a small offset shadow. Heavy condensed lettering where letters are needed. No gradients, no glow, no
watermarks. Original artwork, not based on any existing brand.*

## Ready-to-paste version

`docs/design/flow-prompts.md` has one complete prompt per file, written for Google Flow (Nano Banana and Veo). Use that file when
generating; this one explains the intent. The 24 stand-in images generated earlier were removed again at the owner's request, so
`frontend/public/brand/` is empty and the site shows coloured placeholders until the real files arrive.

Palette to ask for: lime `#B6FE00`, forest green `#034102`, cream `#FDFBE8`, coral `#FF7B5F`, orange `#FA8005`,
sunny yellow `#F7D000`, sky `#50CBFF`, indigo `#2E3EAC`, kraft brown `#C99A63`.

## Logo and icons

| File | Size | Prompt |
| --- | --- | --- |
| `logo-badge.png` (transparent) | 600x400 | A sturdy badge shaped like a parcel label with slightly cut corners, deep forest green, containing the word BAZAARFLOW in heavy white condensed capitals on two lines (BAZAAR / FLOW), tilted about 5 degrees, a tiny TM mark top right. Used on the lime opening screen, so it must read well at 200 px wide. |
| `logo-mark.svg` | 256x256 | Only the badge shape with a lime four-arrow box mark (a small parcel seen from above with a cross of tape) in the middle. For the top-left tile and the favicon. |
| `favicon.png` | 512x512 | The lime parcel-cross mark on a forest-green rounded square. |
| `icons/` (set of 14, SVG, 48x48) | | Chunky rounded line icons, 3 px stroke, forest green on transparent: sale receipt, stock box, customer, udhaar ledger book, approval stamp, chat bubble, phone call, megaphone, chart bars, delivery bag, parcel, tiffin carrier, team, settings gear. Same stroke weight and corner radius across the set. |

## Hero and section objects (transparent PNG, 1600 px)

The hero shows a 3D parcel stack drawn in the browser. The owner liked it, so it is now also an image and a video to make (below): when the video exists it plays instead of the browser-drawn scene; `hero-parcels.png` is the still shown for reduced motion and when WebGL is off.

| File | Prompt |
| --- | --- |
| `hero-parcels.png` | The hero object as a still, 1600 px, transparent: three small matte kraft-paper delivery parcels stacked at a slight angle (the biggest in the middle, a smaller one to its left with a sunny-yellow tape band, a cream tape band over the big one), a round coral tiffin carrier with a forest-green lid and a small carry handle to the right, and a small roll of sunny-yellow tape floating above and behind. Simple rounded shapes, soft studio light from the upper right, soft shadow underneath, centred. A clean 3D render look, not a photo, not a cartoon. |
| `disc-sales.png`, `disc-stock.png`, `disc-khata.png`, `disc-chat.png`, `disc-money.png`, `disc-posts.png` | A round badge, 800 px, like a product seal: a thick coloured ring with the centre in a lighter tint, a bold icon in the middle (sales: receipt; stock: stacked boxes; khata: ledger book; chat: chat bubble for the inbox; money: rupee coin; posts: megaphone) and a curved line of small text around the edge reading SALES, STOCK, KHATA, INBOX, MONEY or POSTS. Ring colours in order: coral, sunny yellow, indigo, orange, sky, lime-green. Transparent background, slight tilt, small shadow. These are the round pieces that float through the page, sit in the slider, pile up in the footer and overlap in a row on the "What it handles" page. |
| `roll-small.png` | A small roll of cream masking tape seen at an angle, transparent background. Used as a quiet detail beside photos. |
| `tape-strip.png` | A translucent kraft tape strip with slightly torn ends, 600x180, transparent. The page also draws its own strips in CSS; this file is optional. |
| `sticky-note.png` | A yellow sticky note with a short serious to-do list in neat handwriting: "pack Ali's order", "count flour and rice", "settle Sana's udhaar". Optional; the page draws its own in CSS. |
| `binder-clip.png` | A black steel binder clip, transparent, seen from the front. Optional. |
| `ribbon.png` | An off-white paper tab with a dotted top edge and a swallow-tail lower edge, 420x260, empty. Optional; the menu tab is drawn in CSS. |

## Video (looping, silent, optional)

The page checks for these files and plays them in place of the still or the browser-drawn scene. No file, no problem: the page
keeps showing what it shows now. Give each as `.mp4` (H.264) and, if you can, `.webm` (VP9) of the same clip. Silent, 24 or 30
fps, a seamless loop (the last frame flows into the first), under 4 MB each.

| File | Size | Prompt |
| --- | --- | --- |
| `hero-parcels.webm` (with **alpha / transparent background**) and `hero-parcels.mp4` | 1600x1000, 8 s loop | The same object as `hero-parcels.png`, moving: the three parcels, the tiffin carrier and the tape roll float and turn slowly, each at its own pace, the camera barely moving, a soft shadow on an invisible floor. Matte paper material, soft studio light from the upper right, clean 3D render look. WebM must have a transparent background so the crumpled lime paper shows through; the MP4 (no transparency) may sit on flat lime `#B6FE00`. |
| `story-handover.mp4` / `.webm` | 1600x1200, 6 s loop | Documentary, slow and quiet: two hands hand over a wrapped parcel at a gate, one in a rider's glove, one bare, the parcel passes across and the bare hand draws it in, natural morning light, shallow depth of field, no faces, no readable text. Ends where it starts. Used in the closing panel on every page. |

More clips can be wired in later (a turning disc, a rider in the street for the News page): ask when you have them.

## Photo frames (3:4 portrait unless stated, 1200 px)

These sit in rounded, tilted frames with taped corners. Use the photo style line above.

| File | Prompt |
| --- | --- |
| `photo-shop-counter.jpg` | A shopkeeper in a small neighbourhood grocery shop seen from the side, writing an order into a phone behind the counter, jars of spices and rice sacks behind, morning light. |
| `photo-ledger.jpg` | Close-up of a hand writing in a khata ledger book beside a phone showing a chat, a calculator and a small pile of notes, shallow depth of field. |
| `photo-parcels.jpg` | Hands in a rust-orange sweater holding two small brown-paper parcels sealed with tape and a hand-written address label (blurred, unreadable). |
| `photo-market.jpg` | A narrow bazaar lane at golden hour, a delivery rider on a motorbike with a square insulated food box on the back, hanging fabrics and produce crates, no readable signs. |
| `photo-team.jpg` | Two shop staff in a back room checking stock on a tablet next to shelves of boxed small goods and a packing table with tape and string. |
| `photo-family.jpg` (16:9, 1600 px) | A packing table seen from above: three brown parcels, a steel tiffin, a paper bag of sweets, a roll of tape, scissors and a handwritten order list, arranged neatly on a cloth. |
| `photo-food-pack.jpg` | Hands closing a cardboard box of hot food (rice, curry in separate small containers), a paper bag beside it, steam, kitchen counter, warm light. |
| `photo-delivery-bag.jpg` | A delivery rider's back with a green insulated box bag, walking up a residential lane, evening light, face not visible. |
| `photo-small-goods.jpg` | A shelf of small goods in a corner shop: tea packets, biscuits, jars of pickle, soap bars, tidy rows, a price tag in marker pen (blurred). |
| `photo-doorstep.jpg` | A small parcel and a paper bag of groceries placed on a doorstep next to a pair of sandals, morning light, no faces. |
| `photo-handover.jpg` | Two hands handing over a wrapped parcel at a gate, one in a rider's glove, one bare, shallow depth of field. |
| `photo-bakery-box.jpg` | A baker tying twine around a small white bakery box on a flour-dusted counter, seen from above. |

## Textures (seamless tiles, 1024 px, JPG)

| File | Prompt |
| --- | --- |
| `texture-lime-paper.jpg` | Crumpled lime-green paper, soft folds, seamless. |
| `texture-forest-paper.jpg` | Crumpled deep forest-green paper, seamless. |
| `texture-kraft.jpg` | Brown kraft cardboard with fibre flecks, seamless. |
| `texture-cream-paper.jpg` | Smooth off-white paper with a faint grain, seamless. Used for the menu sheet and the cards. |

## Illustrations (optional, 1200 px)

| File | Prompt |
| --- | --- |
| `illus-produce.jpg` | Hand-painted gouache pattern of mangoes, green chillies and pomegranates on cream paper. Decoration on the forest board (the reference site has a fruit illustration there). |
| `illus-empty.png` | Friendly empty-state scene: an open cardboard box with a lime sparkle, transparent background. Used when a list is empty. |
| `illus-error.png` | A tangled strip of tape with a surprised face, transparent background. Used for error states. |
| `illus-locked.png` | A small parcel with a padlock tag, transparent background. Used for "access restricted". |

## What the page draws itself (no file needed)

The cursor arrow, the menu tab and sheet, tape strips that unroll, the sticky note, the binder clip, the wavy ribbon, the
spinning "small shops, big orders" badge, the arrows that draw themselves, the torn-paper card, the crumpled paper grounds (a
fallback until your textures arrive) and the hand-cut headline letters are drawn in code, so they work before any artwork exists. The 3D parcels in the hero are built
in the browser with Three.js.
