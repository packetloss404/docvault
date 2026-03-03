"""Tests for source models."""

from django.contrib.auth.models import User
from django.test import TestCase

from documents.models import DocumentType
from organization.models import Tag
from sources.constants import (
    CONSUMED_ACTION_DELETE,
    CONSUMED_ACTION_MOVE,
    CONSUMED_ACTION_NOTHING,
    MAIL_ACCOUNT_GMAIL_OAUTH,
    MAIL_ACCOUNT_IMAP,
    MAIL_ACTION_DOWNLOAD_ATTACHMENT,
    MAIL_ACTION_PROCESS_EMAIL,
    MAIL_PROCESSED_DELETE,
    MAIL_PROCESSED_FLAG,
    MAIL_PROCESSED_MOVE,
    MAIL_PROCESSED_READ,
    MAIL_SECURITY_NONE,
    MAIL_SECURITY_SSL,
    MAIL_SECURITY_STARTTLS,
    SOURCE_EMAIL,
    SOURCE_S3,
    SOURCE_STAGING,
    SOURCE_WATCH_FOLDER,
)
from sources.models import MailAccount, MailRule, Source, WatchFolderSource


class SourceModelTest(TestCase):
    """Tests for Source model."""

    def test_create_source(self):
        source = Source.objects.create(
            label="My Watch Folder",
            source_type=SOURCE_WATCH_FOLDER,
        )
        self.assertEqual(str(source), "My Watch Folder (Watch Folder)")
        self.assertTrue(source.enabled)

    def test_create_email_source(self):
        source = Source.objects.create(
            label="Mail Source",
            source_type=SOURCE_EMAIL,
        )
        self.assertEqual(str(source), "Mail Source (Email (IMAP))")

    def test_create_staging_source(self):
        source = Source.objects.create(
            label="Staging Area",
            source_type=SOURCE_STAGING,
        )
        self.assertEqual(str(source), "Staging Area (Staging Folder)")

    def test_create_s3_source(self):
        source = Source.objects.create(
            label="Cloud Bucket",
            source_type=SOURCE_S3,
        )
        self.assertEqual(str(source), "Cloud Bucket (S3 Bucket)")

    def test_source_with_owner(self):
        user = User.objects.create_user("test", "test@test.com", "pass")
        source = Source.objects.create(
            label="User Source",
            source_type=SOURCE_WATCH_FOLDER,
            owner=user,
        )
        self.assertEqual(source.owner, user)

    def test_source_with_document_type(self):
        doc_type = DocumentType.objects.create(name="Invoice")
        source = Source.objects.create(
            label="Typed Source",
            source_type=SOURCE_WATCH_FOLDER,
            document_type=doc_type,
        )
        self.assertEqual(source.document_type, doc_type)

    def test_source_with_tags(self):
        tag1 = Tag.objects.create(name="auto-import", color="#ff0000")
        tag2 = Tag.objects.create(name="needs-review", color="#00ff00")
        source = Source.objects.create(
            label="Tagged Source",
            source_type=SOURCE_WATCH_FOLDER,
        )
        source.tags.add(tag1, tag2)
        self.assertEqual(source.tags.count(), 2)

    def test_source_enabled_by_default(self):
        source = Source.objects.create(
            label="Default Source",
            source_type=SOURCE_WATCH_FOLDER,
        )
        self.assertTrue(source.enabled)

    def test_source_can_be_disabled(self):
        source = Source.objects.create(
            label="Disabled Source",
            source_type=SOURCE_WATCH_FOLDER,
            enabled=False,
        )
        self.assertFalse(source.enabled)

    def test_source_ordering(self):
        Source.objects.create(label="Bravo", source_type=SOURCE_WATCH_FOLDER)
        Source.objects.create(label="Alpha", source_type=SOURCE_WATCH_FOLDER)
        sources = list(Source.objects.all())
        self.assertEqual(sources[0].label, "Alpha")
        self.assertEqual(sources[1].label, "Bravo")

    def test_source_owner_deletion_sets_null(self):
        user = User.objects.create_user("delme", "del@test.com", "pass")
        source = Source.objects.create(
            label="Orphan Source",
            source_type=SOURCE_WATCH_FOLDER,
            owner=user,
        )
        user.delete()
        source.refresh_from_db()
        self.assertIsNone(source.owner)


