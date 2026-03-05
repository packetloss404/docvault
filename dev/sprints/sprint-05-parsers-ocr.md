# Sprint 5: Parsers & OCR

## Phase: 2 - Document Processing
## Duration: 2 weeks
## Prerequisites: Sprint 4 (Storage & Upload Pipeline)

---

## Sprint Goal
Build the complete parser system for all major document formats and integrate OCRmyPDF for text extraction and searchable PDF generation. Implement language detection and date extraction from document content.

---

## Context for Agents

### Read Before Starting
- `/doc/architecture.md` - Section 4 (Processing Pipeline)
- `/doc/product-spec.md` - Section 2.3 (Processing Module - Parsers)
- `/doc/research/paperless-ngx-analysis.md` - Section 4 (Document Processing Pipeline) for parser patterns
- Sprint 4 established the plugin system - parsers integrate as a plugin

### Key Design Decisions
1. **OCRmyPDF** (not raw Tesseract) - better PDF output, handles PDF/A, skip/redo/force modes
2. **Parser registry pattern** from Mayan - route by MIME type
3. **ParserPlugin** wraps the parser system as a processing plugin
4. **Each parser produces**: extracted text, archive file path (searchable PDF), page count
5. **LibreOffice/Tika for Office docs** - convert to PDF first, then OCR

---

## Tasks

### Task 5.1: Parser Base Class & Registry
**Priority**: Critical
**Estimated Effort**: 4 hours

```python
# processing/parsers/base.py
class DocumentParser(ABC):
    """Base class for format-specific document parsers."""

    # MIME types this parser handles
    supported_mime_types: list[str] = []

    @abstractmethod
    def parse(self, source_path: Path, mime_type: str,
              language: str = 'eng') -> ParseResult:
        """Parse document and extract content."""

    def get_thumbnail(self, source_path: Path, page: int = 1) -> Path | None:
        """Generate thumbnail for first page. Override if supported."""
        return None


@dataclass
class ParseResult:
    content: str = ""              # Extracted text
    archive_path: Path = None      # Searchable PDF path
    page_count: int = 0
    metadata: dict = field(default_factory=dict)  # Extracted metadata
    date: date = None              # Detected document date


# Parser registry
_parser_registry: dict[str, list[type[DocumentParser]]] = {}

def register_parser(parser_class: type[DocumentParser]):
    for mime_type in parser_class.supported_mime_types:
        _parser_registry.setdefault(mime_type, []).append(parser_class)

def get_parser_for_mime_type(mime_type: str) -> DocumentParser | None:
    parsers = _parser_registry.get(mime_type, [])
    if parsers:
        return parsers[0]()  # Return first registered parser
    return None
```

```python
# processing/plugins/parser.py
class ParserPlugin(ProcessingPlugin):
    name = "Parser"
    order = 50

    def can_run(self, context):
        return context.mime_type and get_parser_for_mime_type(context.mime_type)

    def process(self, context):
        parser = get_parser_for_mime_type(context.mime_type)
        if not parser:
            return PluginResult(success=False,
                              message=f"No parser for {context.mime_type}")

        result = parser.parse(context.source_path, context.mime_type,
                            context.language or 'eng')
        context.content = result.content
        context.archive_path = result.archive_path
        context.page_count = result.page_count
        if result.date:
            context.date_created = result.date

        self.send_progress(context, 0.5, f"Parsed {context.original_filename}")
        return PluginResult(success=True)
```

**Acceptance Criteria**:
- Parser base class defines interface
- Registry maps MIME types to parsers
- ParserPlugin integrates with processing pipeline
- Unknown MIME types handled gracefully

### Task 5.2: PDF Parser (OCRmyPDF)
**Priority**: Critical
**Estimated Effort**: 8 hours

