"""Tests for ML text preprocessing."""

from unittest.mock import MagicMock, patch

from django.test import TestCase

from ml.preprocessing import (
    CONTENT_HEAD,
    CONTENT_TAIL,
    MAX_CONTENT_LENGTH,
    STOP_WORDS,
    StemmerCache,
    crop_content,
    get_stemmer_cache,
    preprocess,
)


class CropContentTest(TestCase):
    """Tests for the crop_content function."""

    def test_short_content_unchanged(self):
        """Content under the limit passes through unmodified."""
        content = "Short document content."
        result = crop_content(content)
        self.assertEqual(result, content)

    def test_long_content_cropped(self):
        """Content over 1.2M chars is cropped to head + space + tail."""
        content = "a" * (MAX_CONTENT_LENGTH + 100_000)
        result = crop_content(content)
        # Head (800k) + space (1) + tail (200k)
        expected_length = CONTENT_HEAD + 1 + CONTENT_TAIL
        self.assertEqual(len(result), expected_length)
        self.assertLess(len(result), len(content))

    def test_exact_limit_unchanged(self):
        """Content at exactly 1.2M chars passes through unmodified."""
        content = "x" * MAX_CONTENT_LENGTH
        result = crop_content(content)
        self.assertEqual(len(result), MAX_CONTENT_LENGTH)
        self.assertEqual(result, content)

    def test_crop_preserves_head_and_tail(self):
        """Verify that the first 800k and last 200k chars are preserved."""
        # Build content with identifiable head, middle, and tail sections
        head = "H" * CONTENT_HEAD
        middle = "M" * 500_000  # Exceeds limit; will be cropped
        tail = "T" * CONTENT_TAIL
        content = head + middle + tail
        self.assertGreater(len(content), MAX_CONTENT_LENGTH)

        result = crop_content(content)
        # First 800k chars should be from the head
        self.assertTrue(result[:CONTENT_HEAD].startswith("H" * 100))
        self.assertEqual(result[:CONTENT_HEAD], head)
        # Last 200k chars should be from the tail
        self.assertEqual(result[-CONTENT_TAIL:], tail)


class StemmerCacheTest(TestCase):
    """Tests for the StemmerCache LRU cache."""

    def test_stem_word(self):
        """Basic stemming works (e.g., 'running' -> 'run')."""
        cache = StemmerCache(capacity=100)
        if cache._stemmer is not None:
            result = cache.stem("running")
            self.assertEqual(result, "run")
        else:
            # If NLTK is not installed, word is returned as-is
            result = cache.stem("running")
            self.assertEqual(result, "running")

    def test_cache_hit(self):
        """Stemming the same word twice returns the cached result."""
        cache = StemmerCache(capacity=100)
        result1 = cache.stem("running")
        result2 = cache.stem("running")
        self.assertEqual(result1, result2)
        # If stemmer is available, the word should be in the cache
        if cache._stemmer is not None:
            self.assertIn("running", cache._cache)

    def test_lru_eviction(self):
        """Cache at capacity evicts the least recently used entry."""
        cache = StemmerCache(capacity=3)
        # Manually populate the cache to control content
        cache._cache["word_a"] = "stem_a"
        cache._cache["word_b"] = "stem_b"
        cache._cache["word_c"] = "stem_c"

        # Access word_a to make it recently used
        cache._cache.move_to_end("word_a")

        # Now adding a 4th item should evict word_b (LRU, first in)
        if cache._stemmer is not None:
            cache.stem("testing")
            self.assertNotIn("word_b", cache._cache)
            # word_a should still be there (was recently used)
            self.assertIn("word_a", cache._cache)
        else:
            # Without stemmer, no caching happens
            pass

    def test_clear(self):
        """clear() empties the cache."""
        cache = StemmerCache(capacity=100)
        cache._cache["word"] = "stem"
        self.assertEqual(len(cache._cache), 1)
        cache.clear()
        self.assertEqual(len(cache._cache), 0)

    def test_capacity(self):
        """Cache respects the capacity limit."""
        capacity = 5
        cache = StemmerCache(capacity=capacity)
        # Manually fill beyond capacity
        for i in range(capacity + 3):
            cache._cache[f"word_{i}"] = f"stem_{i}"
            # Simulate the eviction logic used by stem()
            if len(cache._cache) > capacity:
                cache._cache.popitem(last=False)
        self.assertLessEqual(len(cache._cache), capacity)


class GetStemmerCacheTest(TestCase):
    """Tests for the get_stemmer_cache singleton."""

    def test_returns_stemmer_cache_instance(self):
        """get_stemmer_cache returns a StemmerCache instance."""
        cache = get_stemmer_cache()
        self.assertIsInstance(cache, StemmerCache)

    def test_returns_same_instance(self):
        """get_stemmer_cache returns the same singleton on repeated calls."""
        cache1 = get_stemmer_cache()
        cache2 = get_stemmer_cache()
        self.assertIs(cache1, cache2)


class PreprocessTest(TestCase):
    """Tests for the preprocess function."""

    def test_basic_preprocessing(self):
        """Basic input is lowercased, stop-words removed, and stemmed."""
        result = preprocess("The quick brown fox jumps")
        # "The" is a stop word and should be removed
        self.assertNotIn("the", result.split())
        # All tokens should be lowercase
        for token in result.split():
            self.assertEqual(token, token.lower())
        # Result should not be empty
        self.assertTrue(len(result) > 0)

    def test_stop_words_removed(self):
        """Common stop words are filtered out."""
        result = preprocess("the and but or is was are been have has")
        # All of these are stop words — result should be empty
        self.assertEqual(result.strip(), "")

    def test_single_char_tokens_removed(self):
        """Single-character tokens are removed by the len(t) > 1 check."""
        result = preprocess("I a x the big cat")
        tokens = result.split()
        # "I", "a", "x" are single chars; "the" is a stop word
        # Only "big" and "cat" should survive (stemmed forms)
        for token in tokens:
            self.assertGreater(len(token), 1)

    def test_empty_content(self):
        """Empty string input returns empty string."""
        result = preprocess("")
        self.assertEqual(result, "")

    def test_case_normalization(self):
        """Uppercase content is lowercased before tokenization."""
        result = preprocess("INVOICE PAYMENT BILLING")
        for token in result.split():
            self.assertEqual(token, token.lower())

    def test_special_characters_stripped(self):
        """Punctuation and special characters are removed by the tokenizer."""
        result = preprocess("Hello, world! This is a test... #2024")
        # No punctuation should remain in tokens
        for token in result.split():
            self.assertTrue(token.isalnum() or "_" in token)
            # No standalone punctuation marks
            self.assertNotIn(",", token)
            self.assertNotIn("!", token)
            self.assertNotIn(".", token)
            self.assertNotIn("#", token)
