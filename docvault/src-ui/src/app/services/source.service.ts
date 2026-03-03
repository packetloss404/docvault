import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';
import { PaginatedResponse } from '../models/document.model';
import {
  MailAccount,
  MailRule,
  Source,
  WatchFolderSource,
  WorkflowRule,
  WorkflowRuleAction,
  WorkflowTrigger,
} from '../models/source.model';

@Injectable({ providedIn: 'root' })
export class SourceService {
  private readonly sourceUrl = `${environment.apiUrl}/sources`;
  private readonly mailUrl = `${environment.apiUrl}/mail-accounts`;
  private readonly ruleUrl = `${environment.apiUrl}/workflow-rules`;

  constructor(private http: HttpClient) {}

  // --- Sources ---

  getSources(): Observable<PaginatedResponse<Source>> {
    return this.http.get<PaginatedResponse<Source>>(`${this.sourceUrl}/`);
  }

  getSource(id: number): Observable<Source> {
    return this.http.get<Source>(`${this.sourceUrl}/${id}/`);
  }

  createSource(data: Partial<Source>): Observable<Source> {
    return this.http.post<Source>(`${this.sourceUrl}/`, data);
  }

  updateSource(id: number, data: Partial<Source>): Observable<Source> {
    return this.http.patch<Source>(`${this.sourceUrl}/${id}/`, data);
  }

  deleteSource(id: number): Observable<void> {
    return this.http.delete<void>(`${this.sourceUrl}/${id}/`);
  }

  // --- Watch Folders ---

  getWatchFolder(sourceId: number): Observable<WatchFolderSource> {
    return this.http.get<WatchFolderSource>(
      `${this.sourceUrl}/${sourceId}/watch-folder/`,
    );
  }

  createWatchFolder(
    sourceId: number,
    data: Partial<WatchFolderSource>,
  ): Observable<WatchFolderSource> {
    return this.http.post<WatchFolderSource>(
      `${this.sourceUrl}/${sourceId}/watch-folder/`,
      data,
    );
  }

  updateWatchFolder(
    sourceId: number,
    data: Partial<WatchFolderSource>,
  ): Observable<WatchFolderSource> {
    return this.http.patch<WatchFolderSource>(
      `${this.sourceUrl}/${sourceId}/watch-folder/`,
      data,
    );
  }

  // --- Mail Accounts ---

  getMailAccounts(): Observable<PaginatedResponse<MailAccount>> {
    return this.http.get<PaginatedResponse<MailAccount>>(`${this.mailUrl}/`);
  }

  getMailAccount(id: number): Observable<MailAccount> {
    return this.http.get<MailAccount>(`${this.mailUrl}/${id}/`);
  }

  createMailAccount(data: Partial<MailAccount>): Observable<MailAccount> {
    return this.http.post<MailAccount>(`${this.mailUrl}/`, data);
  }

  updateMailAccount(
    id: number,
    data: Partial<MailAccount>,
  ): Observable<MailAccount> {
    return this.http.patch<MailAccount>(`${this.mailUrl}/${id}/`, data);
  }

  deleteMailAccount(id: number): Observable<void> {
    return this.http.delete<void>(`${this.mailUrl}/${id}/`);
  }

  testMailConnection(id: number): Observable<{ success: boolean; message: string }> {
    return this.http.post<{ success: boolean; message: string }>(
      `${this.mailUrl}/${id}/test-connection/`,
      {},
    );
  }

  // --- Mail Rules ---

  getMailRules(accountId: number): Observable<MailRule[]> {
    return this.http.get<MailRule[]>(
      `${this.mailUrl}/${accountId}/rules/`,
    );
  }

  createMailRule(
    accountId: number,
    data: Partial<MailRule>,
  ): Observable<MailRule> {
    return this.http.post<MailRule>(
      `${this.mailUrl}/${accountId}/rules/`,
      data,
    );
  }

  updateMailRule(
    accountId: number,
    ruleId: number,
    data: Partial<MailRule>,
  ): Observable<MailRule> {
    return this.http.patch<MailRule>(
      `${this.mailUrl}/${accountId}/rules/${ruleId}/`,
      data,
    );
  }

  deleteMailRule(accountId: number, ruleId: number): Observable<void> {
    return this.http.delete<void>(
      `${this.mailUrl}/${accountId}/rules/${ruleId}/`,
    );
  }

  // --- Workflow Rules ---

  getWorkflowRules(): Observable<PaginatedResponse<WorkflowRule>> {
    return this.http.get<PaginatedResponse<WorkflowRule>>(`${this.ruleUrl}/`);
  }

  getWorkflowRule(id: number): Observable<WorkflowRule> {
    return this.http.get<WorkflowRule>(`${this.ruleUrl}/${id}/`);
  }

  createWorkflowRule(data: Partial<WorkflowRule>): Observable<WorkflowRule> {
    return this.http.post<WorkflowRule>(`${this.ruleUrl}/`, data);
  }

  updateWorkflowRule(
    id: number,
    data: Partial<WorkflowRule>,
  ): Observable<WorkflowRule> {
    return this.http.patch<WorkflowRule>(`${this.ruleUrl}/${id}/`, data);
  }

  deleteWorkflowRule(id: number): Observable<void> {
    return this.http.delete<void>(`${this.ruleUrl}/${id}/`);
  }

  // --- Triggers ---

  getTriggers(ruleId: number): Observable<WorkflowTrigger[]> {
    return this.http.get<WorkflowTrigger[]>(
      `${this.ruleUrl}/${ruleId}/triggers/`,
    );
  }

  createTrigger(
    ruleId: number,
    data: Partial<WorkflowTrigger>,
  ): Observable<WorkflowTrigger> {
    return this.http.post<WorkflowTrigger>(
      `${this.ruleUrl}/${ruleId}/triggers/`,
      data,
    );
  }

  deleteTrigger(ruleId: number, triggerId: number): Observable<void> {
    return this.http.delete<void>(
      `${this.ruleUrl}/${ruleId}/triggers/${triggerId}/`,
    );
  }

  // --- Rule Actions ---

  getRuleActions(ruleId: number): Observable<WorkflowRuleAction[]> {
    return this.http.get<WorkflowRuleAction[]>(
      `${this.ruleUrl}/${ruleId}/actions/`,
    );
  }

  createRuleAction(
    ruleId: number,
    data: Partial<WorkflowRuleAction>,
  ): Observable<WorkflowRuleAction> {
    return this.http.post<WorkflowRuleAction>(
      `${this.ruleUrl}/${ruleId}/actions/`,
      data,
    );
  }

  deleteRuleAction(ruleId: number, actionId: number): Observable<void> {
    return this.http.delete<void>(
      `${this.ruleUrl}/${ruleId}/actions/${actionId}/`,
    );
  }
}
