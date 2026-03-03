"""Constants for the sources module."""

# Source types
SOURCE_WATCH_FOLDER = "watch_folder"
SOURCE_EMAIL = "email"
SOURCE_STAGING = "staging"
SOURCE_S3 = "s3"
SOURCE_SCANNER = "scanner"

SOURCE_TYPE_CHOICES = [
    (SOURCE_WATCH_FOLDER, "Watch Folder"),
    (SOURCE_EMAIL, "Email (IMAP)"),
    (SOURCE_STAGING, "Staging Folder"),
    (SOURCE_S3, "S3 Bucket"),
    (SOURCE_SCANNER, "SANE Scanner"),
]

# Scanner color modes
SCAN_COLOR = "color"
SCAN_GRAY = "gray"
SCAN_LINEART = "lineart"

SCAN_COLOR_CHOICES = [
    (SCAN_COLOR, "Color"),
    (SCAN_GRAY, "Grayscale"),
    (SCAN_LINEART, "Black & White"),
]

# Scanner paper sizes
PAPER_A4 = "a4"
PAPER_LETTER = "letter"
PAPER_LEGAL = "legal"
PAPER_AUTO = "auto"

PAPER_SIZE_CHOICES = [
    (PAPER_A4, "A4"),
    (PAPER_LETTER, "Letter"),
    (PAPER_LEGAL, "Legal"),
    (PAPER_AUTO, "Auto-detect"),
]

# Mail security types
MAIL_SECURITY_NONE = "none"
MAIL_SECURITY_SSL = "ssl"
MAIL_SECURITY_STARTTLS = "starttls"

MAIL_SECURITY_CHOICES = [
    (MAIL_SECURITY_NONE, "None"),
    (MAIL_SECURITY_SSL, "SSL"),
    (MAIL_SECURITY_STARTTLS, "STARTTLS"),
]

# Mail account types
MAIL_ACCOUNT_IMAP = "imap"
MAIL_ACCOUNT_GMAIL_OAUTH = "gmail_oauth"
MAIL_ACCOUNT_OUTLOOK_OAUTH = "outlook_oauth"

MAIL_ACCOUNT_TYPE_CHOICES = [
    (MAIL_ACCOUNT_IMAP, "IMAP"),
    (MAIL_ACCOUNT_GMAIL_OAUTH, "Gmail OAuth2"),
    (MAIL_ACCOUNT_OUTLOOK_OAUTH, "Outlook OAuth2"),
]

# Mail rule actions
MAIL_ACTION_DOWNLOAD_ATTACHMENT = "download_attachment"
MAIL_ACTION_PROCESS_EMAIL = "process_email"

MAIL_ACTION_CHOICES = [
    (MAIL_ACTION_DOWNLOAD_ATTACHMENT, "Download Attachments"),
    (MAIL_ACTION_PROCESS_EMAIL, "Process Entire Email"),
]

# Post-processing actions for consumed files
CONSUMED_ACTION_DELETE = "delete"
CONSUMED_ACTION_MOVE = "move"
CONSUMED_ACTION_NOTHING = "nothing"

CONSUMED_ACTION_CHOICES = [
    (CONSUMED_ACTION_DELETE, "Delete file"),
    (CONSUMED_ACTION_MOVE, "Move to consumed directory"),
    (CONSUMED_ACTION_NOTHING, "Do nothing"),
]

# Post-processing for email
MAIL_PROCESSED_READ = "mark_read"
MAIL_PROCESSED_MOVE = "move_to_folder"
MAIL_PROCESSED_DELETE = "delete"
MAIL_PROCESSED_FLAG = "flag"

MAIL_PROCESSED_CHOICES = [
    (MAIL_PROCESSED_READ, "Mark as Read"),
    (MAIL_PROCESSED_MOVE, "Move to Folder"),
    (MAIL_PROCESSED_DELETE, "Delete"),
    (MAIL_PROCESSED_FLAG, "Flag/Star"),
]
