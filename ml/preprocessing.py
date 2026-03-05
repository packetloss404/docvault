"""Text preprocessing for ML classification pipeline.

Implements the Paperless-ngx preprocessing approach:
- Regex tokenization (word characters only)
- Case normalization
- Snowball stemming with Redis-backed LRU cache
- Stop word filtering
- Large document cropping
"""

import logging
import re
from collections import OrderedDict

logger = logging.getLogger(__name__)

# Maximum document size: 800k start + 200k end = 1.2M chars
MAX_CONTENT_LENGTH = 1_200_000
CONTENT_HEAD = 800_000
CONTENT_TAIL = 200_000

# Token pattern: sequences of word characters (letters, digits, underscore)
TOKEN_PATTERN = re.compile(r"\w+")

# English stop words (Snowball set)
STOP_WORDS = frozenset([
    "a", "about", "above", "after", "again", "against", "all", "am", "an",
    "and", "any", "are", "aren't", "as", "at", "be", "because", "been",
    "before", "being", "below", "between", "both", "but", "by", "can",
    "can't", "cannot", "could", "couldn't", "did", "didn't", "do", "does",
    "doesn't", "doing", "don't", "down", "during", "each", "few", "for",
    "from", "further", "get", "got", "had", "hadn't", "has", "hasn't",
    "have", "haven't", "having", "he", "her", "here", "hers", "herself",
    "him", "himself", "his", "how", "i", "if", "in", "into", "is",
    "isn't", "it", "its", "itself", "just", "let's", "me", "might",
    "more", "most", "mustn't", "my", "myself", "no", "nor", "not", "of",
    "off", "on", "once", "only", "or", "other", "ought", "our", "ours",
    "ourselves", "out", "over", "own", "same", "shan't", "she", "should",
    "shouldn't", "so", "some", "such", "than", "that", "the", "their",
    "theirs", "them", "themselves", "then", "there", "these", "they",
    "this", "those", "through", "to", "too", "under", "until", "up",
    "very", "was", "wasn't", "we", "were", "weren't", "what", "when",
    "where", "which", "while", "who", "whom", "why", "will", "with",
    "won't", "would", "wouldn't", "you", "your", "yours", "yourself",
    "yourselves",
])


class StemmerCache:
    """LRU cache for Snowball stemmer results.

    Uses an in-memory OrderedDict with a configurable capacity.
    Falls back gracefully if stemming is unavailable.
    """

    def __init__(self, capacity=10_000):
        self._cache: OrderedDict[str, str] = OrderedDict()
        self._capacity = capacity
        self._stemmer = None
        self._init_stemmer()

    def _init_stemmer(self):
        try:
            from nltk.stem.snowball import SnowballStemmer
            self._stemmer = SnowballStemmer("english")
        except ImportError:
            logger.warning(
                "NLTK not installed — stemming disabled. "
                "Install nltk for better classification accuracy."
            )

    def stem(self, word: str) -> str:
        """Stem a word using Snowball with LRU caching."""
        if self._stemmer is None:
            return word

        if word in self._cache:
            self._cache.move_to_end(word)
            return self._cache[word]

        result = self._stemmer.stem(word)

        if len(self._cache) >= self._capacity:
            self._cache.popitem(last=False)

        self._cache[word] = result
        return result

    def clear(self):
        """Clear the stemming cache."""
        self._cache.clear()


# Module-level singleton
_stemmer_cache = None


def get_stemmer_cache() -> StemmerCache:
    """Get or create the module-level stemmer cache."""
    global _stemmer_cache
    if _stemmer_cache is None:
        _stemmer_cache = StemmerCache()
    return _stemmer_cache


def crop_content(content: str) -> str:
    """Crop large documents to a manageable size.

    Takes the first 800k chars and last 200k chars for documents
    exceeding 1.2M characters.
    """
    if len(content) <= MAX_CONTENT_LENGTH:
        return content
    return content[:CONTENT_HEAD] + " " + content[-CONTENT_TAIL:]


def preprocess(content: str) -> str:
    """Full preprocessing pipeline for document content.

    Steps:
    1. Crop large documents
    2. Lowercase
    3. Tokenize (word characters only)
    4. Remove stop words
    5. Stem each token
    6. Rejoin into space-separated string

    Returns preprocessed text suitable for feature extraction.
    """
    content = crop_content(content)
    content = content.lower()

    tokens = TOKEN_PATTERN.findall(content)
    tokens = [t for t in tokens if t not in STOP_WORDS and len(t) > 1]

    cache = get_stemmer_cache()
    tokens = [cache.stem(t) for t in tokens]

    return " ".join(tokens)
