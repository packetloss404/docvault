# Sprint 3: REST API Foundation & Frontend Scaffold

## Phase: 1 - Foundation
## Duration: 2 weeks
## Prerequisites: Sprint 2 (Authentication & Permissions)

---

## Sprint Goal
Complete the DRF API foundation with proper pagination, filtering, throttling, and OpenAPI docs. Initialize the Angular frontend with routing, auth guards, login page, and basic navigation layout.

---

## Context for Agents

### Read Before Starting
- `/doc/architecture.md` - Section 2 (Django App Structure) and Section 3 (Data Model)
- `/doc/product-spec.md` - Section 3 (API Specification) and Section 4 (UI/UX)
- `/doc/research/paperless-ngx-analysis.md` - Section 17 (API Capabilities) for API patterns

### Key Design Decisions
1. **DRF configuration follows Paperless-ngx patterns** - proven approach
2. **OpenAPI 3.0 via drf-spectacular** - auto-generated, always up-to-date
3. **Angular 21+ with standalone components** - modern Angular best practices
4. **Frontend served by Django in production** - no separate web server needed

---

## Tasks

### Task 3.1: DRF Configuration
**Priority**: Critical
**Estimated Effort**: 4 hours

Configure DRF in `docvault/settings/base.py`:
```python
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.TokenAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'core.pagination.StandardPagination',
    'PAGE_SIZE': 25,
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.OrderingFilter',
        'rest_framework.filters.SearchFilter',
    ],
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '20/minute',
        'user': '120/minute',
    },
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'DocVault API',
    'DESCRIPTION': 'Document Management System API',
    'VERSION': '1.0.0',
}
```

Create `core/pagination.py`:
```python
class StandardPagination(PageNumberPagination):
    page_size = 25
    page_size_query_param = 'page_size'
    max_page_size = 100
```

**Acceptance Criteria**:
- Pagination works on all list endpoints (25 default, configurable)
- Rate limiting enforced (20/min anon, 120/min auth)
- Filter backends available on all ViewSets
- OpenAPI schema generates correctly at `/api/schema/`
- Swagger UI available at `/api/docs/`

### Task 3.2: Document API ViewSets
**Priority**: Critical
**Estimated Effort**: 8 hours

Create `documents/views.py`:
```python
class DocumentViewSet(ModelViewSet):
    queryset = Document.objects.all()
    serializer_class = DocumentSerializer
    permission_classes = [IsAuthenticated, DocVaultObjectPermissions]
    filter_backends = [DjangoFilterBackend, OrderingFilter, SearchFilter,
                      ObjectPermissionsFilter]
    filterset_class = DocumentFilterSet
    search_fields = ['title', 'content', 'original_filename']
    ordering_fields = ['title', 'created', 'added', 'archive_serial_number']
    ordering = ['-created']

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user,
                       created_by=self.request.user)

    def perform_destroy(self, instance):
        instance.soft_delete()  # Soft delete, not hard delete

    @action(detail=True, methods=['post'])
    def restore(self, request, pk=None):
        """Restore a soft-deleted document."""
        doc = self.get_object()
        doc.restore()
        return Response(DocumentSerializer(doc).data)


class DocumentTypeViewSet(ModelViewSet):
    queryset = DocumentType.objects.all()
    serializer_class = DocumentTypeSerializer
    permission_classes = [IsAuthenticated]
    search_fields = ['name']
    ordering = ['name']
```

Create `documents/serializers.py`:
```python
class DocumentSerializer(ModelSerializer):
    class Meta:
        model = Document
        fields = [
            'id', 'uuid', 'title', 'content', 'document_type',
            'correspondent', 'storage_path', 'tags',
            'original_filename', 'mime_type', 'checksum',
            'page_count', 'filename', 'archive_filename',
            'created', 'added', 'archive_serial_number',
            'language', 'version_label', 'owner',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'uuid', 'checksum', 'created_at', 'updated_at']

class DocumentTypeSerializer(ModelSerializer):
    document_count = SerializerMethodField()

    class Meta:
        model = DocumentType
        fields = '__all__'

    def get_document_count(self, obj):
        return obj.document_set.count()
```