```python
# processing/parsers/pdf.py
class PDFParser(DocumentParser):
    supported_mime_types = ['application/pdf']

    def parse(self, source_path, mime_type, language='eng'):
        # 1. Run OCRmyPDF to create searchable PDF
        archive_path = self._run_ocrmypdf(source_path, language)

        # 2. Extract text from the result
        content = self._extract_text(archive_path or source_path)

        # 3. Get page count
        page_count = self._get_page_count(source_path)

        return ParseResult(
            content=content,
            archive_path=archive_path,
            page_count=page_count,
        )

    def _run_ocrmypdf(self, source_path, language):
        """Run OCRmyPDF with configured settings."""
        import ocrmypdf
        archive_path = Path(tempfile.mkdtemp()) / f"{source_path.stem}.pdf"

        ocr_config = get_ocr_config()
        try:
            ocrmypdf.ocr(
                input_file=source_path,
                output_file=archive_path,
                language=language,
                skip_text=ocr_config.mode == 'skip',
                redo_ocr=ocr_config.mode == 'redo',
                force_ocr=ocr_config.mode == 'force',
                output_type=ocr_config.output_type,  # 'pdfa' or 'pdf'
                deskew=ocr_config.deskew,
                rotate_pages=ocr_config.rotate,
                clean=ocr_config.clean != 'none',
                clean_final=ocr_config.clean == 'finalize',
                image_dpi=ocr_config.image_dpi,
                jobs=2,  # Parallel OCR threads
            )
            return archive_path
        except ocrmypdf.exceptions.PriorOcrFoundError:
            # PDF already has text, just copy it
            shutil.copy(source_path, archive_path)
            return archive_path

    def _extract_text(self, pdf_path):
        """Extract text from PDF using pikepdf or pdftotext."""
        # Use pikepdf for text extraction
        import pikepdf
        text_parts = []
        with pikepdf.open(pdf_path) as pdf:
            for page in pdf.pages:
                text_parts.append(page.extract_text() or '')
        return '\n'.join(text_parts)

    def _get_page_count(self, pdf_path):
        import pikepdf
        with pikepdf.open(pdf_path) as pdf:
            return len(pdf.pages)
```

OCR configuration:
```python
# processing/config.py
@dataclass
class OCRConfig:
    language: str = 'eng'
    mode: str = 'skip'  # 'skip', 'redo', 'force'
    output_type: str = 'pdfa'
    image_dpi: int = 300
    deskew: bool = True
    rotate: bool = True
    clean: str = 'clean'  # 'none', 'clean', 'finalize'
    max_image_pixels: float = 256_000_000
    pages: int = 0  # 0 = all pages

def get_ocr_config() -> OCRConfig:
    return OCRConfig(
        language=settings.OCR_LANGUAGE,
        mode=settings.OCR_MODE,
        # ... from environment
    )
```

**Acceptance Criteria**:
- PDFs processed with OCRmyPDF
- Text extracted from both text-based and scanned PDFs
- Searchable PDF/A generated as archive
- OCR mode configurable (skip/redo/force)
- Language configurable
- Page count extracted
- Handles PDFs with existing OCR (PriorOcrFoundError)
- Unit tests with sample PDFs

### Task 5.3: Image Parser
**Priority**: High
**Estimated Effort**: 4 hours

```python
# processing/parsers/image.py
class ImageParser(DocumentParser):
    supported_mime_types = [
        'image/jpeg', 'image/png', 'image/tiff',
        'image/webp', 'image/bmp', 'image/gif',
    ]

    def parse(self, source_path, mime_type, language='eng'):
        # Convert image to PDF, then OCR
        pdf_path = self._image_to_pdf(source_path)
        pdf_parser = PDFParser()
        result = pdf_parser.parse(pdf_path, 'application/pdf', language)
        result.page_count = 1
        return result

    def _image_to_pdf(self, image_path):
        """Convert image to PDF using Pillow."""
        from PIL import Image
        pdf_path = Path(tempfile.mkdtemp()) / f"{image_path.stem}.pdf"
        img = Image.open(image_path)
        if img.mode != 'RGB':
            img = img.convert('RGB')
        img.save(pdf_path, 'PDF')
        return pdf_path
```

