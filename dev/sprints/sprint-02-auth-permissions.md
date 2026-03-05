# Sprint 2: Authentication & Permissions

## Phase: 1 - Foundation
## Duration: 2 weeks
## Prerequisites: Sprint 1 (Project Scaffolding & Core Models)

---

## Sprint Goal
Implement comprehensive authentication (Django auth, allauth, LDAP, token auth) and the permission system (roles, object-level ACLs via django-guardian, and the OwnedModel permission pattern).

---

## Context for Agents

### Read Before Starting
- `/doc/architecture.md` - Section 5 (Security Architecture)
- `/doc/product-spec.md` - Section 2.6 (Security Module)
- `/doc/research/mayan-edms-analysis.md` - Section 4 (Security Model) - the ACL pattern we're adopting
- `/doc/research/paperless-ngx-analysis.md` - Section 8 (Permissions) - the guardian pattern we're adopting

### Key Design Decisions
1. **Combine Mayan's generic ACLs with Paperless-ngx's guardian approach**
2. **Owner-based shortcut**: Document owners always have full access (no ACL check needed)
3. **Role -> Permission -> Group -> User** hierarchy
4. **API token auth for programmatic access**
5. **LDAP ready but optional** - enterprise feature, not required for basic setup

---

## Tasks

### Task 2.1: Django Auth & Allauth Setup
**Priority**: Critical
**Estimated Effort**: 6 hours

Install and configure:
- `django-allauth` for OAuth2/SSO
- Token authentication (DRF tokens)
- Session authentication (cookie-based for web UI)

Create `security/` app:
```
security/
├── __init__.py
├── apps.py
├── models/
│   ├── __init__.py
│   ├── role.py          # Role model
│   ├── acl.py           # AccessControlList model
│   └── quota.py         # Quota model (placeholder for Sprint 12)
├── authentication.py    # Custom auth backends
├── permissions.py       # DRF permission classes
├── serializers.py       # User, Group, Role serializers
├── views.py             # Auth API endpoints
├── urls.py
├── admin.py
├── migrations/
└── tests/
```

Configure allauth:
- Email-based registration
- Social login providers (placeholder, configured via admin)
- Email verification (optional, configurable)

**Acceptance Criteria**:
- Users can register via API
- Users can login via API (returns token)
- Users can logout (invalidates token)
- Session auth works for web UI
- Token auth works for API clients
- `django-allauth` installed and configured

### Task 2.2: Role & Permission Models
**Priority**: Critical
**Estimated Effort**: 6 hours

```python
# security/models/role.py

class Permission(models.Model):
    """System-level permission definition."""
    namespace = CharField(max_length=64)  # e.g., 'documents', 'workflows'
    codename = CharField(max_length=64)   # e.g., 'view', 'change', 'delete'
    name = CharField(max_length=256)      # Human-readable name

    class Meta:
        unique_together = [['namespace', 'codename']]
        ordering = ['namespace', 'codename']


class Role(AuditableModel):
    """Collection of permissions assigned to groups."""
    name = CharField(max_length=128, unique=True)
    permissions = ManyToManyField(Permission, blank=True)
    groups = ManyToManyField(Group, blank=True, related_name='roles')

    def has_permission(self, namespace, codename):
        return self.permissions.filter(
            namespace=namespace, codename=codename
        ).exists()
```

Create initial permissions via data migration:
```python
INITIAL_PERMISSIONS = [
    ('documents', 'view_document', 'Can view documents'),
    ('documents', 'add_document', 'Can add documents'),
    ('documents', 'change_document', 'Can change documents'),
    ('documents', 'delete_document', 'Can delete documents'),
    ('documents', 'download_document', 'Can download documents'),
    ('documents', 'share_document', 'Can share documents'),
    ('documents', 'view_documenttype', 'Can view document types'),
    ('documents', 'manage_documenttype', 'Can manage document types'),
    ('security', 'view_user', 'Can view users'),
    ('security', 'manage_user', 'Can manage users'),
    ('security', 'view_role', 'Can view roles'),
    ('security', 'manage_role', 'Can manage roles'),
]
```

