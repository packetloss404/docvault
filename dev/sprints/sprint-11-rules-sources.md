# Sprint 11: Trigger-Action Rules & Sources

## Phase: 4 - Workflow & Automation
## Duration: 2 weeks
## Prerequisites: Sprint 10 (Workflow State Machine)

---

## Sprint Goal
Build the trigger-action workflow rules (from Paperless-ngx), implement document sources (watch folder, email/IMAP, staging folder, S3), and connect rule execution to the processing pipeline.

---

## Context for Agents

### Read Before Starting
- `/doc/product-spec.md` - Section 2.5 (Trigger-Action Engine) and 2.7 (Sources Module)
- `/doc/research/paperless-ngx-analysis.md` - Section 10 (Workflows) and Section 12 (Email Integration)
- `/doc/research/mayan-edms-analysis.md` - Section 9 (Sources) for source type patterns

---

## Tasks

### Task 11.1: WorkflowRule Model (Trigger-Action)
- WorkflowRule: name, enabled, triggers (M2M), actions (M2M), order
- WorkflowTrigger: type (CONSUMPTION/ADDED/UPDATED/SCHEDULED), filter_filename (glob), filter_path (glob), filter_has_tags (M2M), filter_has_correspondent (FK), filter_has_document_type (FK), filter_custom_field_query (JSON), match pattern, matching_algorithm, schedule settings
- WorkflowAction: type (ADD_TAG/REMOVE_TAG/SET_CORRESPONDENT/SET_TYPE/SET_PATH/SET_CUSTOM_FIELD/ASSIGN_PERMISSIONS/EMAIL/WEBHOOK/LAUNCH_WORKFLOW/RUN_SCRIPT), order, configuration (JSON)
- WorkflowActionEmail: subject, body (with placeholders), to
- WorkflowActionWebhook: url, method, headers (JSON), body (JSON)

### Task 11.2: Rule Execution Engine
- WorkflowTriggerPlugin (order 30): match consumption triggers, apply overrides
- Post-save signal on Document: match ADDED/UPDATED triggers, execute actions
- Celery task for SCHEDULED triggers (runs every 15 minutes)
- Placeholder engine: `{{ document.title }}`, `{{ document.correspondent }}`, `{{ document.tags }}`, `{{ document.created }}`
- Email action: send via Django email backend
- Webhook action: HTTP POST/PUT with timeout and error handling

### Task 11.3: Watch Folder Source
- Create `sources/` app
- Source base model: label, enabled, source_type
- WatchFolderSource: path, polling_interval, document_type (FK), tags (M2M)
- Management command: `document_consumer` daemon
- Celery periodic task: poll watch folders, submit new files to processing pipeline
- File locking to prevent duplicate processing
- Move processed files to "consumed" subdirectory or delete (configurable)

### Task 11.4: Email Source (IMAP)
- MailAccount model: name, imap_server, port, security (NONE/SSL/STARTTLS), username, password, account_type (IMAP/GMAIL_OAUTH/OUTLOOK_OAUTH)
- MailRule model: account (FK), folder, filter_from, filter_subject, filter_body, action (DOWNLOAD_ATTACHMENT/PROCESS_EMAIL), document_type (FK), tags (M2M)
- Celery periodic task: fetch mail every 10 minutes
- IMAP integration: connect, search, download attachments
- OAuth2 token refresh for Gmail/Outlook
- Mark processed emails (move to folder, mark read, delete - configurable)

### Task 11.5: Source CRUD API & Frontend
- Source CRUD ViewSet (polymorphic - different fields per source type)
- MailAccount CRUD ViewSet
- MailRule CRUD ViewSet
- Test connection endpoint for mail accounts
- Frontend: Source configuration page (list, create, edit, delete)
- Frontend: Mail account setup with OAuth flow
- Frontend: Watch folder configuration

---

## Definition of Done
- [ ] WorkflowRule with triggers and actions can be created
- [ ] CONSUMPTION triggers apply overrides during processing
- [ ] ADDED/UPDATED triggers execute post-save
- [ ] SCHEDULED triggers execute on schedule
- [ ] Email and webhook actions deliver correctly
- [ ] Watch folder source detects and processes new files
- [ ] Email source fetches and processes attachments
- [ ] Source CRUD API works
- [ ] Frontend source configuration pages work
- [ ] All features have unit tests
