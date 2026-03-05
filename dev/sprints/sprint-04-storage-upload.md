# Sprint 4: Storage & Upload Pipeline

## Phase: 2 - Document Processing
## Duration: 2 weeks
## Prerequisites: Sprint 3 (REST API Foundation & Frontend Scaffold)

---

## Sprint Goal
Build the storage backend abstraction, file upload pipeline, document consumer orchestrator with plugin architecture, Celery async processing, and WebSocket progress notifications.

---

## Context for Agents

### Read Before Starting
- `/doc/architecture.md` - Section 4 (Processing Pipeline Architecture)
- `/doc/product-spec.md` - Section 2.3 (Processing Module) and 2.8 (Storage Module)
- `/doc/research/paperless-ngx-analysis.md` - Section 4 (Processing Pipeline) for plugin pattern
- `/doc/research/lodestone-analysis.md` - Section 1 (Architecture) for S3/MinIO patterns

### Key Design Decisions
1. **Plugin-based processing pipeline** (from Paperless-ngx ConsumeTaskPlugin pattern)
2. **S3-compatible storage via MinIO** (from Lodestone) as primary, local filesystem as fallback
3. **Celery + Redis for async processing** (proven in both Mayan and Paperless-ngx)
4. **WebSocket for real-time progress** (from Paperless-ngx Django Channels)
5. **ProcessingContext dataclass** passes state between plugins

---

## Tasks

### Task 4.1: Storage Backend Abstraction
**Priority**: Critical
**Estimated Effort**: 8 hours

Create `storage/` app:
```python
# storage/backends/base.py
class StorageBackend(ABC):
    @abstractmethod
    def save(self, name: str, content: File) -> str:
        """Save file and return storage path."""

    @abstractmethod
    def open(self, name: str) -> File:
        """Open file for reading."""

    @abstractmethod
    def delete(self, name: str) -> None:
        """Delete file."""

    @abstractmethod
    def exists(self, name: str) -> bool:
        """Check if file exists."""

    @abstractmethod
    def url(self, name: str) -> str:
        """Get URL for file access."""

    @abstractmethod
    def size(self, name: str) -> int:
        """Get file size in bytes."""
```

Implement backends:
- `storage/backends/local.py` - Django default FileSystemStorage wrapper
- `storage/backends/s3.py` - S3-compatible via `boto3`/`django-storages`

Configuration:
```python
# Settings
STORAGE_BACKEND = env.str('STORAGE_BACKEND', 'local')  # 'local' or 's3'
STORAGE_DIR = env.path('STORAGE_DIR', default='media/documents')

# S3 settings
S3_ENDPOINT_URL = env.str('S3_ENDPOINT_URL', default='')
S3_ACCESS_KEY = env.str('S3_ACCESS_KEY', default='')
S3_SECRET_KEY = env.str('S3_SECRET_KEY', default='')
S3_BUCKET_NAME = env.str('S3_BUCKET_NAME', default='docvault')
S3_REGION = env.str('S3_REGION', default='us-east-1')
```

Storage directory structure:
```
media/documents/
├── originals/         # Original uploaded files (never modified)
├── archive/           # Processed/OCR'd PDFs
└── thumbnails/        # Generated previews
```

**Acceptance Criteria**:
- Local storage backend works (save, open, delete, exists)
- S3 storage backend works with MinIO
- Storage backend selectable via environment variable
- Directory structure created automatically
- Unit tests for both backends

### Task 4.2: Celery & Redis Setup
**Priority**: Critical
**Estimated Effort**: 4 hours

Configure Celery in `docvault/celery.py`:
```python
app = Celery('docvault')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
```

Settings:
```python
CELERY_BROKER_URL = env.str('REDIS_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = env.str('REDIS_URL', 'redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 1800  # 30 minutes max
CELERY_TASK_SOFT_TIME_LIMIT = 1500  # 25 minutes soft limit
```

Add Celery worker to Docker Compose:
```yaml
worker:
  build: .
  command: celery -A docvault worker -l info -Q default,processing
  depends_on: [db, redis]
  environment: *app-env
  volumes: *app-volumes
```

**Acceptance Criteria**:
- Celery worker starts and connects to Redis
- Tasks can be submitted and executed
- Task results stored in Redis
- Docker Compose includes worker service

### Task 4.3: Processing Pipeline & Plugin System
**Priority**: Critical
**Estimated Effort**: 10 hours

Create `processing/` app:

