"""Tests for search query building and parsing."""

from django.test import TestCase

from search.query import (
    _parse_date_range,
    _parse_field_queries,
    build_search_query,
)


class ParseFieldQueriesTest(TestCase):
    def test_simple_field_query(self):
        remaining, queries = _parse_field_queries("tag:invoice")
        self.assertEqual(queries, [("tag", "invoice")])
        self.assertEqual(remaining.strip(), "")

    def test_quoted_value(self):
        remaining, queries = _parse_field_queries('correspondent:"Acme Corp"')
        self.assertEqual(queries, [("correspondent", "Acme Corp")])
        self.assertEqual(remaining.strip(), "")

    def test_bracket_value(self):
        remaining, queries = _parse_field_queries(
            "created:[2025-01-01 TO 2025-12-31]",
        )
        self.assertEqual(queries, [("created", "2025-01-01 TO 2025-12-31")])
        self.assertEqual(remaining.strip(), "")

    def test_mixed_text_and_fields(self):
        remaining, queries = _parse_field_queries(
            "important documents tag:finance type:invoice",
        )
        self.assertEqual(len(queries), 2)
        fields = {f: v for f, v in queries}
        self.assertEqual(fields["tag"], "finance")
        self.assertEqual(fields["type"], "invoice")
        self.assertIn("important documents", remaining)

    def test_no_field_queries(self):
        remaining, queries = _parse_field_queries("just plain text")
        self.assertEqual(queries, [])
        self.assertEqual(remaining, "just plain text")

    def test_multiple_same_field(self):
        remaining, queries = _parse_field_queries("tag:finance tag:invoice")
        self.assertEqual(len(queries), 2)
        self.assertEqual(queries[0], ("tag", "finance"))
        self.assertEqual(queries[1], ("tag", "invoice"))

    def test_field_case_insensitive(self):
        remaining, queries = _parse_field_queries("TAG:finance")
        self.assertEqual(queries[0][0], "tag")


class ParseDateRangeTest(TestCase):
    def test_full_range(self):
        result = _parse_date_range("2025-01-01 TO 2025-12-31")
        self.assertEqual(result, {"gte": "2025-01-01", "lte": "2025-12-31"})

    def test_open_start(self):
        result = _parse_date_range("* TO 2025-12-31")
        self.assertEqual(result, {"lte": "2025-12-31"})
        self.assertNotIn("gte", result)

    def test_open_end(self):
        result = _parse_date_range("2025-01-01 TO *")
        self.assertEqual(result, {"gte": "2025-01-01"})
        self.assertNotIn("lte", result)

    def test_invalid_format(self):
        result = _parse_date_range("just a date")
        self.assertIsNone(result)

    def test_both_wildcard(self):
        result = _parse_date_range("* TO *")
        self.assertEqual(result, {})


class BuildSearchQueryTest(TestCase):
    def test_empty_query(self):
        body = build_search_query("")
        self.assertEqual(body["query"], {"match_all": {}})

    def test_simple_text_query(self):
        body = build_search_query("invoice")
        query = body["query"]["bool"]["must"][0]
        self.assertEqual(query["multi_match"]["query"], "invoice")
        self.assertIn("title^3", query["multi_match"]["fields"])
        self.assertIn("content", query["multi_match"]["fields"])

    def test_permission_filter(self):
        body = build_search_query("test", user_id=42)
        filters = body["query"]["bool"]["filter"]
        owner_filter = [f for f in filters if "term" in f and "owner_id" in f["term"]]
        self.assertEqual(len(owner_filter), 1)
        self.assertEqual(owner_filter[0]["term"]["owner_id"], 42)

    def test_no_permission_filter_when_none(self):
        body = build_search_query("test")
        # Should have must but may not have filter
        bool_query = body["query"]["bool"]
        filters = bool_query.get("filter", [])
        owner_filters = [f for f in filters if "term" in f and "owner_id" in f.get("term", {})]
        self.assertEqual(len(owner_filters), 0)

    def test_tag_field_query(self):
        body = build_search_query("tag:finance")
        filters = body["query"]["bool"]["filter"]
        tag_filter = [f for f in filters if "term" in f and "tags" in f["term"]]
        self.assertEqual(len(tag_filter), 1)
        self.assertEqual(tag_filter[0]["term"]["tags"], "finance")

    def test_correspondent_field_query(self):
        body = build_search_query("correspondent:acme")
        must = body["query"]["bool"]["must"]
        match_clause = [m for m in must if "match" in m and "correspondent" in m["match"]]
        self.assertEqual(len(match_clause), 1)
        self.assertEqual(match_clause[0]["match"]["correspondent"], "acme")

    def test_date_range_field_query(self):
        body = build_search_query("created:[2025-01-01 TO 2025-12-31]")
        filters = body["query"]["bool"]["filter"]
        date_filter = [f for f in filters if "range" in f and "created" in f["range"]]
        self.assertEqual(len(date_filter), 1)
        self.assertEqual(date_filter[0]["range"]["created"]["gte"], "2025-01-01")
        self.assertEqual(date_filter[0]["range"]["created"]["lte"], "2025-12-31")

    def test_language_field_query(self):
        body = build_search_query("lang:en")
        filters = body["query"]["bool"]["filter"]
        lang_filter = [f for f in filters if "term" in f and "language" in f["term"]]
        self.assertEqual(len(lang_filter), 1)

    def test_additional_filters(self):
        body = build_search_query("test", filters={
            "document_type_id": 3,
            "correspondent_id": 7,
            "created_after": "2025-01-01",
        })
        filters = body["query"]["bool"]["filter"]
        type_filter = [f for f in filters if "term" in f and "document_type_id" in f.get("term", {})]
        self.assertEqual(len(type_filter), 1)
        self.assertEqual(type_filter[0]["term"]["document_type_id"], 3)

    def test_tag_ids_filter(self):
        body = build_search_query("test", filters={"tag_ids": [1, 2, 3]})
        filters = body["query"]["bool"]["filter"]
        tag_filters = [f for f in filters if "term" in f and "tag_ids" in f.get("term", {})]
        self.assertEqual(len(tag_filters), 3)

    def test_pagination(self):
        body = build_search_query("test", page=3, page_size=10)
        self.assertEqual(body["from"], 20)
        self.assertEqual(body["size"], 10)

    def test_highlighting_config(self):
        body = build_search_query("test")
        self.assertIn("highlight", body)
        self.assertIn("title", body["highlight"]["fields"])
        self.assertIn("content", body["highlight"]["fields"])
        self.assertEqual(body["highlight"]["pre_tags"], ["<mark>"])
        self.assertEqual(body["highlight"]["post_tags"], ["</mark>"])

    def test_aggregations_config(self):
        body = build_search_query("test")
        self.assertIn("aggs", body)
        self.assertIn("tag_facets", body["aggs"])
        self.assertIn("type_facets", body["aggs"])
        self.assertIn("correspondent_facets", body["aggs"])
        self.assertIn("date_histogram", body["aggs"])

    def test_mixed_text_and_field_queries(self):
        body = build_search_query("important tag:finance documents")
        must = body["query"]["bool"]["must"]
        # Should have a multi_match for remaining text
        text_queries = [m for m in must if "multi_match" in m]
        self.assertEqual(len(text_queries), 1)
        self.assertIn("important", text_queries[0]["multi_match"]["query"])
        self.assertIn("documents", text_queries[0]["multi_match"]["query"])
