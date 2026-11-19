# Chip

Chips are small, tappable choices. Three kinds:

- **Suggestion** (`cr-chip--suggest`): a full next question the shopper can send with one tap. Show the whole question and let it wrap to two lines rather than cut it off with "…".
- **Requirement** (`cr-chip--req`, `forest-soft` with a `forest` edge): one requirement the assistant is using, carried forward from earlier questions, with a remove button. Removing a chip re-asks the question without that requirement. This is how the conversation's memory stays visible and correctable.
- **Variant** (`cr-chip--variant`): a real toggle (`aria-pressed`). The selected one takes the `lantern` fill. A variant chip must change the card (colour, stock, delivery) when pressed: anything that looks tappable must do something.

The consumer provides the label, the action and, for requirements, the field it removes from the ticket's `constraints`.