```python
# processing/plugins/base.py
class ProcessingPlugin(ABC):
    """Base class for document processing plugins."""
    name: str = "BasePlugin"
    order: int = 0

    @abstractmethod
    def can_run(self, context: 'ProcessingContext') -> bool:
        """Check if this plugin should run."""

    @abstractmethod
    def process(self, context: 'ProcessingContext') -> 'PluginResult':
        """Execute plugin logic. May modify context."""

    def setup(self, context: 'ProcessingContext') -> None:
        """Optional setup before processing."""
        pass

    def cleanup(self, context: 'ProcessingContext') -> None:
        """Optional cleanup after processing."""
        pass

    def send_progress(self, context: 'ProcessingContext',
                      progress: float, message: str) -> None:
        """Report progress to task tracking."""
        if context.task_id:
            update_task_progress.delay(context.task_id, progress, message)


@dataclass
class PluginResult:
    success: bool = True
    should_stop: bool = False  # Stop processing chain
    message: str = ""


@dataclass
class ProcessingContext:
    # Input
    source_path: Path = None
    original_filename: str = ""
    mime_type: str = ""
    source_type: str = ""  # 'web', 'api', 'email', 'folder', 'scanner'
    user_id: int = None

    # Accumulated state
    content: str = ""
    language: str = ""
    date_created: date = None
    title: str = ""
    archive_path: Path = None
    thumbnail_path: Path = None
    page_count: int = 0
    checksum: str = ""
    archive_checksum: str = ""

    # Classification (populated by later plugins)
    suggested_tags: list = field(default_factory=list)
    suggested_correspondent: int = None
    suggested_document_type: int = None
    suggested_storage_path: int = None

    # Overrides (from API or workflow rules)
    override_title: str = None
    override_correspondent: int = None
    override_document_type: int = None
    override_tags: list = None
    override_owner: int = None
    override_asn: int = None

    # Task tracking
    task_id: str = None
    progress: float = 0.0
    status_message: str = ""

    # Result
    document_id: int = None
    errors: list = field(default_factory=list)
```

```python
# processing/consumer.py
class DocumentConsumer:
    """Orchestrates document processing via plugin chain."""

    def __init__(self):
        self.plugins = self._discover_plugins()

    def _discover_plugins(self) -> list[type[ProcessingPlugin]]:
        """Discover and sort plugins by order."""
        # For now, hardcoded list. Plugin discovery can be added later.
        from .plugins.preflight import PreflightPlugin
        return sorted([PreflightPlugin], key=lambda p: p.order)

    def consume(self, context: ProcessingContext) -> ProcessingContext:
        """Run all applicable plugins on the document."""
        for plugin_class in self.plugins:
            plugin = plugin_class()
            if plugin.can_run(context):
                plugin.setup(context)
                try:
                    result = plugin.process(context)
                    if not result.success:
                        context.errors.append(f"{plugin.name}: {result.message}")
                    if result.should_stop:
                        break
                except Exception as e:
                    context.errors.append(f"{plugin.name}: {str(e)}")
                    raise
                finally:
                    plugin.cleanup(context)
        return context
```

```python
# processing/plugins/preflight.py
class PreflightPlugin(ProcessingPlugin):
    name = "Preflight"
    order = 10

    def can_run(self, context):
        return True  # Always runs

    def process(self, context):
        # 1. Detect MIME type
        import magic
        context.mime_type = magic.from_file(str(context.source_path), mime=True)

        # 2. Calculate checksum
        context.checksum = self._calculate_checksum(context.source_path)

        # 3. Check for duplicates
        if Document.objects.filter(checksum=context.checksum).exists():
            return PluginResult(success=False, should_stop=True,
                              message="Duplicate document detected")

        # 4. Set title from filename if not overridden
        if not context.override_title:
            context.title = Path(context.original_filename).stem

        self.send_progress(context, 0.05, "Preflight checks complete")
        return PluginResult(success=True)
```

**Acceptance Criteria**:
- ProcessingPlugin ABC defines the interface
- ProcessingContext carries all state between plugins
- DocumentConsumer orchestrates plugin execution in order
- PreflightPlugin validates MIME type, checksum, duplicates
- Plugin errors are captured and reported
- Progress tracking works
- Unit tests for consumer and preflight plugin

### Task 4.4: Task Status Tracking
**Priority**: High
**Estimated Effort**: 4 hours

```python
# processing/models.py
class ProcessingTask(SoftDeleteModel):
    class Status(TextChoices):
        PENDING = 'pending'
        STARTED = 'started'
        SUCCESS = 'success'
        FAILURE = 'failure'

    task_id = UUIDField(default=uuid.uuid4, unique=True)
    task_name = CharField(max_length=256)
    status = CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    progress = FloatField(default=0.0)  # 0.0 to 1.0
    status_message = CharField(max_length=512, blank=True, default='')
    result = TextField(blank=True, default='')
    document = ForeignKey('documents.Document', null=True, blank=True,
                         on_delete=SET_NULL)
    owner = ForeignKey(User, null=True, on_delete=SET_NULL)
    created_at = DateTimeField(auto_now_add=True)
    started_at = DateTimeField(null=True)
    completed_at = DateTimeField(null=True)
```

API endpoint:
```python
# GET /api/v1/tasks/ - List tasks for current user
# GET /api/v1/tasks/{id}/ - Task detail
# POST /api/v1/tasks/{id}/acknowledge/ - Mark task as seen
```

**Acceptance Criteria**:
- Task model tracks processing status and progress
- Tasks visible via API (filtered by user)
- Progress updates stored and retrievable
- Acknowledge endpoint marks tasks as seen