**Acceptance Criteria**:
- JPEG, PNG, TIFF, WebP images parsed via OCR
- Images converted to PDF, then OCRmyPDF processes them
- Text extracted from scanned documents as images
- Page count = 1 for single images

### Task 5.4: Office Document Parser
**Priority**: High
**Estimated Effort**: 6 hours

```python
# processing/parsers/office.py
class OfficeParser(DocumentParser):
    supported_mime_types = [
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',  # docx
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',  # xlsx
        'application/vnd.openxmlformats-officedocument.presentationml.presentation',  # pptx
        'application/msword',  # doc
        'application/vnd.ms-excel',  # xls
        'application/vnd.ms-powerpoint',  # ppt
        'application/vnd.oasis.opendocument.text',  # odt
        'application/vnd.oasis.opendocument.spreadsheet',  # ods
        'application/rtf',
    ]

    def parse(self, source_path, mime_type, language='eng'):
        # Strategy 1: Try Gotenberg/Tika for conversion
        # Strategy 2: Fall back to LibreOffice subprocess
        pdf_path = self._convert_to_pdf(source_path)
        if pdf_path:
            pdf_parser = PDFParser()
            return pdf_parser.parse(pdf_path, 'application/pdf', language)
        else:
            # Direct text extraction as fallback
            content = self._extract_text_directly(source_path, mime_type)
            return ParseResult(content=content, page_count=1)

    def _convert_to_pdf(self, source_path):
        """Convert Office document to PDF via LibreOffice."""
        output_dir = Path(tempfile.mkdtemp())
        try:
            subprocess.run([
                'libreoffice', '--headless', '--convert-to', 'pdf',
                '--outdir', str(output_dir), str(source_path)
            ], check=True, timeout=120, capture_output=True)
            pdf_files = list(output_dir.glob('*.pdf'))
            return pdf_files[0] if pdf_files else None
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            return None
```

**Acceptance Criteria**:
- DOCX, XLSX, PPTX, DOC, XLS, PPT, ODT, ODS, RTF supported
- Office documents converted to PDF via LibreOffice
- Text extracted from converted PDFs
- Fallback to direct text extraction if conversion fails
- Timeout handling for LibreOffice

### Task 5.5: Text & Email Parsers
**Priority**: Medium
**Estimated Effort**: 4 hours

```python
# processing/parsers/text.py
class TextParser(DocumentParser):
    supported_mime_types = [
        'text/plain', 'text/html', 'text/csv',
        'text/markdown', 'text/xml', 'application/json',
    ]

    def parse(self, source_path, mime_type, language='eng'):
        content = source_path.read_text(encoding='utf-8', errors='replace')
        if mime_type == 'text/html':
            content = self._strip_html(content)
        return ParseResult(content=content, page_count=1)


# processing/parsers/email_parser.py
class EmailParser(DocumentParser):
    supported_mime_types = [
        'message/rfc822',  # .eml
        'application/vnd.ms-outlook',  # .msg
    ]

    def parse(self, source_path, mime_type, language='eng'):
        if mime_type == 'application/vnd.ms-outlook':
            return self._parse_msg(source_path)
        return self._parse_eml(source_path)

    def _parse_eml(self, source_path):
        import email
        with open(source_path, 'rb') as f:
            msg = email.message_from_binary_file(f)
        subject = msg.get('Subject', '')
        from_addr = msg.get('From', '')
        body = self._get_body(msg)
        content = f"From: {from_addr}\nSubject: {subject}\n\n{body}"
        return ParseResult(content=content, page_count=1,
                          metadata={'from': from_addr, 'subject': subject})
```

