# ChoiceList

"Did you mean…?" Use it when the engine returns `state: "disambiguate"`: the question matched products from different categories with close scores. Each choice names the product, then category and price, so options that share a word ("shell") are easy to tell apart.

- One question above the list, ending in "?".
- Each choice sends that choice's `follow_up_question` from the ticket.
- Never more than four choices; if there are more, the question is too vague: ask for a category instead.
