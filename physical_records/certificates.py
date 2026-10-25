"""Generate a durable PDF record of an attested physical destruction."""

from io import BytesIO
from xml.sax.saxutils import escape

from django.core.files.base import ContentFile


def generate_destruction_certificate(certificate):
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

    buffer = BytesIO()
    styles = getSampleStyleSheet()
    story = [Paragraph("Certificate of Destruction", styles["Title"]), Spacer(1, 16)]
    record = certificate.physical_record
    entries = [
        ("Certificate", str(certificate.pk)),
        ("Document", record.document.title),
        ("Physical record", str(record.pk)),
        ("Barcode", record.barcode or ""),
        ("Destroyed at", certificate.destroyed_at.isoformat()),
        ("Attested by", certificate.destroyed_by.get_username()),
        ("Method", certificate.get_method_display()),
        ("Witness", certificate.witness),
        ("Notes", certificate.notes),
    ]
    for label, value in entries:
        story.append(Paragraph(f"<b>{label}:</b> {escape(value)}", styles["BodyText"]))
        story.append(Spacer(1, 8))
    SimpleDocTemplate(buffer).build(story)
    certificate.certificate_pdf.save(
        f"destruction_{certificate.pk}.pdf", ContentFile(buffer.getvalue()), save=True,
    )
