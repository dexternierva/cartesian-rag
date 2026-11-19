# StockStatus

Stock is shown three ways at once: colour, dot shape and a word. In stock is a solid `status-ok` dot, low stock an outlined `status-warn` ring, out of stock a dashed `status-bad` ring. Then comes the count and the warehouse, in `ink-muted`.

- Status colours are separate from brand colours. "In stock" is lake blue (`status-ok`), not the forest brand green, so success and error are never told apart by red against green alone.
- Always include the word. Colour alone fails for about 1 in 12 men.
- The count is the number for **one** warehouse (`stock.depot_name`), as the engine checked it.
