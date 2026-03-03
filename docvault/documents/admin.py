from django.contrib import admin

from .models import Document, DocumentFile, DocumentPage, DocumentType, DocumentVersion


class DocumentFileInline(admin.TabularInline):
    model = DocumentFile
    extra = 0
    readonly_fields = ["checksum", "size", "created_at"]


class DocumentVersionInline(admin.TabularInline):
    model = DocumentVersion
    extra = 0
    readonly_fields = ["created_at"]


class DocumentPageInline(admin.TabularInline):
    model = DocumentPage
    extra = 0


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ["title", "document_type", "created", "mime_type", "owner", "is_deleted"]
    list_filter = ["document_type", "mime_type", "created", "language"]
    search_fields = ["title", "content", "original_filename"]
    readonly_fields = ["uuid", "checksum", "archive_checksum", "created_at", "updated_at", "added"]
    inlines = [DocumentFileInline, DocumentVersionInline, DocumentPageInline]
    date_hierarchy = "created"

    def get_queryset(self, request):
        return self.model.all_objects.all()

    def is_deleted(self, obj):
        return obj.is_deleted

    is_deleted.boolean = True


@admin.register(DocumentType)
class DocumentTypeAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "matching_algorithm", "trash_time_period", "delete_time_period"]
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ["name"]


@admin.register(DocumentFile)
class DocumentFileAdmin(admin.ModelAdmin):
    list_display = ["document", "filename", "mime_type", "size", "created_at"]
    list_filter = ["mime_type"]
    search_fields = ["filename", "document__title"]
    readonly_fields = ["checksum", "created_at"]


@admin.register(DocumentVersion)
class DocumentVersionAdmin(admin.ModelAdmin):
    list_display = ["document", "version_number", "is_active", "created_at"]
    list_filter = ["is_active"]
    search_fields = ["document__title"]


@admin.register(DocumentPage)
class DocumentPageAdmin(admin.ModelAdmin):
    list_display = ["document", "page_number"]
    search_fields = ["document__title", "content"]
