"""Tests for quota enforcement."""

from django.contrib.auth.models import Group, User
from django.test import TestCase

from documents.models import Document, DocumentFile
from notifications.models import Quota
from notifications.quotas import check_quota, get_effective_quota, get_quota_usage_data, get_usage


class GetEffectiveQuotaTest(TestCase):
    """Tests for the get_effective_quota function."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", password="testpass123!"
        )

    def test_no_quota_returns_none(self):
        """When no quota is configured, return None."""
        result = get_effective_quota(self.user)
        self.assertIsNone(result)

    def test_user_quota_returned(self):
        """User-specific quota should be returned."""
        quota = Quota.objects.create(user=self.user, max_documents=50)
        result = get_effective_quota(self.user)
        self.assertEqual(result, quota)

    def test_group_quota_returned(self):
        """Group quota should apply when user has no user-specific quota."""
        group = Group.objects.create(name="editors")
        self.user.groups.add(group)
        quota = Quota.objects.create(group=group, max_documents=200)
        result = get_effective_quota(self.user)
        self.assertEqual(result, quota)

    def test_global_quota_returned(self):
        """Global quota should apply when no user or group quota exists."""
        quota = Quota.objects.create(max_documents=1000)
        result = get_effective_quota(self.user)
        self.assertEqual(result, quota)

    def test_user_quota_overrides_group(self):
        """User-specific quota takes priority over group quota."""
        group = Group.objects.create(name="editors")
        self.user.groups.add(group)
        Quota.objects.create(group=group, max_documents=200)
        user_quota = Quota.objects.create(user=self.user, max_documents=50)
        result = get_effective_quota(self.user)
        self.assertEqual(result, user_quota)

    def test_user_quota_overrides_global(self):
        """User-specific quota takes priority over global quota."""
        Quota.objects.create(max_documents=1000)
        user_quota = Quota.objects.create(user=self.user, max_documents=50)
        result = get_effective_quota(self.user)
        self.assertEqual(result, user_quota)

    def test_group_quota_overrides_global(self):
        """Group quota takes priority over global quota."""
        group = Group.objects.create(name="editors")
        self.user.groups.add(group)
        Quota.objects.create(max_documents=1000)
        group_quota = Quota.objects.create(group=group, max_documents=200)
        result = get_effective_quota(self.user)
        self.assertEqual(result, group_quota)


class QuotaEnforcementTest(TestCase):
    """Tests for the check_quota function."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", password="testpass123!"
        )

    def _create_documents(self, count, owner=None):
        """Create multiple documents for a user with unique filenames."""
        owner = owner or self.user
        docs = []
        for i in range(count):
            doc = Document.objects.create(
                title=f"Document {i}",
                owner=owner,
                filename=f"doc_{owner.username}_{i}.pdf",
            )
            docs.append(doc)
        return docs

    def _create_document_with_file(self, title, size_bytes, owner=None, idx=0):
        """Create a document with a DocumentFile of a given size."""
        owner = owner or self.user
        doc = Document.objects.create(
            title=title,
            owner=owner,
            filename=f"file_{owner.username}_{title.lower().replace(' ', '_')}_{idx}.pdf",
        )
        DocumentFile.objects.create(
            document=doc,
            filename=f"{title.lower().replace(' ', '_')}.pdf",
            mime_type="application/pdf",
            checksum=f"abc{idx:04d}",
            size=size_bytes,
        )
        return doc

    def test_no_quota_allows(self):
        """With no quota configured, any upload should be allowed."""
        allowed, message = check_quota(self.user)
        self.assertTrue(allowed)
        self.assertEqual(message, "No quota configured.")

    def test_user_quota_within_limit(self):
        """User with fewer documents than quota limit should be allowed."""
        Quota.objects.create(user=self.user, max_documents=10)
        self._create_documents(5)

        allowed, message = check_quota(self.user)
        self.assertTrue(allowed)
        self.assertEqual(message, "Within quota.")

    def test_user_quota_at_limit(self):
        """User at exactly the document quota limit should NOT be allowed."""
        Quota.objects.create(user=self.user, max_documents=5)
        self._create_documents(5)

        allowed, message = check_quota(self.user)
        self.assertFalse(allowed)
        self.assertIn("Document limit reached", message)
        self.assertIn("5/5", message)

    def test_user_quota_over_limit(self):
        """User over the document quota limit should NOT be allowed."""
        Quota.objects.create(user=self.user, max_documents=5)
        self._create_documents(6)

        allowed, message = check_quota(self.user)
        self.assertFalse(allowed)
        self.assertIn("Document limit reached", message)
        self.assertIn("6/5", message)

    def test_storage_quota_within_limit(self):
        """User with less storage used than quota limit should be allowed."""
        # 1 MB limit
        Quota.objects.create(user=self.user, max_storage_bytes=1_048_576)
        # 500 KB used
        self._create_document_with_file("Small Doc", 512_000, idx=0)

        allowed, message = check_quota(self.user)
        self.assertTrue(allowed)
        self.assertEqual(message, "Within quota.")

    def test_storage_quota_at_limit(self):
        """User at exactly the storage quota limit should NOT be allowed."""
        # 1 MB limit
        Quota.objects.create(user=self.user, max_storage_bytes=1_048_576)
        # 1 MB used exactly
        self._create_document_with_file("Full Doc", 1_048_576, idx=0)

        allowed, message = check_quota(self.user)
        self.assertFalse(allowed)
        self.assertIn("Storage limit reached", message)

    def test_storage_quota_over_limit(self):
        """User over the storage quota limit should NOT be allowed."""
        # 1 MB limit
        Quota.objects.create(user=self.user, max_storage_bytes=1_048_576)
        # 1.5 MB used
        self._create_document_with_file("Big Doc", 1_572_864, idx=0)

        allowed, message = check_quota(self.user)
        self.assertFalse(allowed)
        self.assertIn("Storage limit reached", message)

    def test_global_quota_applies(self):
        """Global quota (user=None, group=None) should apply to the user."""
        Quota.objects.create(max_documents=100)
        self._create_documents(5)

        allowed, message = check_quota(self.user)
        self.assertTrue(allowed)
        self.assertEqual(message, "Within quota.")

    def test_global_quota_blocks_at_limit(self):
        """Global quota should block when user is at the limit."""
        Quota.objects.create(max_documents=3)
        self._create_documents(3)

        allowed, message = check_quota(self.user)
        self.assertFalse(allowed)
        self.assertIn("Document limit reached", message)

    def test_user_quota_overrides_global(self):
        """User-specific quota of 50 takes priority over global 100."""
        Quota.objects.create(max_documents=100)  # global
        Quota.objects.create(user=self.user, max_documents=50)  # user-specific
        self._create_documents(5)

        allowed, message = check_quota(self.user)
        self.assertTrue(allowed)
        # Verify the effective quota is the user one (50), not global (100)
        effective = get_effective_quota(self.user)
        self.assertEqual(effective.max_documents, 50)

    def test_group_quota_applies(self):
        """A user in a group with a quota should have that quota apply."""
        group = Group.objects.create(name="editors")
        self.user.groups.add(group)
        Quota.objects.create(group=group, max_documents=200)
        self._create_documents(5)

        allowed, message = check_quota(self.user)
        self.assertTrue(allowed)
        effective = get_effective_quota(self.user)
        self.assertEqual(effective.max_documents, 200)

    def test_user_quota_overrides_group(self):
        """User-specific quota overrides group quota."""
        group = Group.objects.create(name="editors")
        self.user.groups.add(group)
        Quota.objects.create(group=group, max_documents=200)
        Quota.objects.create(user=self.user, max_documents=25)
        self._create_documents(5)

        effective = get_effective_quota(self.user)
        self.assertEqual(effective.max_documents, 25)

    def test_get_usage(self):
        """get_usage should return correct document count and storage bytes."""
        doc = Document.objects.create(
            title="Test Doc",
            owner=self.user,
            filename="test_usage.pdf",
        )
        DocumentFile.objects.create(
            document=doc,
            filename="test.pdf",
            mime_type="application/pdf",
            checksum="abc001",
            size=1024,
        )
        DocumentFile.objects.create(
            document=doc,
            filename="test_archive.pdf",
            mime_type="application/pdf",
            checksum="abc002",
            size=2048,
        )

        doc_count, storage_bytes = get_usage(self.user)
        self.assertEqual(doc_count, 1)
        self.assertEqual(storage_bytes, 3072)  # 1024 + 2048

    def test_get_usage_no_documents(self):
        """get_usage should return 0s when user has no documents."""
        doc_count, storage_bytes = get_usage(self.user)
        self.assertEqual(doc_count, 0)
        self.assertEqual(storage_bytes, 0)

    def test_get_usage_only_counts_owned_documents(self):
        """get_usage should only count documents owned by the specified user."""
        other_user = User.objects.create_user(
            username="other", password="testpass123!"
        )
        Document.objects.create(
            title="My Doc",
            owner=self.user,
            filename="my_doc.pdf",
        )
        Document.objects.create(
            title="Other Doc",
            owner=other_user,
            filename="other_doc.pdf",
        )

        doc_count, storage_bytes = get_usage(self.user)
        self.assertEqual(doc_count, 1)

    def test_get_quota_usage_data(self):
        """get_quota_usage_data should return a complete usage dict."""
        Quota.objects.create(
            user=self.user,
            max_documents=100,
            max_storage_bytes=10_485_760,  # 10 MB
        )
        self._create_document_with_file("Doc A", 2048, idx=0)
        self._create_document_with_file("Doc B", 4096, idx=1)

        data = get_quota_usage_data(self.user)

        self.assertEqual(data["document_count"], 2)
        self.assertEqual(data["storage_bytes"], 6144)  # 2048 + 4096
        self.assertEqual(data["max_documents"], 100)
        self.assertEqual(data["max_storage_bytes"], 10_485_760)
        self.assertEqual(data["documents_remaining"], 98)
        self.assertEqual(data["storage_remaining"], 10_485_760 - 6144)

    def test_get_quota_usage_data_no_quota(self):
        """get_quota_usage_data with no quota returns None for limits."""
        data = get_quota_usage_data(self.user)
        self.assertEqual(data["document_count"], 0)
        self.assertEqual(data["storage_bytes"], 0)
        self.assertIsNone(data["max_documents"])
        self.assertIsNone(data["max_storage_bytes"])
        self.assertIsNone(data["documents_remaining"])
        self.assertIsNone(data["storage_remaining"])

    def test_get_quota_usage_data_partial_quota(self):
        """get_quota_usage_data with only document limit returns None for storage."""
        Quota.objects.create(user=self.user, max_documents=50)
        data = get_quota_usage_data(self.user)

        self.assertEqual(data["max_documents"], 50)
        self.assertIsNone(data["max_storage_bytes"])
        self.assertEqual(data["documents_remaining"], 50)
        self.assertIsNone(data["storage_remaining"])

    def test_documents_remaining_never_negative(self):
        """documents_remaining should never be negative."""
        Quota.objects.create(user=self.user, max_documents=3)
        self._create_documents(5)

        data = get_quota_usage_data(self.user)
        self.assertEqual(data["documents_remaining"], 0)

    def test_unlimited_document_quota(self):
        """Unlimited document quota (None) allows any number of documents."""
        Quota.objects.create(
            user=self.user,
            max_documents=None,
            max_storage_bytes=1_048_576,
        )
        self._create_documents(100)

        allowed, message = check_quota(self.user)
        self.assertTrue(allowed)

    def test_unlimited_storage_quota(self):
        """Unlimited storage quota (None) allows any amount of storage."""
        Quota.objects.create(
            user=self.user,
            max_documents=1000,
            max_storage_bytes=None,
        )
        self._create_document_with_file("Huge File", 999_999_999, idx=0)

        allowed, message = check_quota(self.user)
        self.assertTrue(allowed)
