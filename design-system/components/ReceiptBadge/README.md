# ReceiptBadge

Proof that a number was read from the store's database. It looks like a paper receipt: `receipt-paper` background, a dashed (perforated) `receipt-edge`, a `receipt-check` tick, then "Verified · see source" and the row key in `mono`. It is deliberately unlike a button or a link, so proof always looks the same.

- Every product card and every lookup answer has at least one.
- Opens the `ReceiptDrawer`.
- The row key is shopper-readable: table name + key ("inventory · AT-NAV-4D"), not `stock_available:AT-NAV-4D`.
- A receipt proves where a number came from, not that it answers the question. It never replaces checking the answer.
