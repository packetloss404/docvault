"""Authenticated PDF page images for browsers that block embedded PDF viewers."""

from django.http import Http404, HttpResponse
from rest_framework.exceptions import ValidationError


def build_pdf_page_preview(document, page_number):
    import pymupdf

    from storage.utils import get_storage_backend

    try:
        page_number = int(page_number)
    except (TypeError, ValueError):
        raise ValidationError({"page": "Use a positive page number."})
    if page_number < 1:
        raise ValidationError({"page": "Use a positive page number."})

    if document.archive_filename:
        storage_name = document.archive_filename
    elif document.mime_type == "application/pdf":
        storage_name = document.filename
    else:
        raise Http404("No PDF preview available.")

    backend = get_storage_backend()
    if not storage_name or not backend.exists(storage_name):
        raise Http404("PDF file not found.")
    with backend.open(storage_name) as source:
        data = source.read()
    try:
        pdf = pymupdf.open(stream=data, filetype="pdf")
    except (RuntimeError, ValueError):
        raise Http404("PDF preview is unavailable.")
    with pdf:
        if pdf.needs_pass:
            raise Http404("Encrypted PDF preview is unavailable.")
        if page_number > len(pdf):
            raise Http404("Page not found.")
        page = pdf[page_number - 1]
        if page.rect.width <= 0 or page.rect.height <= 0:
            raise Http404("Page has no visible area.")
        # Bound the raster size even for PDFs with unusually large page boxes.
        scale = min(1600 / page.rect.width, 2000 / page.rect.height)
        image = page.get_pixmap(matrix=pymupdf.Matrix(scale, scale), alpha=False)
        response = HttpResponse(image.tobytes("png"), content_type="image/png")
    response["Cache-Control"] = "private, no-store"
    return response
