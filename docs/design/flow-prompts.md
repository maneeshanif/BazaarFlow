# Prompts for Google Flow (Nano Banana / Imagen / Veo)

One prompt per file, each complete on its own: paste it as it is. Save the result in `frontend/public/brand/` under the
filename in the heading. The site shows a coloured placeholder for any file that is missing, so the order does not matter.

**Settings in Flow**
- Images: Nano Banana Pro if you can choose, otherwise the best image model offered. Set the aspect ratio in the heading.
  Make 2 or 3 variants and keep the best. Download at the largest size.
- Videos: Veo, 8 seconds, the aspect ratio in the heading, no sound needed.
- Flow cannot make transparent backgrounds. Where a heading says **cut-out**, the prompt asks for a plain white (or green)
  background; give me the file as it is and I remove the background and crop it in code. Same for the paper textures: I make them
  tile seamlessly.
- If a result shows readable brand names, logos or captions you did not ask for, regenerate that one.

**What BazaarFlow is, for context:** a back-office for small shops in Pakistan that pack and send out orders (delivery parcels,
small goods, packed food). Serious, documentary, warm. Colours: lime `#B6FE00`, forest green `#034102`, cream `#FDFBE8`,
coral `#FF7B5F`, orange `#FA8005`, sunny yellow `#F7D000`, sky `#50CBFF`, indigo `#2E3EAC`, kraft brown `#C99A63`.

---

## A. Photos (12). Documentary look, no faces to camera, no readable text

### photo-shop-counter.jpg  | 3:4
```
Documentary photograph, natural morning light, a real working neighbourhood grocery shop in Pakistan, honest and unposed, slightly warm colour, shallow depth of field. A shopkeeper seen from the side, writing an order into a phone behind the counter, glass jars of spices and sacks of rice on the shelves behind him, a steel scale on the counter. No readable text, no brand names, no logos, no watermark.
```

### photo-ledger.jpg  | 3:4
```
Documentary photograph, natural window light, shallow depth of field. Close-up of a hand writing with a pen in a handwritten khata ledger book on a worn wooden shop counter, a phone showing a chat conversation beside it, a small desk calculator and a neat pile of Pakistani rupee notes. Warm colour, honest and unposed. No readable text, no brand names, no watermark.
```

### photo-parcels.jpg  | 3:4
```
Documentary photograph, soft natural light, shallow depth of field. Two hands in a rust-orange knitted sweater holding two small parcels wrapped in brown kraft paper, tied with twine and sealed with tape, a handwritten address label on each that is blurred and unreadable. The person's face is not in the frame. Warm colour, honest and unposed. No watermark.
```

### photo-market.jpg  | 3:4
```
Documentary photograph at golden hour, warm colour. A narrow bazaar lane in a Pakistani city, a delivery rider on a motorbike seen from behind with a square insulated food box on the back, hanging fabrics and stacked produce crates on both sides, soft dust in the light. No readable signs, no brand names, no watermark.
```

### photo-team.jpg  | 3:4
```
Documentary photograph, natural light from a window. Two shop staff in a back room checking stock on a tablet next to metal shelves of boxed small goods and a packing table with a roll of tape and a ball of string, seen from the side and behind, not looking at the camera. Honest and unposed, slightly warm colour. No readable text, no brand names, no watermark.
```

### photo-family.jpg  | 16:9
```
Documentary photograph from directly above, soft natural light. A packing table covered with a plain cloth: three brown kraft-paper parcels tied with twine, a steel tiffin carrier, a paper bag of sweets, a roll of cream tape, scissors and a handwritten order list, arranged neatly with a little breathing space between them. Warm colour. No readable text, no brand names, no watermark.
```

### photo-food-pack.jpg  | 3:4
```
Documentary photograph in warm kitchen light, shallow depth of field. A pair of hands closing a cardboard box of hot food for delivery, rice and curry in separate small foil containers inside it, a paper bag beside the box, a little steam rising, a clean kitchen counter. Hands only, no face. No readable text, no brand names, no watermark.
```

### photo-delivery-bag.jpg  | 3:4
```
Documentary photograph in soft evening light. A delivery rider seen from behind, a green insulated box bag on his back, walking up a quiet residential lane in Pakistan, brick walls and a tree, face not visible. Honest and unposed, warm colour. No readable text, no brand names, no watermark.
```

### photo-small-goods.jpg  | 3:4
```
Documentary photograph, natural light. A shelf of small goods in a corner shop: tea packets, biscuits, jars of pickle and bars of soap in tidy rows, a hand-written price tag in marker pen that is blurred and unreadable. Shallow depth of field, slightly warm colour. No readable brand names, no logos, no watermark.
```

### photo-doorstep.jpg  | 3:4
```
Documentary photograph in soft morning light. A small brown paper parcel and a paper bag of groceries placed on a doorstep next to a pair of leather sandals, a patterned doormat, nobody in the frame. Quiet, honest, slightly warm colour. No readable text, no brand names, no watermark.
```

