"""Tests for workflow conditions evaluator."""

from unittest.mock import MagicMock

from django.test import TestCase

from workflows.conditions import UnsafeExpressionError, evaluate_condition


class ConditionsTest(TestCase):
    """Tests for the safe expression evaluator."""

    def _make_instance(self, context=None, doc_title="Test Doc"):
        """Create a mock workflow instance."""
        instance = MagicMock()
        instance.context = context or {}
        instance.document = MagicMock()
        instance.document.title = doc_title
        instance.document.language = "en"
        instance.document.document_type_id = 1
        return instance

    def test_empty_expression_returns_true(self):
        instance = self._make_instance()
        self.assertTrue(evaluate_condition("", instance))

    def test_whitespace_expression_returns_true(self):
        instance = self._make_instance()
        self.assertTrue(evaluate_condition("   ", instance))

    def test_none_expression_returns_true(self):
        instance = self._make_instance()
        self.assertTrue(evaluate_condition(None, instance))

    def test_simple_true(self):
        instance = self._make_instance()
        self.assertTrue(evaluate_condition("True", instance))

    def test_simple_false(self):
        instance = self._make_instance()
        self.assertFalse(evaluate_condition("False", instance))

    def test_comparison(self):
        instance = self._make_instance()
        self.assertTrue(evaluate_condition("1 == 1", instance))
        self.assertFalse(evaluate_condition("1 == 2", instance))

    def test_document_attribute(self):
        instance = self._make_instance(doc_title="Invoice 2024")
        self.assertTrue(
            evaluate_condition("document.title == 'Invoice 2024'", instance)
        )

    def test_document_language(self):
        instance = self._make_instance()
        self.assertTrue(evaluate_condition("document.language == 'en'", instance))

    def test_context_access(self):
        instance = self._make_instance(context={"approved": True})
        self.assertTrue(evaluate_condition("context['approved'] == True", instance))

    def test_context_get(self):
        instance = self._make_instance(context={"score": 85})
        self.assertTrue(evaluate_condition("context.get('score', 0) > 50", instance))

    def test_context_missing_key_with_get(self):
        instance = self._make_instance(context={})
        self.assertFalse(
            evaluate_condition("context.get('approved', False)", instance)
        )

    def test_boolean_operations(self):
        instance = self._make_instance(context={"a": True, "b": False})
        self.assertTrue(
            evaluate_condition(
                "context['a'] == True and context['b'] == False", instance
            )
        )

    def test_or_operation(self):
        instance = self._make_instance(context={"status": "urgent"})
        self.assertTrue(
            evaluate_condition(
                "context.get('status') == 'urgent' or context.get('status') == 'high'",
                instance,
            )
        )

    def test_not_operation(self):
        instance = self._make_instance()
        self.assertTrue(evaluate_condition("not False", instance))

    def test_len_allowed(self):
        instance = self._make_instance(context={"items": [1, 2, 3]})
        self.assertTrue(
            evaluate_condition("len(context.get('items', [])) > 0", instance)
        )

    def test_in_operator(self):
        instance = self._make_instance(context={"tags": ["urgent", "invoice"]})
        self.assertTrue(
            evaluate_condition("'urgent' in context.get('tags', [])", instance)
        )

    def test_if_expression(self):
        instance = self._make_instance(context={"value": 10})
        result = evaluate_condition(
            "True if context.get('value', 0) > 5 else False", instance
        )
        self.assertTrue(result)

    def test_arithmetic(self):
        instance = self._make_instance()
        self.assertTrue(evaluate_condition("2 + 3 == 5", instance))

    def test_rejects_function_call(self):
        instance = self._make_instance()
        with self.assertRaises(UnsafeExpressionError):
            evaluate_condition("print('hello')", instance)

    def test_rejects_import(self):
        instance = self._make_instance()
        with self.assertRaises(UnsafeExpressionError):
            evaluate_condition("__import__('os')", instance)

    def test_rejects_lambda(self):
        instance = self._make_instance()
        with self.assertRaises(UnsafeExpressionError):
            evaluate_condition("(lambda: True)()", instance)

    def test_rejects_dunder_access(self):
        instance = self._make_instance()
        with self.assertRaises(UnsafeExpressionError):
            evaluate_condition("().__class__.__bases__", instance)

    def test_rejects_list_comprehension(self):
        instance = self._make_instance()
        with self.assertRaises(UnsafeExpressionError):
            evaluate_condition("[x for x in range(10)]", instance)

    def test_rejects_exec(self):
        instance = self._make_instance()
        with self.assertRaises(UnsafeExpressionError):
            evaluate_condition("exec('import os')", instance)

    def test_syntax_error(self):
        instance = self._make_instance()
        with self.assertRaises(UnsafeExpressionError):
            evaluate_condition("if True:", instance)

    def test_instance_access(self):
        instance = self._make_instance()
        instance.workflow = MagicMock()
        instance.workflow.label = "Test WF"
        self.assertTrue(
            evaluate_condition("instance.workflow.label == 'Test WF'", instance)
        )
