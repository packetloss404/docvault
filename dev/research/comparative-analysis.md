# Comparative Analysis - All Three Systems

## Feature Matrix

| Feature | Lodestone | Mayan EDMS | Paperless-ngx | **Our System** |
|---------|:---------:|:----------:|:-------------:|:--------------:|
| **Architecture** | Microservices | Monolith (100+ apps) | Monolith + SPA | Modular Monolith + SPA |
| **Frontend** | Angular 11 | Django Templates | Angular 21 | Modern SPA (Angular/React) |
| **Backend** | Express.js + Go | Django 5.2 | Django 5.2 | Django |
| **API** | Custom REST | DRF + Swagger | DRF + OpenAPI | DRF + OpenAPI |
| **Search Engine** | Elasticsearch | Elasticsearch/Whoosh | Whoosh + FAISS | Elasticsearch + FAISS |
| **Task Queue** | RabbitMQ | Celery + Redis | Celery + Redis | Celery + Redis |
| **OCR** | Apache Tika | Tesseract | OCRmyPDF (Tesseract) | OCRmyPDF |
| **Storage** | MinIO (S3) | S3/GCS/Local/Encrypted | Local filesystem | S3/Local + Encryption |
| | | | | |
| **Full-Text Search** | YES | YES | YES | YES |
| **Vector/Semantic Search** | NO | NO | YES (FAISS) | YES |
| **ML Auto-Classification** | NO | NO | YES (scikit-learn) | YES |
| **LLM Integration** | NO | YES (basic) | YES (comprehensive) | YES |
| **Barcode Detection** | NO | NO | YES (zxing-cpp) | YES |
| | | | | |
| **Tagging** | Hierarchical JSON | Color-coded flat | Hierarchical 5-level | Hierarchical + Color |
| **Custom Fields** | NO | Metadata Types | 10 data types | Extended Custom Fields |
| **Cabinets/Folders** | NO | MPTT hierarchical | NO | MPTT hierarchical |
| **Document Types** | File types only | Full schema | Matching-based | Full schema + ML |
| | | | | |
| **Workflow Engine** | NO | State machine (full) | Trigger/Action | State machine + Triggers |
| **Retention Policies** | NO | YES (per type) | NO | YES |
| **Check-in/Check-out** | NO | YES | NO | YES |
| **Document Versioning** | NO | YES (full) | YES (basic) | YES (full) |
| **Document Signing** | NO | YES (GPG) | NO | YES |
| | | | | |
| **Authentication** | None | LDAP+OIDC+OTP | OAuth/allauth | LDAP+OIDC+OTP+OAuth |
| **Object-Level ACLs** | NO | YES (generic) | YES (guardian) | YES (generic + guardian) |
| **Role-Based Permissions** | NO | YES | YES (basic) | YES (comprehensive) |
| **Usage Quotas** | NO | YES | NO | YES |
| **Storage Encryption** | NO | YES (AES-256) | NO | YES |
| **Audit Trail** | NO | YES (events) | YES (optional) | YES (mandatory) |
| | | | | |
| **Email Ingestion** | NO (WIP) | YES | YES (IMAP+OAuth) | YES |
| **Watch Folders** | YES | YES | YES | YES |
| **Scanner Support** | NO | YES (SANE) | NO | YES |
| **Cloud Storage Sources** | NO | YES (S3/GCS) | NO | YES |
| **Bulk Operations** | NO | YES | YES | YES |
| | | | | |
| **Share Links** | NO | NO | YES | YES |
| **Comments/Notes** | NO | YES | YES | YES |
| **Dark Mode** | NO | NO | YES | YES |
| **Multi-language UI** | NO | YES | YES (30+) | YES |
| **WebSocket Updates** | NO | NO | YES | YES |
| **Non-destructive** | YES | NO | NO | YES (configurable) |
| **Pre/Post Hooks** | NO | NO | YES | YES |
| **Plugin System** | NO | Backend registry | ConsumeTaskPlugin | Full plugin system |

---

## Best-of-Breed Feature Selection

### From Lodestone (Adopt)
1. **Non-destructive processing** - Option to keep originals untouched
2. **S3-compatible storage via MinIO** - Industry-standard storage API
3. **WORM storage support** - Compliance-ready immutable storage
4. **Microservices-inspired processing** - Scalable worker architecture
5. **Convention over Configuration** - Sensible defaults philosophy

### From Mayan EDMS (Adopt)
1. **Workflow state machine** - Full state/transition/action/escalation engine
2. **Generic ACLs** - Object-level permissions on any model
3. **Check-in/check-out** - Document locking for collaboration
4. **Retention policies** - Auto-trash/delete per document type
5. **AES-256 storage encryption** - At-rest encryption
6. **LDAP + OIDC + OTP authentication** - Enterprise auth
7. **MPTT cabinets** - Hierarchical folder system
8. **Document signing** - GPG/PGP support
9. **Usage quotas** - Resource management
10. **11+ ingestion sources** - Comprehensive input options
11. **Metadata validators/parsers/lookups** - Rich metadata system
12. **Event system with decorators** - Comprehensive audit trail
13. **SANE scanner support** - Direct scanner integration

### From Paperless-ngx (Adopt)
1. **ML auto-classification** - scikit-learn pipeline
2. **Modern Angular SPA** - Best-in-class UI/UX
3. **Barcode detection & ASN** - Physical-digital bridge
4. **FAISS vector search** - Semantic search
5. **LLM integration** - Document Q&A, AI classification
6. **Custom fields (10 types)** - Flexible metadata
7. **Share links** - Guest access with expiration
8. **WebSocket real-time updates** - Live UI updates
9. **Pre/post-consume scripts** - Hook-based extensibility
10. **Plugin architecture** - ConsumeTaskPlugin pattern
11. **Hierarchical tags with colors** - Visual organization
12. **Dark mode & theming** - Modern UI expectations
13. **Saved views** - Customizable dashboards
14. **Document versioning** - Version tracking
15. **Soft delete/trash** - Safe deletion with recovery

---

## Architecture Decision: Why Modular Monolith

After analyzing all three systems:

- **Lodestone's microservices** are elegant but add operational complexity and make development harder (9 separate repos, complex orchestration)
- **Mayan's 100+ Django apps** provide modularity but are overwhelming and tightly coupled despite the app separation
- **Paperless-ngx's focused monolith** is the most maintainable but could benefit from better modularity

**Decision**: Build a **modular monolith** using Django with clear domain boundaries, but keep everything in a single deployable unit. Use Celery workers for processing scalability. Keep the Angular SPA for frontend. This gives us Mayan's modularity without the complexity, and Paperless-ngx's simplicity without the limitations.

---

## Technology Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Backend Framework | Django 5.x | Proven, both Mayan & Paperless use it, rich ecosystem |
| Frontend | Angular 21+ | Paperless-ngx proves it works well, modern SPA |
| API | DRF + OpenAPI | Industry standard, both systems use it |
| Search | Elasticsearch + FAISS | Elasticsearch scales better than Whoosh; FAISS for AI |
| Task Queue | Celery + Redis | Proven combination in both systems |
| OCR | OCRmyPDF (Tesseract) | Better than raw Tesseract, PDF/A output |
| Storage | S3-compatible + Local | MinIO for self-hosted, AWS S3 for cloud |
| Auth | django-allauth + LDAP + OTP | Cover both consumer and enterprise |
| Permissions | django-guardian + custom ACLs | Combine best of both approaches |
| ML | scikit-learn + LLM | Proven pipeline from Paperless-ngx |
| Database | PostgreSQL (primary) | Production-grade, both systems recommend it |