class WatchFolderSourceTest(TestCase):
    """Tests for WatchFolderSource model."""

    def test_create_watch_folder(self):
        source = Source.objects.create(
            label="Inbox", source_type=SOURCE_WATCH_FOLDER,
        )
        wf = WatchFolderSource.objects.create(
            source=source,
            path="/data/consume",
            polling_interval=60,
        )
        self.assertEqual(wf.consumed_action, CONSUMED_ACTION_MOVE)
        self.assertEqual(str(wf), "WatchFolder: /data/consume")

    def test_watch_folder_default_polling_interval(self):
        source = Source.objects.create(
            label="Default Poll", source_type=SOURCE_WATCH_FOLDER,
        )
        wf = WatchFolderSource.objects.create(
            source=source,
            path="/data/watch",
        )
        self.assertEqual(wf.polling_interval, 300)

    def test_watch_folder_consumed_action_delete(self):
        source = Source.objects.create(
            label="Delete Source", source_type=SOURCE_WATCH_FOLDER,
        )
        wf = WatchFolderSource.objects.create(
            source=source,
            path="/data/delete",
            consumed_action=CONSUMED_ACTION_DELETE,
        )
        self.assertEqual(wf.consumed_action, CONSUMED_ACTION_DELETE)

    def test_watch_folder_consumed_action_nothing(self):
        source = Source.objects.create(
            label="Nothing Source", source_type=SOURCE_WATCH_FOLDER,
        )
        wf = WatchFolderSource.objects.create(
            source=source,
            path="/data/noop",
            consumed_action=CONSUMED_ACTION_NOTHING,
        )
        self.assertEqual(wf.consumed_action, CONSUMED_ACTION_NOTHING)

    def test_watch_folder_with_consumed_directory(self):
        source = Source.objects.create(
            label="Move Source", source_type=SOURCE_WATCH_FOLDER,
        )
        wf = WatchFolderSource.objects.create(
            source=source,
            path="/data/incoming",
            consumed_directory="/data/consumed",
        )
        self.assertEqual(wf.consumed_directory, "/data/consumed")

    def test_watch_folder_cascade_delete(self):
        """Deleting the source cascades to the watch folder."""
        source = Source.objects.create(
            label="Cascade Test", source_type=SOURCE_WATCH_FOLDER,
        )
        WatchFolderSource.objects.create(source=source, path="/tmp/test")
        source.delete()
        self.assertEqual(WatchFolderSource.objects.count(), 0)

    def test_watch_folder_one_to_one(self):
        """A source can only have one watch folder configuration."""
        source = Source.objects.create(
            label="One-to-One", source_type=SOURCE_WATCH_FOLDER,
        )
        WatchFolderSource.objects.create(source=source, path="/path/1")
        with self.assertRaises(Exception):
            WatchFolderSource.objects.create(source=source, path="/path/2")


class MailAccountTest(TestCase):
    """Tests for MailAccount model."""

    def test_create_mail_account(self):
        account = MailAccount.objects.create(
            name="Work Email",
            imap_server="imap.example.com",
            port=993,
            security=MAIL_SECURITY_SSL,
            account_type=MAIL_ACCOUNT_IMAP,
            username="user@example.com",
            password="secret",
        )
        self.assertEqual(str(account), "Work Email (user@example.com)")
        self.assertTrue(account.enabled)

    def test_mail_account_defaults(self):
        account = MailAccount.objects.create(
            name="Defaults",
            imap_server="imap.test.com",
            username="test@test.com",
        )
        self.assertEqual(account.port, 993)
        self.assertEqual(account.security, MAIL_SECURITY_SSL)
        self.assertEqual(account.account_type, MAIL_ACCOUNT_IMAP)
        self.assertTrue(account.enabled)

    def test_mail_account_starttls(self):
        account = MailAccount.objects.create(
            name="STARTTLS",
            imap_server="imap.test.com",
            security=MAIL_SECURITY_STARTTLS,
            username="test@test.com",
        )
        self.assertEqual(account.security, MAIL_SECURITY_STARTTLS)

    def test_mail_account_no_security(self):
        account = MailAccount.objects.create(
            name="Insecure",
            imap_server="imap.test.com",
            security=MAIL_SECURITY_NONE,
            username="test@test.com",
        )
        self.assertEqual(account.security, MAIL_SECURITY_NONE)

    def test_mail_account_gmail_oauth(self):
        account = MailAccount.objects.create(
            name="Gmail",
            imap_server="imap.gmail.com",
            account_type=MAIL_ACCOUNT_GMAIL_OAUTH,
            username="user@gmail.com",
            oauth_client_id="client-id",
            oauth_client_secret="client-secret",
        )
        self.assertEqual(account.account_type, MAIL_ACCOUNT_GMAIL_OAUTH)
        self.assertEqual(account.oauth_client_id, "client-id")

    def test_mail_account_can_be_disabled(self):
        account = MailAccount.objects.create(
            name="Disabled",
            imap_server="imap.test.com",
            username="test@test.com",
            enabled=False,
        )
        self.assertFalse(account.enabled)

    def test_mail_account_ordering(self):
        MailAccount.objects.create(
            name="Zebra", imap_server="z.test.com", username="z@test.com",
        )
        MailAccount.objects.create(
            name="Alpha", imap_server="a.test.com", username="a@test.com",
        )
        accounts = list(MailAccount.objects.all())
        self.assertEqual(accounts[0].name, "Alpha")
        self.assertEqual(accounts[1].name, "Zebra")


