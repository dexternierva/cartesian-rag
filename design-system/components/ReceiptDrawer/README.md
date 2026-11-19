# ReceiptDrawer

Slides in from the right when a `ReceiptBadge` is pressed. It shows the exact database row, the query that read it, and when. It is the same paper as the badge (`receipt-paper`), with a dashed tear line under the title.

- Title in shopper words: "Where this number came from".
- Field names stay as the database spells them, in `mono`: this is the one place where engine words belong.
- `role="dialog"`, focus moves into the drawer, Esc and the close button return focus to the badge.
- On phones it takes the full width.
