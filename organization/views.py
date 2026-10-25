"""Views for the organization module."""


from django.db import transaction
from drf_spectacular.utils import extend_schema
from mptt.exceptions import InvalidMove
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from documents.models import Document
from legal_hold.permissions import ensure_document_mutable
from security.permissions import (
    IsAdminOrReadOnly,
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
    CabinetMoveSerializer,
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
    ensure_document_mutable(document, view.request.user)


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

    @extend_schema(request=CabinetMoveSerializer, responses=CabinetSerializer)
    @action(detail=True, methods=["post"])
    @transaction.atomic
    def move(self, request, pk=None):
        """Move a cabinet relative to a target or to a legacy parent selection."""
        cabinet = self.get_object()
        serializer = CabinetMoveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        target = data.get("target", data.get("parent"))
        # MPTT moves can update siblings and ancestors beyond the source/target rows.
        list(Cabinet.objects.select_for_update().order_by("pk").values_list("pk", flat=True))
        cabinet.refresh_from_db()
        if target:
            target.refresh_from_db()
            if target.pk == cabinet.pk or target.is_descendant_of(cabinet):
                raise ValidationError("A cabinet cannot be moved inside its own subtree.")
        try:
            cabinet.move_to(target, position=data["position"])
        except (InvalidMove, ValueError) as exc:
            raise ValidationError(str(exc)) from exc
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

    @action(detail=False, methods=["get"])
    def autocomplete(self, request):
        paths = self.get_queryset().filter(name__icontains=request.query_params.get("q", ""))[:20]
        return Response([{"id": item.pk, "name": item.name} for item in paths])


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
        if getattr(self, "swagger_fake_view", False):
            return CustomFieldInstance.objects.none()
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
        ensure_document_mutable(serializer.instance.document, self.request.user)
        if "document" in serializer.validated_data:
            _validate_nested_document(self, serializer.validated_data["document"])
        serializer.save()

    def perform_destroy(self, instance):
        ensure_document_mutable(instance.document, self.request.user)
        instance.delete()


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
        if getattr(self, "swagger_fake_view", False):
            return DocumentMetadata.objects.none()
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
        ensure_document_mutable(serializer.instance.document, self.request.user)
        if "document" in serializer.validated_data:
            _validate_nested_document(self, serializer.validated_data["document"])
        serializer.save()

    def perform_destroy(self, instance):
        ensure_document_mutable(instance.document, self.request.user)
        instance.delete()


class DocumentTypeCustomFieldViewSet(viewsets.ModelViewSet):
    """Manage custom field assignments for a document type."""

    serializer_class = DocumentTypeCustomFieldSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrReadOnly]
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
    permission_classes = [permissions.IsAuthenticated, IsAdminOrReadOnly]
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

        for document in docs.filter(is_held=True):
            ensure_document_mutable(document, request.user)

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

        for document in docs.filter(is_held=True):
            ensure_document_mutable(document, request.user)

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