class MailRuleTest(TestCase):
    """Tests for MailRule model."""

    def setUp(self):
        self.account = MailAccount.objects.create(
            name="Test",
            imap_server="imap.test.com",
            username="test@test.com",
            password="pass",
        )

    def test_create_mail_rule(self):
        rule = MailRule.objects.create(
            name="Download PDFs",
            account=self.account,
            folder="INBOX",
            filter_attachment_filename="*.pdf",
            action=MAIL_ACTION_DOWNLOAD_ATTACHMENT,
            processed_action=MAIL_PROCESSED_READ,
        )
        self.assertEqual(str(rule), "Download PDFs (Test)")
        self.assertTrue(rule.enabled)

    def test_mail_rule_defaults(self):
        rule = MailRule.objects.create(
            name="Defaults",
            account=self.account,
        )
        self.assertEqual(rule.folder, "INBOX")
        self.assertEqual(rule.action, MAIL_ACTION_DOWNLOAD_ATTACHMENT)
        self.assertEqual(rule.processed_action, MAIL_PROCESSED_READ)
        self.assertEqual(rule.maximum_age, 30)
        self.assertEqual(rule.order, 0)
        self.assertTrue(rule.enabled)

    def test_mail_rule_process_email_action(self):
        rule = MailRule.objects.create(
            name="Process Email",
            account=self.account,
            action=MAIL_ACTION_PROCESS_EMAIL,
        )
        self.assertEqual(rule.action, MAIL_ACTION_PROCESS_EMAIL)

    def test_mail_rule_processed_move(self):
        rule = MailRule.objects.create(
            name="Move Processed",
            account=self.account,
            processed_action=MAIL_PROCESSED_MOVE,
            processed_folder="Archive",
        )
        self.assertEqual(rule.processed_action, MAIL_PROCESSED_MOVE)
        self.assertEqual(rule.processed_folder, "Archive")

    def test_mail_rule_processed_delete(self):
        rule = MailRule.objects.create(
            name="Delete Processed",
            account=self.account,
            processed_action=MAIL_PROCESSED_DELETE,
        )
        self.assertEqual(rule.processed_action, MAIL_PROCESSED_DELETE)

    def test_mail_rule_processed_flag(self):
        rule = MailRule.objects.create(
            name="Flag Processed",
            account=self.account,
            processed_action=MAIL_PROCESSED_FLAG,
        )
        self.assertEqual(rule.processed_action, MAIL_PROCESSED_FLAG)

    def test_mail_rule_with_filters(self):
        rule = MailRule.objects.create(
            name="Filtered",
            account=self.account,
            filter_from="billing@company.com",
            filter_subject="Invoice*",
            filter_body="payment",
            filter_attachment_filename="*.pdf",
        )
        self.assertEqual(rule.filter_from, "billing@company.com")
        self.assertEqual(rule.filter_subject, "Invoice*")
        self.assertEqual(rule.filter_body, "payment")
        self.assertEqual(rule.filter_attachment_filename, "*.pdf")

    def test_mail_rule_with_classification(self):
        doc_type = DocumentType.objects.create(name="Invoice")
        tag = Tag.objects.create(name="email-import", color="#ff0000")
        user = User.objects.create_user("owner", "owner@test.com", "pass")
        rule = MailRule.objects.create(
            name="Classified",
            account=self.account,
            document_type=doc_type,
            owner=user,
        )
        rule.tags.add(tag)
        self.assertEqual(rule.document_type, doc_type)
        self.assertEqual(rule.owner, user)
        self.assertEqual(rule.tags.count(), 1)

    def test_mail_rule_ordering(self):
        rule1 = MailRule.objects.create(
            name="Rule B", account=self.account, order=1,
        )
        rule2 = MailRule.objects.create(
            name="Rule A", account=self.account, order=0,
        )
        rules = list(MailRule.objects.all())
        self.assertEqual(rules[0].pk, rule2.pk)
        self.assertEqual(rules[1].pk, rule1.pk)

    def test_mail_rule_cascade_delete(self):
        """Deleting the account cascades to its rules."""
        MailRule.objects.create(name="R1", account=self.account)
        MailRule.objects.create(name="R2", account=self.account)
        self.account.delete()
        self.assertEqual(MailRule.objects.count(), 0)

    def test_mail_rule_can_be_disabled(self):
        rule = MailRule.objects.create(
            name="Disabled",
            account=self.account,
            enabled=False,
        )
        self.assertFalse(rule.enabled)

    def test_mail_rule_maximum_age(self):
        rule = MailRule.objects.create(
            name="Old Mail",
            account=self.account,
            maximum_age=90,
        )
        self.assertEqual(rule.maximum_age, 90)
