import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';
import { PaginatedResponse } from '../models/document.model';
import {
  ActionBackend,
  WorkflowInstance,
  WorkflowInstanceLogEntry,
  WorkflowState,
  WorkflowStateAction,
  WorkflowStateEscalation,
  WorkflowTemplate,
  WorkflowTransition,
  WorkflowTransitionField,
} from '../models/workflow.model';

@Injectable({ providedIn: 'root' })
export class WorkflowService {
  private readonly baseUrl = `${environment.apiUrl}/workflow-templates`;
  private readonly docUrl = `${environment.apiUrl}/documents`;
  private readonly backendsUrl = `${environment.apiUrl}/workflow-action-backends`;

  constructor(private http: HttpClient) {}

  // --- Templates ---

  getTemplates(): Observable<PaginatedResponse<WorkflowTemplate>> {
    return this.http.get<PaginatedResponse<WorkflowTemplate>>(`${this.baseUrl}/`);
  }

  getTemplate(id: number): Observable<WorkflowTemplate> {
    return this.http.get<WorkflowTemplate>(`${this.baseUrl}/${id}/`);
  }

  createTemplate(data: Partial<WorkflowTemplate>): Observable<WorkflowTemplate> {
    return this.http.post<WorkflowTemplate>(`${this.baseUrl}/`, data);
  }

  updateTemplate(id: number, data: Partial<WorkflowTemplate>): Observable<WorkflowTemplate> {
    return this.http.patch<WorkflowTemplate>(`${this.baseUrl}/${id}/`, data);
  }

  deleteTemplate(id: number): Observable<void> {
    return this.http.delete<void>(`${this.baseUrl}/${id}/`);
  }

  // --- States ---

  getStates(templateId: number): Observable<WorkflowState[]> {
    return this.http.get<WorkflowState[]>(
      `${this.baseUrl}/${templateId}/states/`,
    );
  }

  createState(templateId: number, data: Partial<WorkflowState>): Observable<WorkflowState> {
    return this.http.post<WorkflowState>(
      `${this.baseUrl}/${templateId}/states/`,
      data,
    );
  }

  updateState(templateId: number, stateId: number, data: Partial<WorkflowState>): Observable<WorkflowState> {
    return this.http.patch<WorkflowState>(
      `${this.baseUrl}/${templateId}/states/${stateId}/`,
      data,
    );
  }

  deleteState(templateId: number, stateId: number): Observable<void> {
    return this.http.delete<void>(
      `${this.baseUrl}/${templateId}/states/${stateId}/`,
    );
  }

  // --- Transitions ---

  getTransitions(templateId: number): Observable<WorkflowTransition[]> {
    return this.http.get<WorkflowTransition[]>(
      `${this.baseUrl}/${templateId}/transitions/`,
    );
  }

  createTransition(templateId: number, data: Partial<WorkflowTransition>): Observable<WorkflowTransition> {
    return this.http.post<WorkflowTransition>(
      `${this.baseUrl}/${templateId}/transitions/`,
      data,
    );
  }

  updateTransition(templateId: number, transitionId: number, data: Partial<WorkflowTransition>): Observable<WorkflowTransition> {
    return this.http.patch<WorkflowTransition>(
      `${this.baseUrl}/${templateId}/transitions/${transitionId}/`,
      data,
    );
  }

  deleteTransition(templateId: number, transitionId: number): Observable<void> {
    return this.http.delete<void>(
      `${this.baseUrl}/${templateId}/transitions/${transitionId}/`,
    );
  }

  // --- Transition Fields ---

  getTransitionFields(templateId: number, transitionId: number): Observable<WorkflowTransitionField[]> {
    return this.http.get<WorkflowTransitionField[]>(
      `${this.baseUrl}/${templateId}/transitions/${transitionId}/fields/`,
    );
  }

  createTransitionField(templateId: number, transitionId: number, data: Partial<WorkflowTransitionField>): Observable<WorkflowTransitionField> {
    return this.http.post<WorkflowTransitionField>(
      `${this.baseUrl}/${templateId}/transitions/${transitionId}/fields/`,
      data,
    );
  }

  deleteTransitionField(templateId: number, transitionId: number, fieldId: number): Observable<void> {
    return this.http.delete<void>(
      `${this.baseUrl}/${templateId}/transitions/${transitionId}/fields/${fieldId}/`,
    );
  }

  // --- State Actions ---

  getStateActions(templateId: number, stateId: number): Observable<WorkflowStateAction[]> {
    return this.http.get<WorkflowStateAction[]>(
      `${this.baseUrl}/${templateId}/states/${stateId}/actions/`,
    );
  }

  createStateAction(templateId: number, stateId: number, data: Partial<WorkflowStateAction>): Observable<WorkflowStateAction> {
    return this.http.post<WorkflowStateAction>(
      `${this.baseUrl}/${templateId}/states/${stateId}/actions/`,
      data,
    );
  }

  deleteStateAction(templateId: number, stateId: number, actionId: number): Observable<void> {
    return this.http.delete<void>(
      `${this.baseUrl}/${templateId}/states/${stateId}/actions/${actionId}/`,
    );
  }

  // --- State Escalations ---

  getStateEscalations(templateId: number, stateId: number): Observable<WorkflowStateEscalation[]> {
    return this.http.get<WorkflowStateEscalation[]>(
      `${this.baseUrl}/${templateId}/states/${stateId}/escalations/`,
    );
  }

  createStateEscalation(templateId: number, stateId: number, data: Partial<WorkflowStateEscalation>): Observable<WorkflowStateEscalation> {
    return this.http.post<WorkflowStateEscalation>(
      `${this.baseUrl}/${templateId}/states/${stateId}/escalations/`,
      data,
    );
  }

  deleteStateEscalation(templateId: number, stateId: number, escalationId: number): Observable<void> {
    return this.http.delete<void>(
      `${this.baseUrl}/${templateId}/states/${stateId}/escalations/${escalationId}/`,
    );
  }

  // --- Document Workflows ---

  getDocumentWorkflows(documentId: number): Observable<WorkflowInstance[]> {
    return this.http.get<WorkflowInstance[]>(
      `${this.docUrl}/${documentId}/workflows/`,
    );
  }

  launchWorkflow(documentId: number, templateId: number): Observable<WorkflowInstance> {
    return this.http.post<WorkflowInstance>(
      `${this.docUrl}/${documentId}/workflows/launch/`,
      { workflow_template_id: templateId },
    );
  }

  executeTransition(
    documentId: number,
    instanceId: number,
    transitionId: number,
    fieldValues: Record<string, string> = {},
    comment: string = '',
  ): Observable<WorkflowInstance> {
    return this.http.post<WorkflowInstance>(
      `${this.docUrl}/${documentId}/workflows/${instanceId}/transitions/${transitionId}/execute/`,
      { field_values: fieldValues, comment },
    );
  }

  getWorkflowLog(documentId: number, instanceId: number): Observable<WorkflowInstanceLogEntry[]> {
    return this.http.get<WorkflowInstanceLogEntry[]>(
      `${this.docUrl}/${documentId}/workflows/${instanceId}/log/`,
    );
  }

  getAvailableTransitions(documentId: number, instanceId: number): Observable<WorkflowTransition[]> {
    return this.http.get<WorkflowTransition[]>(
      `${this.docUrl}/${documentId}/workflows/${instanceId}/available-transitions/`,
    );
  }

  // --- Action Backends ---

  getActionBackends(): Observable<ActionBackend[]> {
    return this.http.get<ActionBackend[]>(`${this.backendsUrl}/`);
  }
}