### photo-handover.jpg  | 4:3
```
Documentary photograph, shallow depth of field, soft morning light. Two hands handing over a wrapped brown parcel at a metal gate, one hand in a rider's glove, the other bare, no faces in the frame. Honest and unposed, warm colour. No readable text, no watermark.
```

### photo-bakery-box.jpg  | 3:4
```
Documentary photograph from above, natural light. A baker's hands tying twine around a small white bakery box on a flour-dusted wooden counter, a few loose flour marks and a wooden rolling pin at the edge, no face. Warm colour, shallow depth of field. No readable text, no brand names, no watermark.
```

---

## B. Illustration, hero object and round badges

### illus-produce.jpg  | 4:3
```
Hand-painted gouache pattern of ripe mangoes, green chillies and cut pomegranates with leaves, arranged evenly across warm cream paper, bold simple shapes, visible brush texture, rich saturated colour, a printed-textile feel. No text, no border, no watermark.
```

### hero-parcels.png  | 3:2  **cut-out**
```
Clean 3D render in a soft matte style, soft studio light from the upper right. Three small matte kraft-paper delivery parcels stacked at a slight angle: the biggest in the middle with a cream tape band over it, a smaller one on its left with a sunny-yellow tape band. To their right a round coral-red tiffin carrier with a forest-green lid and a small carry handle. A small roll of sunny-yellow tape floats above and behind. Centred on a pure plain white background (#FFFFFF), a soft shadow only directly under the objects, nothing else in the frame. No text, no logos.
```

### disc-sales.png  | 1:1  **cut-out**
```
A round product-seal badge, flat printed graphic style with a slight paper grain and a small offset shadow. A thick coral (#FF7B5F) ring, a lighter cream centre containing one bold simple receipt icon in dark forest green (#034102). Heavy condensed capital letters SALES curved along the inside of the ring, in cream. Slightly tilted. Centred on a pure plain white background (#FFFFFF), nothing else in the frame. No gradients, no glow.
```

### disc-stock.png  | 1:1  **cut-out**
```
A round product-seal badge, flat printed graphic style with a slight paper grain and a small offset shadow. A thick sunny-yellow (#F7D000) ring, a lighter cream centre containing one bold simple icon of stacked cardboard boxes in dark forest green (#034102). Heavy condensed capital letters STOCK curved along the inside of the ring, in dark forest green. Slightly tilted. Centred on a pure plain white background (#FFFFFF), nothing else in the frame. No gradients, no glow.
```

### disc-khata.png  | 1:1  **cut-out**
```
A round product-seal badge, flat printed graphic style with a slight paper grain and a small offset shadow. A thick indigo (#2E3EAC) ring, a lighter cream centre containing one bold simple open ledger-book icon in dark forest green (#034102). Heavy condensed capital letters KHATA curved along the inside of the ring, in cream. Slightly tilted. Centred on a pure plain white background (#FFFFFF), nothing else in the frame. No gradients, no glow.
```

### disc-chat.png  | 1:1  **cut-out**
```
A round product-seal badge, flat printed graphic style with a slight paper grain and a small offset shadow. A thick orange (#FA8005) ring, a lighter cream centre containing one bold simple chat-bubble icon in dark forest green (#034102). Heavy condensed capital letters INBOX curved along the inside of the ring, in cream. Slightly tilted. Centred on a pure plain white background (#FFFFFF), nothing else in the frame. No gradients, no glow.
```

### disc-money.png  | 1:1  **cut-out**
```
A round product-seal badge, flat printed graphic style with a slight paper grain and a small offset shadow. A thick sky-blue (#50CBFF) ring, a lighter cream centre containing one bold simple rupee-coin icon in dark forest green (#034102). Heavy condensed capital letters MONEY curved along the inside of the ring, in dark forest green. Slightly tilted. Centred on a pure plain white background (#FFFFFF), nothing else in the frame. No gradients, no glow.
```

### disc-posts.png  | 1:1  **cut-out**
```
A round product-seal badge, flat printed graphic style with a slight paper grain and a small offset shadow. A thick lime-green (#B6FE00) ring, a lighter cream centre containing one bold simple megaphone icon in dark forest green (#034102). Heavy condensed capital letters POSTS curved along the inside of the ring, in dark forest green. Slightly tilted. Centred on a pure plain white background (#FFFFFF), nothing else in the frame. No gradients, no glow.
```

---

## C. Paper textures (4). Flat, even light, fill the whole frame

### texture-lime-paper.jpg  | 1:1
```
Flat top-down macro photograph of crumpled lime-green paper (#B6FE00) with soft folds and creases, even diffuse lighting, no vignette, fills the entire frame edge to edge, no objects, no border.
```

### texture-forest-paper.jpg  | 1:1
```
Flat top-down macro photograph of crumpled deep forest-green paper (#034102) with soft folds and creases, even diffuse lighting, no vignette, fills the entire frame edge to edge, no objects, no border.
```

### texture-kraft.jpg  | 1:1
```
Flat top-down macro photograph of brown kraft cardboard paper (#C99A63) with visible fibre flecks and a few fine creases, even diffuse lighting, no vignette, fills the entire frame edge to edge, no objects, no border.
```

