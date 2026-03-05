# Lodestone Document Management System - Deep Dive Analysis

## Executive Summary

Lodestone is a modern, microservices-based personal document management system designed for self-hosted deployment on trusted home networks. It emphasizes non-destructive document processing, meaning original files are never modified. The system uses a cloud-native architecture with Docker containers and Kubernetes support.

**Project Maturity:** Work-in-Progress (v0.1.0) - Not production-ready
**License:** Open Source
**Target Audience:** Home users / personal document management

---

## 1. Technical Architecture

### Tech Stack
| Component | Technology | Version |
|-----------|-----------|---------|
| Frontend | Angular | v11.x |
| Backend API | Express.js (Node.js) | v4.16 |
| Document Processors | Go | Compiled binaries |
| Search Engine | Elasticsearch | v7.2.1 |
| Message Queue | RabbitMQ | v3-management |
| OCR Engine | Apache Tika | Java-based |
| Object Storage | MinIO | S3-compatible |

### Microservices Architecture
Lodestone is composed of **9+ independent Docker containers**:

1. **Elasticsearch** (`lodestonehq/lodestone-elasticsearch:v0.1.0`)
   - Data persistence and full-text search
   - Custom mapping schema via `mapping.json`
   - Ports: 9200 (HTTP), 9300 (cluster)

2. **Document Processor** (`lodestonehq/lodestone-document-processor:v0.1.0`)
   - Go-based worker consuming from RabbitMQ
   - Integrates with Tika for OCR and text extraction
   - Pushes processed content to Elasticsearch

3. **Thumbnail Processor** (`lodestonehq/lodestone-thumbnail-processor:v0.1.0`)
   - Go-based worker for preview generation
   - Separate service for decoupled processing

4. **Web/API Server** (`lodestonehq/lodestone-ui:v0.1.0`)
   - Express.js REST API + Angular SPA
   - Serves configuration files from `/lodestone/data/`
   - Port: 3000

5. **Filesystem Publisher** (`lodestonehq/lodestone-fs-publisher:v0.1.0`)
   - Go-based filesystem watcher
   - Monitors `/data/storage/documents` directory
   - Publishes file events to RabbitMQ

6. **Email Publisher** - WIP, not yet implemented

7. **Storage Service** (MinIO)
   - S3-compatible object storage
   - WORM (Write-Once-Read-Multiple) support
   - AMQP notification integration

8. **Message Queue** (RabbitMQ)
   - Fanout exchange: `lodestone`
   - Routing key: `storagelogs`

9. **OCR Service** (Apache Tika)
   - Port: 9998
   - Handles text extraction and OCR

### Communication Patterns
- **REST API**: Unified under `/api/v1/` prefix
- **AMQP/RabbitMQ**: Async document processing messages
- **Direct HTTP**: Inter-service communication
- **Reverse Proxy**: Unifies all services under single entry point

### Deployment
- **Docker Compose**: Primary deployment method (`docker-compose.yml`)
- **Kubernetes**: Example manifests in `docs/examples/k8s/`
  - StatefulSets for Elasticsearch, RabbitMQ, MinIO
  - Deployments for processors, webapp, Tika
  - HAProxy Ingress with TLS support
  - Namespace: `lodestone`

---

## 2. Data Model

### Document Storage Strategy (Multi-tier)
1. **Original Documents** (Read-only) - Stored in MinIO, never modified
2. **Processed Content** (Write-once) - Extracted text indexed in Elasticsearch
3. **Thumbnails** (Regeneratable) - Generated previews in MinIO

### Configuration Files
- **`filetypes.json`**: Include/exclude patterns for document processing
- **`tags.json`**: Nested hierarchical tag structure
- **`mapping.json`**: Elasticsearch schema definition

### Supported File Formats
- Microsoft Office: `.doc`, `.docx`, `.xls`, `.xlsx`, `.ppt`, `.pptx`
- Apple iWork: `.pages`, `.numbers`, `.key`
- PDF, RTF
- Images with OCR: `.jpg`, `.jpeg`, `.png`, `.tiff`, `.tif`

---

## 3. Processing Pipeline

```
Filesystem Publisher (watches /data/storage/documents)
    |
    v
RabbitMQ (fanout exchange)
    |
    +---> Document Processor --> Tika (OCR/extraction) --> Elasticsearch (index)
    |
    +---> Thumbnail Processor --> MinIO (preview storage)
```

**Key Principle**: Non-destructive processing - originals remain untouched.

---

## 4. Features

### Implemented
- Full-text search via Elasticsearch with relevance ranking
- Faceted search: date range, file type, file size, tags
- Hierarchical tagging system (configurable via `tags.json`)
- Document thumbnails and preview
- Bookmark functionality
- Similar document recommendations
- Card-based search results with pagination
- Watch folder monitoring for auto-ingestion
- Multiple document format support via Tika

### Not Implemented / WIP
- No user management or authentication
- No multi-user support
- Email ingestion (commented out in docker-compose)
- No annotation or commenting system
- No workflow engine
- No document versioning
- No collaboration features

---

## 5. UI/UX

- **Angular v11.x** frontend with modern card-based design
- **Search-first interface**: Prominent search bar with faceted sidebar
- **Dashboard**: Clean layout with sorting options
- **Document Detail View**: Preview with page navigation, metadata panel, tags, similar documents
- **Responsive**: Works on desktop and tablet via web browser

---

## 6. Strengths (Features to Adopt)

1. **Non-destructive processing** - Original files never modified (unique differentiator)
2. **True microservices architecture** - Independently scalable components
3. **S3-compatible storage** - MinIO provides industry-standard storage API
4. **WORM storage support** - Write-Once-Read-Multiple for compliance
5. **Convention over Configuration** - Sensible defaults, minimal setup
6. **Cloud-native design** - Docker + Kubernetes ready
7. **Message queue architecture** - Scalable, decoupled processing via RabbitMQ
8. **Similar document recommendations** - Content-based discovery

---

## 7. Weaknesses / Gaps

1. No authentication or authorization
2. No multi-user support
3. No workflow engine
4. No document versioning
5. No metadata system beyond tags
6. No collaboration features (comments, sharing)
7. Limited file type support
8. No email integration (WIP)
9. No plugin/extension system
10. Outdated Angular version (v11)
11. Project appears largely unmaintained (v0.1.0 status)
12. Separate repos for each service makes contribution harder
