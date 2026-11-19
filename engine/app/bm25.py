"""BM25: the keyword detective, written from scratch so you can read every line.

THE IDEA (no maths degree needed)
    Score each document for a question by adding up points per matching word:
      1. RARE words are worth more.   "stackable" appears in 1 product -> big clue.
                                      "chair" appears in 30 -> weak clue.
      2. REPEATS help, but less each time.  Saying "mesh" 5 times isn't 5x better.
      3. SHORT documents get a small boost. One match in 6 words beats one in 60.

    That's all BM25 is: a careful word-matching score. It has no idea that
    "lamp" and "light" mean nearly the same thing.
"""
import math
import re

# Tiny words that appear everywhere and tell us nothing.
STOPWORDS = {"a", "an", "the", "and", "or", "of", "to", "in", "on", "at", "for", "with",
             "my", "me", "i", "is", "are", "it", "its", "that", "this", "can", "up",
             "do", "you", "some", "something", "somewhere", "put", "under"}


def tokenize(text: str) -> list:
    """'A Breathable chair!' -> ['breathable', 'chair']"""
    words = re.findall(r"[a-z0-9]+", text.lower())
    return [w for w in words if w not in STOPWORDS and len(w) > 1]


class BM25:
    def __init__(self, documents: list, k1: float = 1.5, b: float = 0.75):
        """documents = list of strings. k1 and b are the standard tuning knobs."""
        self.k1, self.b = k1, b
        self.docs = [tokenize(d) for d in documents]
        self.n = len(self.docs)
        self.avg_len = sum(len(d) for d in self.docs) / max(self.n, 1)
        # In how many documents does each word appear?
        self.doc_freq = {}
        for doc in self.docs:
            for word in set(doc):
                self.doc_freq[word] = self.doc_freq.get(word, 0) + 1

    def _rarity(self, word: str) -> float:
        """IDF: rare word -> high number, common word -> near zero."""
        df = self.doc_freq.get(word, 0)
        return math.log((self.n - df + 0.5) / (df + 0.5) + 1)

    def scores(self, question: str) -> list:
        """One score per document. 0 means no shared words at all."""
        q_words = tokenize(question)
        out = []
        for doc in self.docs:
            score = 0.0
            for word in q_words:
                tf = doc.count(word)                      # how often the word appears here
                if tf == 0:
                    continue
                length_penalty = 1 - self.b + self.b * len(doc) / self.avg_len
                score += self._rarity(word) * tf * (self.k1 + 1) / (tf + self.k1 * length_penalty)
            out.append(score)
        return out


if __name__ == "__main__":
    docs = ["Stackable guest chair with a molded shell seat",
            "Ergonomic mesh chair with 4D armrests",
            "Braided USB-C charging cable, navy blue"]
    engine = BM25(docs)
    for q in ["stackable chair", "navy blue charging cable", "something to charge my laptop"]:
        print(f"{q!r:<36} tokens={tokenize(q)}  scores={[round(s, 2) for s in engine.scores(q)]}")
