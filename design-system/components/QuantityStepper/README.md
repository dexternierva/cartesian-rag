# QuantityStepper

Sets how many units to hold. Starts at the quantity the shopper asked for (the ticket's `constraints.quantity`), so "40 chairs" arrives filled in. The total next to it updates as the number changes.

- Minus, a typed number, plus. Minimum 1.
- If the number is more than the warehouse has, keep the number and say so beside the Hold button: never silently lower it.