**Acceptance Criteria**:
- Role model with M2M to Permission and Group
- Permission model with namespace/codename pattern
- Initial permissions created via data migration
- Roles can be created, assigned to groups, and checked
- Unit tests for permission checking

### Task 2.3: Object-Level ACLs (django-guardian)
**Priority**: Critical
**Estimated Effort**: 8 hours

Install and configure `django-guardian` for object-level permissions:

```python
# security/permissions.py

class DocVaultObjectPermissions(DjangoObjectPermissions):
    """
    Custom permission class that checks:
    1. Is user superuser? -> Allow all
    2. Is user the object owner? -> Allow all
    3. Does user have explicit object permission (guardian)? -> Check
    4. Does user's role grant model-level permission? -> Check
    5. Default: Deny
    """

    perms_map = {
        'GET': ['%(app_label)s.view_%(model_name)s'],
        'OPTIONS': [],
        'HEAD': [],
        'POST': ['%(app_label)s.add_%(model_name)s'],
        'PUT': ['%(app_label)s.change_%(model_name)s'],
        'PATCH': ['%(app_label)s.change_%(model_name)s'],
        'DELETE': ['%(app_label)s.delete_%(model_name)s'],
    }

    def has_object_permission(self, request, view, obj):
        # Owner shortcut
        if hasattr(obj, 'owner') and obj.owner == request.user:
            return True

        # Guardian check
        return super().has_object_permission(request, view, obj)


class ObjectPermissionsFilter(DjangoObjectPermissionsFilter):
    """Filter querysets to only objects user can access."""

    def filter_queryset(self, request, queryset, view):
        # Owner shortcut - always include owned objects
        user = request.user
        if hasattr(queryset.model, 'owner'):
            owned = queryset.filter(owner=user)
            permitted = super().filter_queryset(request, queryset, view)
            return (owned | permitted).distinct()
        return super().filter_queryset(request, queryset, view)
```

Utility function for setting permissions:
```python
def set_object_permissions(obj, permissions_dict):
    """
    Set object-level permissions.
    permissions_dict format:
    {
        'view': {'users': [1, 2], 'groups': [3]},
        'change': {'users': [1], 'groups': []},
    }
    """
    from guardian.shortcuts import assign_perm, remove_perm
    # Clear existing and assign new...
```

**Acceptance Criteria**:
- django-guardian installed and configured
- DocVaultObjectPermissions class works with DRF ViewSets
- Owner always has full access
- Non-owners need explicit permissions
- ObjectPermissionsFilter filters querysets correctly
- Permission assignment utility function works
- Unit tests for all permission scenarios

### Task 2.4: User & Group Management API
**Priority**: High
**Estimated Effort**: 6 hours

Create API endpoints for user and group management:

```python
# Endpoints:
GET/POST     /api/v1/users/           # List/create users
GET/PATCH    /api/v1/users/{id}/      # Retrieve/update user
GET/POST     /api/v1/groups/          # List/create groups
GET/PATCH    /api/v1/groups/{id}/     # Retrieve/update group
GET/POST     /api/v1/roles/           # List/create roles
GET/PATCH    /api/v1/roles/{id}/      # Retrieve/update role
GET          /api/v1/permissions/     # List all permissions
POST         /api/v1/auth/login/      # Login (returns token)
POST         /api/v1/auth/logout/     # Logout (invalidates token)
POST         /api/v1/auth/register/   # Register new user
GET          /api/v1/auth/profile/    # Current user profile
PATCH        /api/v1/auth/profile/    # Update profile
POST         /api/v1/auth/token/      # Generate API token
```

