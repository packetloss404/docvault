"""Views for the organization module."""


from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from documents.models import Document
from security.permissions import (
    get_document_for_user,
    get_objects_for_user_with_ownership,
)

from .models import (
    Cabinet,
    Correspondent,
    CustomField,
    CustomFieldInstance,
    DocumentMetadata,
    DocumentTypeCustomField,
    DocumentTypeMetadata,
    MetadataType,
    StoragePath,
    Tag,
)
from .serializers import (
    BulkAssignSerializer,
    BulkSetCustomFieldsSerializer,
    CabinetSerializer,
    CabinetTreeSerializer,
    CorrespondentSerializer,
    CustomFieldInstanceSerializer,
    CustomFieldInstanceWriteSerializer,
    CustomFieldSerializer,
    DocumentMetadataSerializer,
    DocumentTypeCustomFieldSerializer,
    DocumentTypeMetadataSerializer,
    MetadataTypeSerializer,
    StoragePathSerializer,
    TagSerializer,
    TagTreeSerializer,
)


def _document_action_for_viewset_action(action):
    return "change" if action in {"create", "update", "partial_update", "destroy"} else "view"


def _permitted_documents(user, action="view"):
    return get_objects_for_user_with_ownership(
        user,
        f"documents.{action}_document",
        Document.objects.all(),
    )


def _validate_nested_document(view, document):
    document_pk = view.kwargs.get("document_pk")
    if document_pk is not None and document.pk != int(document_pk):
        raise ValidationError({"document": "Document does not match the URL."})
    get_document_for_user(view.request.user, document.pk, action="change")