Create `documents/filters.py`:
```python
class DocumentFilterSet(FilterSet):
    created_after = DateFilter(field_name='created', lookup_expr='gte')
    created_before = DateFilter(field_name='created', lookup_expr='lte')
    added_after = DateTimeFilter(field_name='added', lookup_expr='gte')
    added_before = DateTimeFilter(field_name='added', lookup_expr='lte')
    tags__id__in = CharFilter(method='filter_tags')
    has_asn = BooleanFilter(method='filter_has_asn')

    class Meta:
        model = Document
        fields = ['document_type', 'correspondent', 'storage_path',
                  'mime_type', 'language', 'archive_serial_number']

    def filter_tags(self, queryset, name, value):
        tag_ids = [int(x) for x in value.split(',')]
        for tag_id in tag_ids:
            queryset = queryset.filter(tags__id=tag_id)
        return queryset

    def filter_has_asn(self, queryset, name, value):
        if value:
            return queryset.filter(archive_serial_number__isnull=False)
        return queryset.filter(archive_serial_number__isnull=True)
```

**Acceptance Criteria**:
- CRUD operations work on Documents and DocumentTypes
- Filtering works (date ranges, tags, document type, etc.)
- Ordering works on all specified fields
- Search works across title, content, filename
- Permissions enforced (owner access, ACL access)
- Soft delete on DELETE (not hard delete)
- Restore endpoint works
- Pagination on list endpoints
- Unit tests for all endpoints and filters

### Task 3.3: URL Configuration
**Priority**: High
**Estimated Effort**: 2 hours

Configure `docvault/urls.py`:
```python
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

router = DefaultRouter()
router.register(r'documents', DocumentViewSet)
router.register(r'document_types', DocumentTypeViewSet)
router.register(r'users', UserViewSet)
router.register(r'groups', GroupViewSet)
router.register(r'roles', RoleViewSet)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include(router.urls)),
    path('api/v1/auth/', include('security.urls')),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema')),
]
```

**Acceptance Criteria**:
- All endpoints accessible under `/api/v1/`
- OpenAPI schema at `/api/schema/`
- Swagger UI at `/api/docs/`
- Django admin at `/admin/`

### Task 3.4: Angular Project Initialization
**Priority**: Critical
**Estimated Effort**: 6 hours

Initialize Angular 21+ project in `src-ui/`:
```bash
ng new docvault-ui --style=scss --routing=true --standalone=true
```

Set up project structure:
```
src-ui/
├── angular.json
├── package.json
├── tsconfig.json
├── src/
│   ├── main.ts
│   ├── index.html
│   ├── styles.scss
│   ├── app/
│   │   ├── app.component.ts
│   │   ├── app.routes.ts
│   │   ├── services/
│   │   │   ├── api.service.ts            # Base HTTP service
│   │   │   ├── auth.service.ts           # Authentication
│   │   │   ├── document.service.ts       # Document CRUD
│   │   │   └── config.service.ts         # App configuration
│   │   ├── guards/
│   │   │   └── auth.guard.ts             # Route protection
│   │   ├── interceptors/
│   │   │   ├── auth.interceptor.ts       # Token injection
│   │   │   └── error.interceptor.ts      # Error handling
│   │   ├── models/
│   │   │   ├── document.model.ts         # TypeScript interfaces
│   │   │   └── user.model.ts
│   │   └── components/
│   │       ├── login/                    # Login page
│   │       ├── layout/                   # App shell (nav, sidebar)
│   │       └── dashboard/               # Placeholder dashboard
│   └── environments/
│       ├── environment.ts
│       └── environment.prod.ts
```

Install dependencies:
```bash
pnpm add @ng-bootstrap/ng-bootstrap bootstrap bootstrap-icons
```

