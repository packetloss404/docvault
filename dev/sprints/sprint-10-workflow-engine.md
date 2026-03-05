# Sprint 10: Workflow State Machine

## Phase: 4 - Workflow & Automation
## Duration: 2 weeks
## Prerequisites: Sprint 9 (Search & Saved Views)

---

## Sprint Goal
Build the workflow state machine engine from Mayan EDMS: templates, states, transitions with conditions, state actions (on_entry/on_exit), escalation with timeouts, transition fields for user input, and the workflow instance runtime with audit logging.

---

## Context for Agents

### Read Before Starting
- `/doc/product-spec.md` - Section 2.5 (Workflow Module - State Machine Engine)
- `/doc/research/mayan-edms-analysis.md` - Section 6 (Workflow Engine) - the pattern we're implementing
- This is the most complex data model in the system

---

## Tasks

### Task 10.1: Workflow Template & State Models
- Create `workflows/` app
- WorkflowTemplate: name, auto_launch, document_types (M2M), enabled
- WorkflowState: template (FK), label, initial (bool), final (bool), completion (0-100)
- Validation: exactly one initial state per template, at least one final state

### Task 10.2: Transition & Condition Models
- WorkflowTransition: template (FK), origin_state (FK), destination_state (FK), label, condition (TextField for Python expression)
- Condition evaluator: safe evaluation of Python expressions against workflow context
- WorkflowTransitionField: transition (FK), name, label, field_type, required, help_text
- Field types: text, textarea, select, number, date, boolean

### Task 10.3: State Actions & Escalation
- WorkflowStateAction: state (FK), label, when (ON_ENTRY/ON_EXIT), backend_class (dotted path), backend_data (JSON), enabled
- Built-in action implementations:
  - SetDocumentPropertiesAction: modify title, description, language
  - SetMetadataAction: set metadata values
  - AddTagAction: add tags to document
  - AddToCabinetAction: file in cabinet
  - LaunchWorkflowAction: trigger another workflow
  - SendEmailAction: send email notification
  - WebhookAction: HTTP POST/PUT to external URL
- WorkflowStateEscalation: state (FK), destination_state (FK), delay_amount, delay_unit, condition, enabled
- Celery task to check and process escalations (runs every 5 minutes)

### Task 10.4: Workflow Instance & Execution Engine
- WorkflowInstance: template (FK), document (FK), current_state (FK), context (JSONField), created_at
- WorkflowInstanceLogEntry: instance (FK), from_state, to_state, actor (FK), timestamp, comment, transition_field_values (JSON)
- Engine methods:
  - `launch(document)`: Create instance, set initial state, execute entry actions
  - `transition(instance, transition, actor, field_values)`: Execute exit actions, move to new state, execute entry actions, log
  - `get_available_transitions(instance, user)`: Return valid transitions (evaluate conditions)
  - `check_escalations()`: Find overdue instances, auto-transition

### Task 10.5: Workflow API
- WorkflowTemplate CRUD ViewSet
- WorkflowState nested ViewSet
- WorkflowTransition nested ViewSet
- WorkflowStateAction nested ViewSet
- WorkflowInstance ViewSet (per-document)
- POST `/api/v1/workflow_instances/{id}/transition/` - Execute transition
- GET `/api/v1/workflow_instances/{id}/log/` - Audit log
- GET `/api/v1/documents/{id}/workflows/` - Active workflows for document
- Celery task registration for escalation processing

### Task 10.6: Frontend Workflow Display
- Workflow status indicator on document detail page
- Current state display with completion percentage
- Available transitions as action buttons
- Transition dialog (shows custom fields, condition warnings)
- Workflow log/history timeline
- Workflow template list page (admin view)

---

## Definition of Done
- [ ] Workflow templates with states and transitions can be created
- [ ] Conditions evaluate correctly (safe Python expressions)
- [ ] State actions execute on entry/exit
- [ ] Escalation auto-transitions after timeout
- [ ] Transition fields collect user input
- [ ] Workflow instances track per-document state
- [ ] Log entries record all transitions with actors
- [ ] API endpoints for all workflow operations work
- [ ] Frontend shows workflow status and allows transitions
- [ ] All features have unit tests