### Task 4.5: File Upload Endpoint
**Priority**: Critical
**Estimated Effort**: 6 hours

```python
# documents/views.py
class DocumentUploadView(CreateAPIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser]

    def create(self, request, *args, **kwargs):
        file = request.FILES.get('document')
        if not file:
            return Response({'error': 'No file provided'}, status=400)

        # Save to temp location
        temp_path = self._save_temp_file(file)

        # Create processing task
        task = ProcessingTask.objects.create(
            task_name='document_consumption',
            owner=request.user,
            status_message='Queued for processing'
        )

        # Queue async processing
        consume_document.delay(
            source_path=str(temp_path),
            original_filename=file.name,
            task_id=str(task.task_id),
            user_id=request.user.id,
            override_title=request.data.get('title'),
            override_correspondent=request.data.get('correspondent'),
            override_document_type=request.data.get('document_type'),
            override_tags=request.data.get('tags'),
        )

        return Response({
            'task_id': str(task.task_id),
            'status': 'queued',
        }, status=202)
```

```python
# processing/tasks.py
@shared_task(bind=True, max_retries=3)
def consume_document(self, source_path, original_filename, task_id,
                     user_id, **overrides):
    """Main document consumption Celery task."""
    context = ProcessingContext(
        source_path=Path(source_path),
        original_filename=original_filename,
        task_id=task_id,
        user_id=user_id,
        source_type='api',
        override_title=overrides.get('override_title'),
        override_correspondent=overrides.get('override_correspondent'),
        override_document_type=overrides.get('override_document_type'),
        override_tags=overrides.get('override_tags'),
    )

    task = ProcessingTask.objects.get(task_id=task_id)
    task.status = ProcessingTask.Status.STARTED
    task.started_at = timezone.now()
    task.save()

    try:
        consumer = DocumentConsumer()
        context = consumer.consume(context)

        if context.errors:
            task.status = ProcessingTask.Status.FAILURE
            task.result = '\n'.join(context.errors)
        else:
            task.status = ProcessingTask.Status.SUCCESS
            task.document_id = context.document_id
            task.result = f'Document created: {context.title}'

    except Exception as e:
        task.status = ProcessingTask.Status.FAILURE
        task.result = str(e)
        raise
    finally:
        task.completed_at = timezone.now()
        task.save()
```

**Acceptance Criteria**:
- POST `/api/v1/documents/upload/` accepts file upload
- Returns 202 with task_id immediately (async processing)
- File saved to temp location
- Celery task processes the document
- Task status updated throughout processing
- Multiple files can be uploaded concurrently
- Error handling for invalid files

### Task 4.6: WebSocket Progress Notifications
**Priority**: High
**Estimated Effort**: 6 hours

Install Django Channels:
```python
# docvault/asgi.py
application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter([
            path("ws/status/", TaskStatusConsumer.as_asgi()),
        ])
    ),
})
```

```python
# processing/consumers.py (WebSocket, not document consumer)
class TaskStatusConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]
        if self.user.is_anonymous:
            await self.close()
            return
        self.group_name = f"user_{self.user.id}_tasks"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def task_update(self, event):
        await self.send(text_data=json.dumps(event['data']))
```

Utility to send updates:
```python
# processing/signals.py
def send_task_update(task_id, user_id, progress, message, status):
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"user_{user_id}_tasks",
        {
            "type": "task.update",
            "data": {
                "task_id": str(task_id),
                "progress": progress,
                "message": message,
                "status": status,
            }
        }
    )
```

**Acceptance Criteria**:
- WebSocket connection established at `ws://host/ws/status/`
- Authenticated users receive task progress updates in real-time
- Updates include task_id, progress percentage, message, status
- Connection properly closed on disconnect
- Frontend can connect and display progress (basic console logging)

---

## Dependencies

### New Python Packages
```
celery>=5.6
redis>=5.2
channels>=4.2
channels-redis>=4.2
django-storages>=1.14
boto3>=1.40
python-magic>=0.4
```

### Docker Compose Additions
```yaml
minio:
  image: minio/minio:latest
  command: server /data --console-address ":9001"
  ports:
    - "9000:9000"
    - "9001:9001"
  environment:
    MINIO_ROOT_USER: docvault
    MINIO_ROOT_PASSWORD: docvault123
  volumes:
    - miniodata:/data
```

---

## Definition of Done
- [ ] Storage backends (local + S3) work with save/open/delete
- [ ] Celery worker processes async tasks
- [ ] ProcessingPlugin base class and registry work
- [ ] PreflightPlugin validates MIME type, checksum, duplicates
- [ ] File upload endpoint accepts files and queues processing
- [ ] ProcessingTask model tracks status and progress
- [ ] WebSocket delivers real-time progress updates
- [ ] Task status API returns current task status
- [ ] MinIO integration works for S3 storage
- [ ] All components have unit tests
- [ ] `python manage.py test` passes
