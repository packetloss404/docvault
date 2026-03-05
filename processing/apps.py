"""Processing app configuration."""

from django.apps import AppConfig


class ProcessingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "processing"
    verbose_name = "Processing"

    def ready(self):
        from .parsers.base import register_parser
        from .parsers.email_parser import EmailParser
        from .parsers.image import ImageParser
        from .parsers.office import OfficeParser
        from .parsers.pdf import PDFParser
        from .parsers.text import TextParser

        register_parser(PDFParser)
        register_parser(ImageParser)
        register_parser(OfficeParser)
        register_parser(TextParser)
        register_parser(EmailParser)