**Acceptance Criteria**:
- `pnpm start` runs Angular dev server
- Angular app builds successfully
- SCSS and Bootstrap configured
- Project structure follows conventions

### Task 3.5: Angular Auth Flow
**Priority**: Critical
**Estimated Effort**: 6 hours

Implement authentication:

**`auth.service.ts`**:
- `login(username, password)` - POST to `/api/v1/auth/login/`
- `logout()` - POST to `/api/v1/auth/logout/`, clear token
- `getProfile()` - GET `/api/v1/auth/profile/`
- Token storage in localStorage
- `isAuthenticated$` observable

**`auth.interceptor.ts`**:
- Inject `Authorization: Token xxx` header on all API requests
- Handle 401 responses (redirect to login)

**`auth.guard.ts`**:
- Protect routes requiring authentication
- Redirect to login if not authenticated

**`login/` component**:
- Username/password form
- Error message display
- Redirect to dashboard on success

**Acceptance Criteria**:
- Login page renders and submits credentials
- Token stored and sent with subsequent requests
- 401 responses redirect to login
- Protected routes inaccessible when not logged in
- Logout clears token and redirects to login

### Task 3.6: Basic Layout & Navigation
**Priority**: High
**Estimated Effort**: 4 hours

Create app shell with:

**`layout/` component**:
- Top navigation bar with logo, search input (placeholder), user menu
- Sidebar with navigation links:
  - Dashboard
  - Documents
  - Document Types (placeholder)
  - Tags (placeholder)
  - Admin (placeholder)
- Main content area with router outlet
- Responsive design (sidebar collapses on mobile)

**`dashboard/` component**:
- Placeholder dashboard with:
  - Welcome message
  - Document count statistic (from API)
  - Quick upload button (placeholder)

**Acceptance Criteria**:
- App shell with nav bar and sidebar renders
- Navigation links work (route to placeholder pages)
- Layout is responsive
- User menu shows logged-in username
- Logout from user menu works

### Task 3.7: Docker Build for Frontend
**Priority**: Medium
**Estimated Effort**: 3 hours

Update `Dockerfile` for multi-stage build:
```dockerfile
# Stage 1: Build Angular
FROM node:22-slim AS frontend
WORKDIR /app
COPY src-ui/package.json src-ui/pnpm-lock.yaml ./
RUN corepack enable && pnpm install --frozen-lockfile
COPY src-ui/ .
RUN pnpm build --configuration=production

# Stage 2: Django app
FROM python:3.13-slim AS app
# ... (existing Django setup)
# Copy built frontend into Django static directory
COPY --from=frontend /app/dist/docvault-ui/ /app/frontend/static/frontend/
```

Configure Django to serve the Angular SPA:
```python
# In urls.py, catch-all route for SPA
urlpatterns += [
    re_path(r'^(?!api|admin|static).*$', serve_frontend),
]
```

**Acceptance Criteria**:
- Multi-stage Docker build produces working image
- Angular app served by Django in production mode
- API requests go to Django backend
- SPA routing works (refresh on any route loads Angular app)

---

## Dependencies

### New Python Packages
```
drf-spectacular>=0.28
django-filter>=24.0
```

### New NPM Packages
```
@angular/core@^21
@ng-bootstrap/ng-bootstrap@^20
bootstrap@^5.3
bootstrap-icons@^1.11
```

---

## Definition of Done
- [ ] DRF configured with pagination, filtering, throttling, OpenAPI
- [ ] Document CRUD API works with permissions
- [ ] DocumentType CRUD API works
- [ ] OpenAPI schema generates correctly
- [ ] Swagger UI accessible
- [ ] Angular project initialized and builds
- [ ] Login page works (authenticate and store token)
- [ ] Auth guard protects routes
- [ ] Auth interceptor injects token
- [ ] Basic layout with navigation renders
- [ ] Multi-stage Docker build works
- [ ] Django serves Angular app in production mode
- [ ] All API endpoints have unit tests
- [ ] `python manage.py test` passes
