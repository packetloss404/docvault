import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIClient

from sources.models import Source


@pytest.mark.django_db
def test_admin_can_configure_source_without_disclosing_credentials():
    admin = User.objects.create_user('source-config-admin', is_staff=True)
    client = APIClient()
    client.force_authenticate(admin)
    response = client.post('/api/v1/sources/', {
        'label': 'S3 source', 'source_type': 's3', 'configuration': {
            'bucket': 'documents', 'aws_secret_access_key': 'private-test-value', 'use_storage_endpoint': True,
        },
    }, format='json')
    assert response.status_code == 201
    assert 'configuration' not in response.data
    source = Source.objects.get(pk=response.data['id'])
    assert source.configuration['aws_secret_access_key'] == 'private-test-value'
    assert 'private-test-value' not in client.get(f'/api/v1/sources/{source.pk}/').content.decode()


@pytest.mark.django_db
def test_api_configuration_cannot_supply_an_arbitrary_network_destination():
    admin = User.objects.create_user('unsafe-source-config-admin', is_staff=True)
    client = APIClient()
    client.force_authenticate(admin)
    response = client.post('/api/v1/sources/', {
        'label': 'Unsafe', 'source_type': 's3', 'configuration': {'endpoint_url': 'http://169.254.169.254/'},
    }, format='json')
    assert response.status_code == 400
    assert not Source.objects.exists()
