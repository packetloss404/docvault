"""Tests for matching algorithm implementations."""

from django.contrib.auth.models import User
from django.test import TestCase

from documents.constants import (
    MATCH_ALL,
    MATCH_ANY,
    MATCH_AUTO,
    MATCH_FUZZY,
    MATCH_LITERAL,
    MATCH_NONE,
    MATCH_REGEX,
)
from organization.matching import get_matching_objects, matches
from organization.models import Correspondent, Tag


class MatchingAlgorithmsTest(TestCase):
    """Tests for all matching algorithms."""

    def setUp(self):
        self.user = User.objects.create_user(username="matchuser", password="pass!")

    def _make_tag(self, name, algorithm, match, insensitive=True):
        return Tag.objects.create(
            name=name,
            match=match,
            matching_algorithm=algorithm,
            is_insensitive=insensitive,
            owner=self.user,
        )

    def test_match_none_never_matches(self):
        tag = self._make_tag("No Match", MATCH_NONE, "invoice")
        self.assertFalse(matches(tag, "This is an invoice"))

    def test_match_any_single_word(self):
        tag = self._make_tag("Any", MATCH_ANY, "invoice receipt")
        self.assertTrue(matches(tag, "This document is an invoice"))
        self.assertTrue(matches(tag, "This is a receipt"))

    def test_match_any_no_match(self):
        tag = self._make_tag("Any", MATCH_ANY, "invoice receipt")
        self.assertFalse(matches(tag, "This is a contract"))

    def test_match_all_requires_all_words(self):
        tag = self._make_tag("All", MATCH_ALL, "bank statement")
        self.assertTrue(matches(tag, "Your bank statement is ready"))
        self.assertFalse(matches(tag, "Your bank is ready"))
        self.assertFalse(matches(tag, "Your statement is ready"))

    def test_match_literal_exact_string(self):
        tag = self._make_tag("Literal", MATCH_LITERAL, "ACME Corp")
        self.assertTrue(matches(tag, "Invoice from ACME Corp, dated 2025"))
        self.assertFalse(matches(tag, "Invoice from Beta Inc"))

    def test_match_literal_case_insensitive(self):
        tag = self._make_tag("Literal", MATCH_LITERAL, "acme corp", insensitive=True)
        self.assertTrue(matches(tag, "Invoice from ACME Corp"))

    def test_match_literal_case_sensitive(self):
        tag = self._make_tag("Literal", MATCH_LITERAL, "ACME Corp", insensitive=False)
        self.assertTrue(matches(tag, "Invoice from ACME Corp"))
        self.assertFalse(matches(tag, "Invoice from acme corp"))

    def test_match_regex_simple(self):
        tag = self._make_tag("Regex", MATCH_REGEX, r"INV-\d{4}")
        self.assertTrue(matches(tag, "Invoice number: INV-1234"))
        self.assertFalse(matches(tag, "Invoice number: 1234"))

    def test_match_regex_case_insensitive(self):
        tag = self._make_tag("Regex", MATCH_REGEX, r"invoice", insensitive=True)
        self.assertTrue(matches(tag, "This is an INVOICE"))

    def test_match_regex_invalid_pattern(self):
        tag = self._make_tag("Regex", MATCH_REGEX, r"[invalid")
        self.assertFalse(matches(tag, "anything"))

    def test_match_fuzzy_approximate(self):
        tag = self._make_tag("Fuzzy", MATCH_FUZZY, "invoice")
        self.assertTrue(matches(tag, "This is an invoice document"))

    def test_match_fuzzy_close_match(self):
        tag = self._make_tag("Fuzzy", MATCH_FUZZY, "invoce")
        # "invoce" is close to "invoice" (ratio ~0.92)
        self.assertTrue(matches(tag, "This is an invoice document"))

    def test_match_fuzzy_no_match(self):
        tag = self._make_tag("Fuzzy", MATCH_FUZZY, "xyzzy")
        self.assertFalse(matches(tag, "This is an invoice document"))

    def test_match_auto_returns_false(self):
        """Auto matching is a placeholder, should return False."""
        tag = self._make_tag("Auto", MATCH_AUTO, "anything")
        self.assertFalse(matches(tag, "Some content"))

    def test_empty_content_returns_false(self):
        tag = self._make_tag("Any", MATCH_ANY, "invoice")
        self.assertFalse(matches(tag, ""))

    def test_empty_pattern_returns_false(self):
        tag = self._make_tag("Any", MATCH_ANY, "")
        self.assertFalse(matches(tag, "Some content"))


class GetMatchingObjectsTest(TestCase):
    """Tests for the get_matching_objects function."""

    def setUp(self):
        self.user = User.objects.create_user(username="matchuser2", password="pass!")

    def test_get_matching_tags(self):
        Tag.objects.create(
            name="Finance", match="invoice bank", matching_algorithm=MATCH_ANY,
            owner=self.user,
        )
        Tag.objects.create(
            name="Legal", match="contract agreement", matching_algorithm=MATCH_ANY,
            owner=self.user,
        )
        Tag.objects.create(
            name="None", match="something", matching_algorithm=MATCH_NONE,
            owner=self.user,
        )

        results = get_matching_objects(
            Tag.objects.all(),
            "This invoice from the bank is overdue",
        )
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].name, "Finance")

    def test_get_matching_correspondents(self):
        Correspondent.objects.create(
            name="ACME", match="ACME Corp", matching_algorithm=MATCH_LITERAL,
            owner=self.user,
        )
        Correspondent.objects.create(
            name="Other", match="Other Inc", matching_algorithm=MATCH_LITERAL,
            owner=self.user,
        )

        results = get_matching_objects(
            Correspondent.objects.all(),
            "Invoice from ACME Corp dated 2025",
        )
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].name, "ACME")
