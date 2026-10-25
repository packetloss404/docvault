from io import BytesIO

import pytest
from django.contrib.auth.models import User
from PIL import Image
from rest_framework.test import APIClient

from documents.models import Document
from processing.barcode_utils import extract_asn, scan_page_for_barcodes


@pytest.mark.django_db
def test_printed_asn_label_is_decodable_by_the_actual_ingestion_scanner():
    user = User.objects.create_user('label-roundtrip-owner')
    document = Document.objects.create(title='Label', owner=user, archive_serial_number=985612)
    client = APIClient()
    client.force_authenticate(user)
    response = client.get(f'/api/v1/documents/{document.pk}/barcode-label/')
    assert response.status_code == 200
    barcodes = scan_page_for_barcodes(Image.open(BytesIO(response.content)))
    assert extract_asn({0: barcodes}) == document.archive_serial_number