class TagViewSet(viewsets.ModelViewSet):
    """CRUD operations for Tags with hierarchy support."""

    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = [permissions.IsAuthenticated]
    search_fields = ["name"]
    ordering_fields = ["name", "created_at"]
    ordering = ["tree_id", "lft"]

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    @action(detail=False, methods=["get"])
    def tree(self, request):
        """Get tags as a nested tree structure."""
        roots = Tag.objects.root_nodes()
        serializer = TagTreeSerializer(roots, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def autocomplete(self, request):
        """Autocomplete endpoint for tag search."""
        q = request.query_params.get("q", "")
        tags = Tag.objects.filter(name__icontains=q)[:20]
        return Response([
            {"id": t.id, "name": t.name, "color": t.color}
            for t in tags
        ])


class CorrespondentViewSet(viewsets.ModelViewSet):
    """CRUD operations for Correspondents."""

    queryset = Correspondent.objects.all()
    serializer_class = CorrespondentSerializer
    permission_classes = [permissions.IsAuthenticated]
    search_fields = ["name"]
    ordering_fields = ["name", "created_at"]
    ordering = ["name"]

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    @action(detail=False, methods=["get"])
    def autocomplete(self, request):
        """Autocomplete endpoint for correspondent search."""
        q = request.query_params.get("q", "")
        correspondents = Correspondent.objects.filter(name__icontains=q)[:20]
        return Response([
            {"id": c.id, "name": c.name}
            for c in correspondents
        ])


class CabinetViewSet(viewsets.ModelViewSet):
    """CRUD operations for Cabinets with hierarchy support."""

    queryset = Cabinet.objects.all()
    serializer_class = CabinetSerializer
    permission_classes = [permissions.IsAuthenticated]
    search_fields = ["name"]
    ordering_fields = ["name", "created_at"]
    ordering = ["tree_id", "lft"]

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    @action(detail=False, methods=["get"])
    def tree(self, request):
        """Get cabinets as a nested tree structure."""
        roots = Cabinet.objects.root_nodes()
        serializer = CabinetTreeSerializer(roots, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def move(self, request, pk=None):
        """Move a cabinet to a new parent."""
        cabinet = self.get_object()
        parent_id = request.data.get("parent")
        if parent_id:
            parent = Cabinet.objects.get(pk=parent_id)
            cabinet.move_to(parent, position="last-child")
        else:
            cabinet.move_to(None, position="last-child")
        cabinet.refresh_from_db()
        return Response(CabinetSerializer(cabinet).data)

    @action(detail=False, methods=["get"])
    def autocomplete(self, request):
        """Autocomplete endpoint for cabinet search."""
        q = request.query_params.get("q", "")
        cabinets = Cabinet.objects.filter(name__icontains=q)[:20]
        return Response([
            {"id": c.id, "name": c.name}
            for c in cabinets
        ])


class StoragePathViewSet(viewsets.ModelViewSet):
    """CRUD operations for StoragePaths."""

    queryset = StoragePath.objects.all()
    serializer_class = StoragePathSerializer
    permission_classes = [permissions.IsAuthenticated]
    search_fields = ["name"]
    ordering_fields = ["name", "created_at"]
    ordering = ["name"]

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class CustomFieldViewSet(viewsets.ModelViewSet):
    """CRUD operations for CustomField definitions."""

    queryset = CustomField.objects.all()
    serializer_class = CustomFieldSerializer
    permission_classes = [permissions.IsAuthenticated]
    search_fields = ["name"]
    ordering_fields = ["name", "created_at"]
    ordering = ["name"]

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class CustomFieldInstanceViewSet(viewsets.ModelViewSet):
    """
    Per-document custom field values.

    Nested under documents: /api/v1/documents/{doc_id}/custom-fields/
    Also available flat: /api/v1/custom-field-instances/
    """

    permission_classes = [permissions.IsAuthenticated]
    pagination_class = None
    ordering = ["field__name"]

    def get_queryset(self):
        action = _document_action_for_viewset_action(self.action)
        qs = CustomFieldInstance.objects.select_related("field", "document")
        doc_id = self.kwargs.get("document_pk")
        if doc_id:
            document = get_document_for_user(self.request.user, doc_id, action=action)
            return qs.filter(document=document)
        return qs.filter(document__in=_permitted_documents(self.request.user, action=action))

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return CustomFieldInstanceWriteSerializer
        return CustomFieldInstanceSerializer

    def perform_create(self, serializer):
        _validate_nested_document(self, serializer.validated_data["document"])
        serializer.save()

    def perform_update(self, serializer):
        if "document" in serializer.validated_data:
            _validate_nested_document(self, serializer.validated_data["document"])
        serializer.save()


class MetadataTypeViewSet(viewsets.ModelViewSet):
    """CRUD operations for MetadataType definitions."""

    queryset = MetadataType.objects.all()
    serializer_class = MetadataTypeSerializer
    permission_classes = [permissions.IsAuthenticated]
    search_fields = ["name", "label"]
    ordering_fields = ["name", "created_at"]
    ordering = ["name"]

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    @action(detail=True, methods=["get"], url_path="lookup-options")
    def lookup_options(self, request, pk=None):
        """Render the lookup template and return available options."""
        mt = self.get_object()
        options = mt.render_lookup()
        return Response({"options": options})


class DocumentMetadataViewSet(viewsets.ModelViewSet):
    """
    Per-document metadata values.

    Nested under documents: /api/v1/documents/{doc_id}/metadata/
    Also available flat: /api/v1/document-metadata/
    """

    serializer_class = DocumentMetadataSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = None
    ordering = ["metadata_type__name"]

    def get_queryset(self):
        action = _document_action_for_viewset_action(self.action)
        qs = DocumentMetadata.objects.select_related("metadata_type", "document")
        doc_id = self.kwargs.get("document_pk")
        if doc_id:
            document = get_document_for_user(self.request.user, doc_id, action=action)
            return qs.filter(document=document)
        return qs.filter(document__in=_permitted_documents(self.request.user, action=action))

    def perform_create(self, serializer):
        _validate_nested_document(self, serializer.validated_data["document"])
        serializer.save()

    def perform_update(self, serializer):
        if "document" in serializer.validated_data:
            _validate_nested_document(self, serializer.validated_data["document"])
        serializer.save()


class DocumentTypeCustomFieldViewSet(viewsets.ModelViewSet):
    """Manage custom field assignments for a document type."""

    serializer_class = DocumentTypeCustomFieldSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        qs = DocumentTypeCustomField.objects.select_related("custom_field")
        dt_id = self.kwargs.get("document_type_pk")
        if dt_id:
            qs = qs.filter(document_type_id=dt_id)
        return qs


class DocumentTypeMetadataViewSet(viewsets.ModelViewSet):
    """Manage metadata type assignments for a document type."""

    serializer_class = DocumentTypeMetadataSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        qs = DocumentTypeMetadata.objects.select_related("metadata_type")
        dt_id = self.kwargs.get("document_type_pk")
        if dt_id:
            qs = qs.filter(document_type_id=dt_id)
        return qs


class BulkSetCustomFieldsView(viewsets.ViewSet):
    """Bulk set a custom field value on multiple documents."""

    permission_classes = [permissions.IsAuthenticated]

    def create(self, request):
        serializer = BulkSetCustomFieldsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        document_ids = set(data["document_ids"])
        docs = get_objects_for_user_with_ownership(
            request.user,
            "documents.change_document",
            Document.objects.filter(pk__in=document_ids),
        )
        if docs.count() != len(document_ids):
            return Response(
                {"error": "One or more documents were not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            field = CustomField.objects.get(pk=data["field_id"])
        except CustomField.DoesNotExist:
            return Response(
                {"error": "Custom field not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        updated = 0
        for doc in docs:
            instance, _ = CustomFieldInstance.objects.get_or_create(
                document=doc, field=field,
            )
            instance.value = data["value"]
            instance.save()
            updated += 1

        return Response({"updated": updated})


class BulkAssignView(viewsets.ViewSet):
    """Bulk assign tags, correspondent, or cabinet to multiple documents."""

    permission_classes = [permissions.IsAuthenticated]

    def create(self, request):
        serializer = BulkAssignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        document_ids = set(data["document_ids"])
        docs = get_objects_for_user_with_ownership(
            request.user,
            "documents.change_document",
            Document.objects.filter(pk__in=document_ids),
        )
        if docs.count() != len(document_ids):
            return Response(
                {"error": "One or more documents were not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Add tags
        if data.get("tag_ids"):
            tags = Tag.objects.filter(pk__in=data["tag_ids"])
            for doc in docs:
                doc.tags.add(*tags)

        # Remove tags
        if data.get("remove_tag_ids"):
            remove_tags = Tag.objects.filter(pk__in=data["remove_tag_ids"])
            for doc in docs:
                doc.tags.remove(*remove_tags)

        # Set correspondent
        if "correspondent_id" in request.data:
            corr_id = data.get("correspondent_id")
            docs.update(correspondent_id=corr_id)

        # Set cabinet
        if "cabinet_id" in request.data:
            cab_id = data.get("cabinet_id")
            docs.update(cabinet_id=cab_id)

        return Response({"updated": docs.count()})
