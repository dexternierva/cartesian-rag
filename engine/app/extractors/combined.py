"""Two form-fillers working together: the AI first, the rules fill the gaps.

WHY (real result, 2026-11-12)
    - The AI read "how much for" and "forty" (the rules can't), but it LEFT OUT
      fields it should have filled: "navy" in Q11, "don't mind which warehouses" in Q16.
    - The rules can't read unusual phrasing, but they never forget a pattern
      they know: they caught "navy" and "don't mind which" every time.
    Each one covers the other's blind spot, the same lesson as hybrid search
    (keyword + meaning).

THE MERGE RULE (simple on purpose)
    For each box on the form:
        AI filled it?        -> keep the AI's value (it reads language better)
        AI left it empty?    -> use the rules' value, if the rules found one
"""


def make_combined(ai_extract, rules_extract):
    def extract(question, previous=None):
        ai_form = ai_extract(question, previous) or {}
        rules_form = rules_extract(question, previous) or {}
        merged = dict(ai_form)
        filled_by_rules = []
        for field, value in rules_form.items():
            if field == "follow_up" or value is None:
                continue                      # follow-up detection stays with the AI (or the station)
            if merged.get(field) in (None, "", []):
                merged[field] = value
                filled_by_rules.append(field)
        extract.last_filled_by_rules = filled_by_rules      # handy for debugging
        return merged

    extract.label = f"AI + rules backstop [{getattr(ai_extract, 'label', 'ai')}]"
    extract.last_filled_by_rules = []
    return extract
