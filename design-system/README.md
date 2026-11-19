CartesianRAG is the shopping and support assistant for a store that sells gear for both the campsite and the office: folding tables, chairs, mugs, cups, lamps, jackets. The look is the outdoors brought indoors: forest green, lantern yellow, a spark of campfire red, and warm brown neutrals instead of grey. Answers are built from the store's database, and the design's main job is to make each answer usable (hold it, change it, check it) and honest (where it came from, how long it takes, what it assumed).

## Content fundamentals

Write from the shopper's side of the screen. Plain words, short sentences, sentence case, "you" for the shopper and "we" for the store. No emoji, no exclamation marks.

- **Shopper words, not engine words.** "Found 2 chairs that match everything you asked for", not "2 rows pass every rule". Table names, SKUs and SQL live only in the receipt drawer.
- **Say what a number is about.** "48 navy AeroTask Pro Mesh chairs are available at Indianapolis Regional", not "Available: 48".
- **Buttons say verb, object and consequence.** "Hold 40 chairs for 15 min", "Show the chair that arrives in 3 days". Never "Submit", never wording that sounds like a charge.
- **Say no with a way out.** "Nothing matches all of that right now. Without the 2-day delivery limit, 1 chair matches." Then a button for it.
- **Be honest about time.** "Usually 6 to 40 seconds", with the real steps. Never promise speed the engine doesn't have.
- **Be honest about the source.** "Real answers recorded on 18 Nov 2026" in a demo; "Live answers from the store's database" only when live.
- **Make assumptions visible.** If the assistant assumed something (one warehouse, any colour), it says so and offers the change.

## Visual foundations

### Colour

Two themes: **Daylight** (`light`, first) and **Campfire night** (`dark`). Every pair below holds at least 4.5:1 for text and 3:1 for control borders and marks, in both themes.

- **Neutrals are brown.** Page `canvas`; cards, panels and inputs `surface`; strips and wells `surface-sunk`; hairlines `line`; control borders `line-strong`. Text is `ink`, secondary text `ink-muted`.
- **Forest is the primary brand colour.** `forest` fills primary buttons and marks links and selected states, with `on-forest` text. Hover and pressed: `forest-strong`. Selected tint: `forest-soft`.
- **Lantern is the secondary brand colour.** `lantern` is a fill, never text: the "Best match" tag, the selected variant chip, the current step in the waiting card, and secondary buttons that suggest a way out. Text on it is `on-lantern`. Soft highlight: `lantern-soft`.
- **Campfire is a rare accent.** `campfire` appears only on promo tags ("New", "Camp-to-desk") and the spark in the brand mark. Never on buttons, errors, stock or timers: red reads as danger.
- **Status colours are separate from brand colours.** `status-ok` (lake blue), `status-warn` (amber) and `status-bad` (crimson), each with a `-soft` tint. Status is always colour + shape + word: solid dot for in stock, outlined ring for low stock, dashed ring for out of stock. "In stock" is not the brand green, so success and error never depend on telling red from green.
- **Receipts have their own paper.** `receipt-paper`, a dashed `receipt-edge`, `receipt-ink` text and a `receipt-check` tick. Proof always looks like a receipt, never like a button or a link.

### Type

Three families, all from Google Fonts:

- **Display:** `display` (Bricolage Grotesque), for titles and product names (`display-xl`, `heading-lg`, `heading-md`) and single big numbers.
- **Text:** `sans` (Figtree), for everything a shopper reads (`body`, `body-strong`, `body-sm`, `label`).
- **Data:** `mono` (JetBrains Mono), only for SKUs, row keys, SQL (`mono`) and timers (`timer`).

Prices and counts use tabular figures. Keep answers near 65 characters per line.

### Space, shape and depth

- Spacing steps `space-1` to `space-8` (4, 8, 12, 16, 24, 32 px). Cards pad `space-4`; answers in a conversation sit `space-6` apart.
- Radii: `radius-sm` for receipts and tags, `radius-md` for buttons, inputs and notices, `radius-lg` for cards and panels, `radius-pill` for chips.
- Shadows: `shadow-card` lifts cards just off the surface; `shadow-pop` is for the floating assistant and the receipt drawer only.

### States and focus

Keyboard focus is a solid 2px `forest-strong` outline, 2px from the element. Disabled controls use `surface-sunk` with `ink-muted` text and keep their label. Anything that looks tappable must do something: a chip that changes nothing is drawn as plain text instead.

### Motion

One motion only: the current step in the waiting card pulses gently. It stops under `prefers-reduced-motion`. No other animation.

## Iconography

Simple line icons on a 16px grid with a 1.75px stroke, rounded caps, drawn in `currentColor`: check, lock, close, alert, person. Product photos are placeholders (a line drawing of the product type on `surface-sunk`). The store has no logo yet: set the name "CartesianRAG" in `display`.

## Components

All components are plain HTML with the classes in `components/bundle.css`, prefixed `cr-`, inside an element with class `cr`. They map to what the engine returns in its answer ticket:

| Ticket | Component |
| --- | --- |
| `product_card` | ProductCard (with QuantityStepper, HoldNotice, ReceiptBadge) |
| `choices` / `state: disambiguate` | ChoiceList |
| `state: no_results` | NothingMatches |
| `handoff` / `state: handoff` | HandoffNotice |
| a lookup row (`table`) | AnswerFact |
| `citations` | ReceiptBadge, ReceiptDrawer |
| `constraints` | Chip (requirement) |
| while waiting | ProgressCard |
