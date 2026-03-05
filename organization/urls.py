"""URL configuration for the organization module."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r"tags", views.TagViewSet, basename="tag")
router.register(r"correspondents", views.CorrespondentViewSet, basename="correspondent")
router.register(r"cabinets", views.CabinetViewSet, basename="cabinet")
router.register(r"storage-paths", views.StoragePathViewSet, basename="storagepath")
router.register(r"custom-fields", views.CustomFieldViewSet, basename="customfield")
router.register(r"metadata-types", views.MetadataTypeViewSet, basename="metadatatype")
router.register(
    r"custom-field-instances",
    views.CustomFieldInstanceViewSet,
    basename="customfieldinstance",
)
router.register(
    r"document-metadata",
    views.DocumentMetadataViewSet,
    basename="documentmetadata",
)

# Nested routes under documents
doc_custom_fields = views.CustomFieldInstanceViewSet.as_view({
    "get": "list",
    "post": "create",
})
doc_custom_field_detail = views.CustomFieldInstanceViewSet.as_view({
    "get": "retrieve",
    "put": "update",
    "patch": "partial_update",
    "delete": "destroy",
})
doc_metadata = views.DocumentMetadataViewSet.as_view({
    "get": "list",
    "post": "create",
})
doc_metadata_detail = views.DocumentMetadataViewSet.as_view({
    "get": "retrieve",
    "put": "update",
    "patch": "partial_update",
    "delete": "destroy",
})

# Nested routes under document-types
dt_custom_fields = views.DocumentTypeCustomFieldViewSet.as_view({
    "get": "list",
    "post": "create",
})
dt_custom_field_detail = views.DocumentTypeCustomFieldViewSet.as_view({
    "get": "retrieve",
    "put": "update",
    "patch": "partial_update",
    "delete": "destroy",
})
dt_metadata = views.DocumentTypeMetadataViewSet.as_view({
    "get": "list",
    "post": "create",
})
dt_metadata_detail = views.DocumentTypeMetadataViewSet.as_view({
    "get": "retrieve",
    "put": "update",
    "patch": "partial_update",
    "delete": "destroy",
})

urlpatterns = [
    path("bulk-assign/", views.BulkAssignView.as_view({"post": "create"}), name="bulk-assign"),
    path(
        "bulk-set-custom-fields/",
        views.BulkSetCustomFieldsView.as_view({"post": "create"}),
        name="bulk-set-custom-fields",
    ),
    # Nested document custom fields
    path(
        "documents/<int:document_pk>/custom-fields/",
        doc_custom_fields,
        name="document-custom-fields-list",
    ),
    path(
        "documents/<int:document_pk>/custom-fields/<int:pk>/",
        doc_custom_field_detail,
        name="document-custom-fields-detail",
    ),
    # Nested document metadata
    path(
        "documents/<int:document_pk>/metadata/",
        doc_metadata,
        name="document-metadata-list",
    ),
    path(
        "documents/<int:document_pk>/metadata/<int:pk>/",
        doc_metadata_detail,
        name="document-metadata-detail",
    ),
    # Nested document-type custom field assignments
    path(
        "document-types/<int:document_type_pk>/custom-fields/",
        dt_custom_fields,
        name="doctype-custom-fields-list",
    ),
    path(
        "document-types/<int:document_type_pk>/custom-fields/<int:pk>/",
        dt_custom_field_detail,
        name="doctype-custom-fields-detail",
    ),
    # Nested document-type metadata assignments
    path(
        "document-types/<int:document_type_pk>/metadata-types/",
        dt_metadata,
        name="doctype-metadata-list",
    ),
    path(
        "document-types/<int:document_type_pk>/metadata-types/<int:pk>/",
        dt_metadata_detail,
        name="doctype-metadata-detail",
    ),
    path("", include(router.urls)),
]