### texture-cream-paper.jpg  | 1:1
```
Flat top-down macro photograph of smooth off-white cream paper (#FDFBE8) with a faint fibre grain, even diffuse lighting, no vignette, fills the entire frame edge to edge, no objects, no border.
```

---

## D. Logo and icons

### logo-badge.png  | 3:2  **cut-out**
```
A logo badge, flat vector style, no gradients. A sturdy badge shaped like a parcel label with slightly cut corners, deep forest green (#034102), tilted about 5 degrees. Inside it the word BAZAARFLOW in heavy white condensed capital letters on two lines (BAZAAR above, FLOW below), a tiny TM mark at the top right. It must stay readable at 200 px wide. Centred on a pure plain white background (#FFFFFF), nothing else in the frame.
```

### logo-mark.png  | 1:1  **cut-out**
```
A square app mark, flat vector style, no gradients: the same parcel-label badge shape in deep forest green (#034102) with a lime (#B6FE00) symbol in the middle: a small parcel seen from above with a cross of tape over it. No text. Centred on a pure plain white background (#FFFFFF), nothing else in the frame.
```

### favicon.png  | 1:1
```
A square app icon, flat vector style: a lime (#B6FE00) parcel seen from above with a cross of tape over it, on a deep forest-green (#034102) rounded square that fills the frame. No text, no gradients.
```

### icons-sheet.png  | 16:9  **cut-out**
```
An icon sheet on a pure plain white background (#FFFFFF): fourteen chunky rounded line icons in a neat grid of two rows of seven, each with the same 3 px stroke weight and corner radius, dark forest green (#034102) on white, generous space between them, no labels. In order, row one: sale receipt, stock box, customer (person), udhaar ledger book, approval stamp, chat bubble, phone call. Row two: megaphone, chart bars, delivery bag, parcel, tiffin carrier, team (three people), settings gear. Flat, consistent, nothing else in the frame.
```

---

## E. Small drawn objects (the page also draws its own until these arrive)

### roll-small.png  | 1:1  **cut-out**
```
A small roll of cream masking tape seen at a three-quarter angle, soft studio light, flat clean look, on a pure plain white background (#FFFFFF), a soft shadow only directly under it, nothing else in the frame. No text.
```

### tape-strip.png  | 3:1  **cut-out**
```
A single strip of translucent kraft-coloured sticky tape lying flat, slightly torn zigzag ends, seen from above, soft shadow, on a pure plain white background (#FFFFFF), nothing else in the frame.
```

### sticky-note.png  | 1:1  **cut-out**
```
A yellow sticky note seen from above, slightly curled corner, with a short serious to-do list in neat handwriting: "pack Ali's order", "count flour and rice", "settle Sana's udhaar", each with an empty circle in front of it. Soft shadow, on a pure plain white background (#FFFFFF), nothing else in the frame.
```

### binder-clip.png  | 1:1  **cut-out**
```
A black steel binder clip seen from the front, clean studio light, soft shadow, on a pure plain white background (#FFFFFF), nothing else in the frame.
```

### ribbon.png  | 3:2  **cut-out**
```
An off-white paper tab with a dotted line across its top edge and a swallow-tail (V-notched) lower edge, empty, no text, seen from the front with a soft shadow, on a pure plain white background (#FFFFFF), nothing else in the frame.
```

### illus-empty.png  | 1:1  **cut-out**
```
A friendly flat illustration for an empty list: an open empty cardboard box with a small lime-green sparkle above it, paper grain, small offset shadow, simple shapes, on a pure plain white background (#FFFFFF), nothing else in the frame. No text.
```

### illus-error.png  | 1:1  **cut-out**
```
A friendly flat illustration for an error: a tangled strip of tape with a small surprised face, paper grain, small offset shadow, simple shapes, on a pure plain white background (#FFFFFF), nothing else in the frame. No text.
```

### illus-locked.png  | 1:1  **cut-out**
```
A friendly flat illustration for "access restricted": a small kraft parcel with a padlock tag tied to it, paper grain, small offset shadow, simple shapes, on a pure plain white background (#FFFFFF), nothing else in the frame. No text.
```

---

## F. Videos (Veo). Silent, a seamless loop if you can

### hero-parcels.mp4  | 16:9, 8 s  (background to be keyed out)
```
Clean 3D animation in a soft matte style, soft studio light from the upper right, a locked-off camera. Three small matte kraft-paper delivery parcels stacked at a slight angle (a cream tape band over the biggest, a yellow tape band on a smaller one), a round coral tiffin carrier with a forest-green lid, and a small roll of yellow tape. They float and turn very slowly, each at its own pace, as if weightless, then drift back to where they started so the loop is seamless. Flat bright green background (#00FF00), no floor, no shadow on the background, nothing else in the frame. No text, no logos, no sound.
```

### story-handover.mp4  | 4:3, 6 s
```
Documentary video, slow and quiet, shallow depth of field, soft morning light, a steady camera. Two hands hand over a wrapped brown parcel at a metal gate: one hand in a rider's glove passes it across and the bare hand draws it in. No faces in the frame. It ends in the same position it began so it loops. No text, no logos, no sound.
```