Serializers:
```python
class UserSerializer(ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name',
                  'is_active', 'groups', 'date_joined']
        read_only_fields = ['id', 'date_joined']

class UserCreateSerializer(ModelSerializer):
    password = CharField(write_only=True, min_length=8)
    # ...

class GroupSerializer(ModelSerializer):
    user_count = SerializerMethodField()
    # ...

class RoleSerializer(ModelSerializer):
    permissions = PermissionSerializer(many=True, read_only=True)
    permission_ids = PrimaryKeyRelatedField(many=True, write_only=True, ...)
    # ...
```

**Acceptance Criteria**:
- All user/group/role CRUD endpoints work
- Login returns authentication token
- Logout invalidates token
- Profile endpoint returns current user info
- Only admins can manage users/groups/roles
- Password validation enforced
- Unit tests for all endpoints

### Task 2.5: LDAP Authentication Backend
**Priority**: Medium
**Estimated Effort**: 4 hours

Install and configure `django-auth-ldap`:

```python
# security/authentication.py
import ldap
from django_auth_ldap.config import LDAPSearch, GroupOfNamesType

# Configuration via environment variables
AUTH_LDAP_ENABLED = env.bool('LDAP_ENABLED', default=False)
AUTH_LDAP_SERVER_URI = env.str('LDAP_SERVER_URI', default='')
AUTH_LDAP_BIND_DN = env.str('LDAP_BIND_DN', default='')
AUTH_LDAP_BIND_PASSWORD = env.str('LDAP_BIND_PASSWORD', default='')
AUTH_LDAP_USER_SEARCH = LDAPSearch(
    env.str('LDAP_USER_SEARCH_BASE', default=''),
    ldap.SCOPE_SUBTREE,
    env.str('LDAP_USER_SEARCH_FILTER', default='(uid=%(user)s)')
)
AUTH_LDAP_GROUP_SEARCH = LDAPSearch(
    env.str('LDAP_GROUP_SEARCH_BASE', default=''),
    ldap.SCOPE_SUBTREE,
    '(objectClass=groupOfNames)'
)
AUTH_LDAP_GROUP_TYPE = GroupOfNamesType()
AUTH_LDAP_USER_ATTR_MAP = {
    'first_name': 'givenName',
    'last_name': 'sn',
    'email': 'mail',
}
```

**Acceptance Criteria**:
- LDAP auth works when `LDAP_ENABLED=true` and LDAP server configured
- LDAP users auto-created in Django on first login
- LDAP group membership synced to Django groups
- System works without LDAP when `LDAP_ENABLED=false`
- Configuration fully via environment variables

### Task 2.6: Middleware Stack
**Priority**: Medium
**Estimated Effort**: 3 hours

Configure middleware in `base.py`:
```python
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'core.middleware.AuditableModelMiddleware',
]
```

Create `core/middleware.py`:
```python
class AuditableModelMiddleware:
    """Automatically set created_by/updated_by on AuditableModel saves."""
    # Thread-local storage for current user
    # ...
```

**Acceptance Criteria**:
- CORS headers configured (allow frontend origin)
- Security headers set (X-Frame-Options, CSP, etc.)
- Whitenoise serves static files
- AuditableModel middleware sets user on save

---

## Dependencies

### New Python Packages
```
django-allauth>=65.0
django-guardian>=3.3
django-auth-ldap>=5.3
django-cors-headers>=4.9
djangorestframework>=3.16
whitenoise>=6.11
python-ldap>=3.4  # System dependency: libldap2-dev, libsasl2-dev
```

---

## Definition of Done
- [ ] Users can register, login, and logout via API
- [ ] Token authentication works for API clients
- [ ] Session authentication works for web UI
- [ ] Role model with permissions exists and works
- [ ] Object-level ACLs filter document access correctly
- [ ] Owner-based access shortcut works
- [ ] User/group/role CRUD API endpoints work
- [ ] LDAP authentication works when configured
- [ ] Middleware stack is complete (CORS, security, audit)
- [ ] All auth/permission scenarios have unit tests
- [ ] `python manage.py test` passes
