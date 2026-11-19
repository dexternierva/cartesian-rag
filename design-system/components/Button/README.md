# Button

Buttons start an action. **Primary** (`forest` fill, `on-forest` text) at most once per card or panel, for the step the shopper came for: "Hold 40 chairs for 15 min". **Secondary** (`lantern` fill, `on-lantern` text) for a helpful way out the engine suggests, such as relaxing one requirement. **Quiet** (`surface`, `line-strong` border) for everything else. **Link** for small in-line actions.

- Label = verb + object + consequence, in sentence case: "Hold 40 chairs for 15 min", never "Submit" or "Reserve stock & create PO".
- Disabled buttons keep their label and say why in a line next to them ("Only 48 at Indianapolis Regional").
- Never use `campfire` on a button: red reads as danger.
- Minimum height 44px (36px for `cr-btn--sm` inside cards).

Classes: `cr-btn` + `cr-btn--primary | --secondary | --quiet`, optional `cr-btn--sm`, `cr-btn--block`; `cr-link`.
