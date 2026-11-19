# ProductCard

One product the engine found, built from a `product_card` component in the ticket. Top: photo, name and colour, price, SKU, `StockStatus`, delivery. Then specs, a `ReceiptBadge`, and the action area: `QuantityStepper`, total and a primary **Hold** button.

States:
- **Ready**: as shown.
- **Too many**: quantity above `stock.available`; the Hold button is disabled and a `status-warn` notice says how many the warehouse has.
- **Confirm**: a `lantern-soft` notice asks "Hold 40 × AeroTask Pro Mesh (Navy) for $12,800.00?" with Cancel and Confirm hold.
- **Held**: a `forest-soft` notice with a lock, "Held: 40 × …", a countdown, the PO number and what happens at zero.
- **Another product held**: Hold is disabled on the other cards.

The consumer provides the ticket's card (name, colour, sku, unit_price, stock, delivery, specs, citation_ids) and `constraints.quantity`.