**Acceptance Criteria**:
- Plain text, HTML, CSV, Markdown parsed
- HTML tags stripped for plain text content
- EML and MSG email files parsed
- Email metadata extracted (from, subject, date)

### Task 5.6: Language Detection & Date Extraction
**Priority**: Medium
**Estimated Effort**: 4 hours

```python
# processing/plugins/language.py
class LanguageDetectionPlugin(ProcessingPlugin):
    name = "LanguageDetection"
    order = 80

    def can_run(self, context):
        return bool(context.content) and not context.language

    def process(self, context):
        from langdetect import detect
        try:
            context.language = detect(context.content[:5000])
        except:
            context.language = 'en'
        return PluginResult(success=True)


# processing/plugins/date_extraction.py
class DateExtractionPlugin(ProcessingPlugin):
    name = "DateExtraction"
    order = 90

    def can_run(self, context):
        return bool(context.content) and not context.date_created

    def process(self, context):
        # Try to extract date from first few lines of content
        import dateparser
        # Look for date patterns in first 1000 chars
        for line in context.content[:1000].splitlines():
            parsed = dateparser.parse(line, settings={
                'PREFER_DATES_FROM': 'past',
                'REQUIRE_PARTS': ['day', 'month', 'year'],
            })
            if parsed:
                context.date_created = parsed.date()
                break
        if not context.date_created:
            context.date_created = date.today()
        return PluginResult(success=True)
```

**Acceptance Criteria**:
- Language auto-detected from document content
- Date extracted from document content when possible
- Falls back to current date if no date found
- Language detection uses first 5000 chars (performance)

### Task 5.7: Register All Parsers & Integration Test
**Priority**: High
**Estimated Effort**: 4 hours

Register all parsers in app initialization:
```python
# processing/apps.py
class ProcessingConfig(AppConfig):
    def ready(self):
        from .parsers.pdf import PDFParser
        from .parsers.image import ImageParser
        from .parsers.office import OfficeParser
        from .parsers.text import TextParser
        from .parsers.email_parser import EmailParser
        from .parsers.base import register_parser

        register_parser(PDFParser)
        register_parser(ImageParser)
        register_parser(OfficeParser)
        register_parser(TextParser)
        register_parser(EmailParser)
```

Update DocumentConsumer plugin list:
```python
plugins = [
    PreflightPlugin,         # Order 10
    ParserPlugin,            # Order 50
    LanguageDetectionPlugin, # Order 80
    DateExtractionPlugin,    # Order 90
]
```

Integration test: Upload a PDF via API, verify text extracted, archive created, language detected, date extracted, document saved to database.

**Acceptance Criteria**:
- All parsers registered on app startup
- End-to-end test: upload PDF -> OCR -> text extraction -> document created
- End-to-end test: upload image -> OCR -> text extraction
- End-to-end test: upload DOCX -> conversion -> text extraction
- All tests pass

---

## Dependencies

### New Python Packages
```
ocrmypdf>=16.0
pikepdf>=9.0
Pillow>=12.0
python-magic>=0.4
langdetect>=1.0
dateparser>=1.3
extract-msg>=0.55
```

### System Dependencies (Docker)
```
tesseract-ocr
tesseract-ocr-eng
libreoffice-writer
libreoffice-calc
libreoffice-impress
ghostscript
unpaper
libmagic1
```

---

## Definition of Done
- [ ] PDF parser extracts text and creates searchable PDF/A
- [ ] Image parser OCRs images (JPEG, PNG, TIFF)
- [ ] Office parser converts and extracts text (DOCX, XLSX, PPTX)
- [ ] Text parser handles plain text, HTML, CSV
- [ ] Email parser extracts content from EML and MSG
- [ ] Language auto-detected from content
- [ ] Date extracted from content when possible
- [ ] All parsers registered and routed by MIME type
- [ ] End-to-end integration tests pass
- [ ] OCR configuration (mode, language, DPI) works via env vars
- [ ] `python manage.py test` passes
