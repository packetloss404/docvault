import { TestBed } from '@angular/core/testing';
import {
  HttpTestingController,
  provideHttpClientTesting,
} from '@angular/common/http/testing';
import { provideHttpClient } from '@angular/common/http';
import { WorkflowService } from './workflow.service';
import { environment } from '../../environments/environment';

const API = environment.apiUrl;
const BASE = `${API}/workflow-templates`;
const DOC = `${API}/documents`;
const BACKENDS = `${API}/workflow-action-backends`;

describe('WorkflowService', () => {
  let service: WorkflowService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    service = TestBed.inject(WorkflowService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  // --- Templates ---

  describe('getTemplates', () => {
    it('sends GET to /workflow-templates/', () => {
      service.getTemplates().subscribe();
      const req = httpMock.expectOne(`${BASE}/`);
      expect(req.request.method).toBe('GET');
      req.flush({ count: 0, results: [] });
    });
  });

  describe('getTemplate', () => {
    it('sends GET to /workflow-templates/:id/', () => {
      service.getTemplate(1).subscribe();
      const req = httpMock.expectOne(`${BASE}/1/`);
      expect(req.request.method).toBe('GET');
      req.flush({ id: 1, label: 'Approval', internal_name: 'approval', auto_launch: false, document_type_ids: [], state_count: 0, transition_count: 0, created_at: '', updated_at: '' });
    });
  });

  describe('createTemplate', () => {
    it('sends POST to /workflow-templates/ with body', () => {
      const data = { label: 'Review', internal_name: 'review' };
      service.createTemplate(data).subscribe();
      const req = httpMock.expectOne(`${BASE}/`);
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual(data);
      req.flush({ id: 2, ...data, auto_launch: false, document_type_ids: [], state_count: 0, transition_count: 0, created_at: '', updated_at: '' });
    });
  });

  describe('updateTemplate', () => {
    it('sends PATCH to /workflow-templates/:id/ with body', () => {
      const data = { label: 'Updated' };
      service.updateTemplate(1, data).subscribe();
      const req = httpMock.expectOne(`${BASE}/1/`);
      expect(req.request.method).toBe('PATCH');
      expect(req.request.body).toEqual(data);
      req.flush({ id: 1, label: 'Updated', internal_name: 'review', auto_launch: false, document_type_ids: [], state_count: 0, transition_count: 0, created_at: '', updated_at: '' });
    });
  });

  describe('deleteTemplate', () => {
    it('sends DELETE to /workflow-templates/:id/', () => {
      service.deleteTemplate(1).subscribe();
      const req = httpMock.expectOne(`${BASE}/1/`);
      expect(req.request.method).toBe('DELETE');
      req.flush(null);
    });
  });

  // --- States ---

  describe('getStates', () => {
    it('sends GET to /workflow-templates/:templateId/states/', () => {
      service.getStates(1).subscribe();
      const req = httpMock.expectOne(`${BASE}/1/states/`);
      expect(req.request.method).toBe('GET');
      req.flush([]);
    });
  });

  describe('createState', () => {
    it('sends POST to /workflow-templates/:templateId/states/ with body', () => {
      const data = { label: 'Draft', initial: true, final: false, completion: 0 };
      service.createState(1, data).subscribe();
      const req = httpMock.expectOne(`${BASE}/1/states/`);
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual(data);
      req.flush({ id: 10, workflow: 1, ...data });
    });
  });

  describe('updateState', () => {
    it('sends PATCH to /workflow-templates/:templateId/states/:stateId/ with body', () => {
      const data = { label: 'In Review' };
      service.updateState(1, 10, data).subscribe();
      const req = httpMock.expectOne(`${BASE}/1/states/10/`);
      expect(req.request.method).toBe('PATCH');
      expect(req.request.body).toEqual(data);
      req.flush({ id: 10, workflow: 1, label: 'In Review', initial: false, final: false, completion: 50 });
    });
  });

  describe('deleteState', () => {
    it('sends DELETE to /workflow-templates/:templateId/states/:stateId/', () => {
      service.deleteState(1, 10).subscribe();
      const req = httpMock.expectOne(`${BASE}/1/states/10/`);
      expect(req.request.method).toBe('DELETE');
      req.flush(null);
    });
  });

  // --- Transitions ---

  describe('getTransitions', () => {
    it('sends GET to /workflow-templates/:templateId/transitions/', () => {
      service.getTransitions(1).subscribe();
      const req = httpMock.expectOne(`${BASE}/1/transitions/`);
      expect(req.request.method).toBe('GET');
      req.flush([]);
    });
  });

  describe('createTransition', () => {
    it('sends POST to /workflow-templates/:templateId/transitions/ with body', () => {
      const data = { label: 'Approve', origin_state: 10, destination_state: 11 };
      service.createTransition(1, data).subscribe();
      const req = httpMock.expectOne(`${BASE}/1/transitions/`);
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual(data);
      req.flush({ id: 20, workflow: 1, ...data, origin_state_label: 'Draft', destination_state_label: 'Approved', condition: '' });
    });
  });

  describe('updateTransition', () => {
    it('sends PATCH to /workflow-templates/:templateId/transitions/:transitionId/ with body', () => {
      const data = { label: 'Reject' };
      service.updateTransition(1, 20, data).subscribe();
      const req = httpMock.expectOne(`${BASE}/1/transitions/20/`);
      expect(req.request.method).toBe('PATCH');
      expect(req.request.body).toEqual(data);
      req.flush({ id: 20, workflow: 1, label: 'Reject', origin_state: 10, origin_state_label: 'Draft', destination_state: 12, destination_state_label: 'Rejected', condition: '' });
    });
  });

  describe('deleteTransition', () => {
    it('sends DELETE to /workflow-templates/:templateId/transitions/:transitionId/', () => {
      service.deleteTransition(1, 20).subscribe();
      const req = httpMock.expectOne(`${BASE}/1/transitions/20/`);
      expect(req.request.method).toBe('DELETE');
      req.flush(null);
    });
  });

  // --- Transition Fields ---

  describe('getTransitionFields', () => {
    it('sends GET to /workflow-templates/:templateId/transitions/:transitionId/fields/', () => {
      service.getTransitionFields(1, 20).subscribe();
      const req = httpMock.expectOne(`${BASE}/1/transitions/20/fields/`);
      expect(req.request.method).toBe('GET');
      req.flush([]);
    });
  });

  describe('createTransitionField', () => {
    it('sends POST to /workflow-templates/:templateId/transitions/:transitionId/fields/ with body', () => {
      const data = { name: 'comment', label: 'Comment', field_type: 'text' as const, required: false, default: '', help_text: '' };
      service.createTransitionField(1, 20, data).subscribe();
      const req = httpMock.expectOne(`${BASE}/1/transitions/20/fields/`);
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual(data);
      req.flush({ id: 30, transition: 20, ...data });
    });
  });

  describe('deleteTransitionField', () => {
    it('sends DELETE to /workflow-templates/:templateId/transitions/:transitionId/fields/:fieldId/', () => {
      service.deleteTransitionField(1, 20, 30).subscribe();
      const req = httpMock.expectOne(`${BASE}/1/transitions/20/fields/30/`);
      expect(req.request.method).toBe('DELETE');
      req.flush(null);
    });
  });

  // --- State Actions ---

  describe('getStateActions', () => {
    it('sends GET to /workflow-templates/:templateId/states/:stateId/actions/', () => {
      service.getStateActions(1, 10).subscribe();
      const req = httpMock.expectOne(`${BASE}/1/states/10/actions/`);
      expect(req.request.method).toBe('GET');
      req.flush([]);
    });
  });

  describe('createStateAction', () => {
    it('sends POST to /workflow-templates/:templateId/states/:stateId/actions/ with body', () => {
      const data = { label: 'Send Email', enabled: true, when: 'on_entry' as const, backend_path: 'email.backend', backend_data: {}, condition: '', order: 1 };
      service.createStateAction(1, 10, data).subscribe();
      const req = httpMock.expectOne(`${BASE}/1/states/10/actions/`);
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual(data);
      req.flush({ id: 40, state: 10, ...data });
    });
  });

  describe('deleteStateAction', () => {
    it('sends DELETE to /workflow-templates/:templateId/states/:stateId/actions/:actionId/', () => {
      service.deleteStateAction(1, 10, 40).subscribe();
      const req = httpMock.expectOne(`${BASE}/1/states/10/actions/40/`);
      expect(req.request.method).toBe('DELETE');
      req.flush(null);
    });
  });

  // --- State Escalations ---

  describe('getStateEscalations', () => {
    it('sends GET to /workflow-templates/:templateId/states/:stateId/escalations/', () => {
      service.getStateEscalations(1, 10).subscribe();
      const req = httpMock.expectOne(`${BASE}/1/states/10/escalations/`);
      expect(req.request.method).toBe('GET');
      req.flush([]);
    });
  });

  describe('createStateEscalation', () => {
    it('sends POST to /workflow-templates/:templateId/states/:stateId/escalations/ with body', () => {
      const data = { transition: 20, enabled: true, amount: 2, unit: 'days' as const, condition: '', comment: 'Auto escalate', priority: 1 };
      service.createStateEscalation(1, 10, data).subscribe();
      const req = httpMock.expectOne(`${BASE}/1/states/10/escalations/`);
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual(data);
      req.flush({ id: 50, state: 10, ...data });
    });
  });

  describe('deleteStateEscalation', () => {
    it('sends DELETE to /workflow-templates/:templateId/states/:stateId/escalations/:escalationId/', () => {
      service.deleteStateEscalation(1, 10, 50).subscribe();
      const req = httpMock.expectOne(`${BASE}/1/states/10/escalations/50/`);
      expect(req.request.method).toBe('DELETE');
      req.flush(null);
    });
  });

  // --- Document Workflows ---

  describe('getDocumentWorkflows', () => {
    it('sends GET to /documents/:documentId/workflows/', () => {
      service.getDocumentWorkflows(99).subscribe();
      const req = httpMock.expectOne(`${DOC}/99/workflows/`);
      expect(req.request.method).toBe('GET');
      req.flush([]);
    });
  });

  describe('launchWorkflow', () => {
    it('sends POST to /documents/:documentId/workflows/launch/ with templateId', () => {
      service.launchWorkflow(99, 1).subscribe();
      const req = httpMock.expectOne(`${DOC}/99/workflows/launch/`);
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual({ workflow_template_id: 1 });
      req.flush({ id: 100, workflow: 1, workflow_label: 'Approval', document: 99, current_state: 10, current_state_label: 'Draft', completion: 0, is_complete: false, context: {}, launched_at: '', state_changed_at: '' });
    });
  });

  describe('executeTransition', () => {
    it('sends POST to /documents/:documentId/workflows/:instanceId/transitions/:transitionId/execute/ with defaults', () => {
      service.executeTransition(99, 100, 20).subscribe();
      const req = httpMock.expectOne(`${DOC}/99/workflows/100/transitions/20/execute/`);
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual({ field_values: {}, comment: '' });
      req.flush({});
    });

    it('sends POST with custom field_values and comment', () => {
      service.executeTransition(99, 100, 20, { note: 'ok' }, 'approved').subscribe();
      const req = httpMock.expectOne(`${DOC}/99/workflows/100/transitions/20/execute/`);
      expect(req.request.body).toEqual({ field_values: { note: 'ok' }, comment: 'approved' });
      req.flush({});
    });
  });

  describe('getWorkflowLog', () => {
    it('sends GET to /documents/:documentId/workflows/:instanceId/log/', () => {
      service.getWorkflowLog(99, 100).subscribe();
      const req = httpMock.expectOne(`${DOC}/99/workflows/100/log/`);
      expect(req.request.method).toBe('GET');
      req.flush([]);
    });
  });

  describe('getAvailableTransitions', () => {
    it('sends GET to /documents/:documentId/workflows/:instanceId/available-transitions/', () => {
      service.getAvailableTransitions(99, 100).subscribe();
      const req = httpMock.expectOne(`${DOC}/99/workflows/100/available-transitions/`);
      expect(req.request.method).toBe('GET');
      req.flush([]);
    });
  });

  // --- Action Backends ---

  describe('getActionBackends', () => {
    it('sends GET to /workflow-action-backends/', () => {
      service.getActionBackends().subscribe();
      const req = httpMock.expectOne(`${BACKENDS}/`);
      expect(req.request.method).toBe('GET');
      req.flush([]);
    });
  });
});
