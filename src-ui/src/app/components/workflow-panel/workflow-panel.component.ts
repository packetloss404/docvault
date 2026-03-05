import { Component, Input, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { WorkflowService } from '../../services/workflow.service';
import {
  WorkflowInstance,
  WorkflowInstanceLogEntry,
  WorkflowTemplate,
  WorkflowTransition,
  WorkflowTransitionField,
} from '../../models/workflow.model';

@Component({
  selector: 'app-workflow-panel',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './workflow-panel.component.html',
})
export class WorkflowPanelComponent implements OnInit {
  @Input() documentId!: number;

  instances = signal<WorkflowInstance[]>([]);
  templates = signal<WorkflowTemplate[]>([]);
  loading = signal(true);

  // Selected instance details
  selectedInstance = signal<WorkflowInstance | null>(null);
  availableTransitions = signal<WorkflowTransition[]>([]);
  logEntries = signal<WorkflowInstanceLogEntry[]>([]);

  // Transition dialog
  showTransitionDialog = signal(false);
  selectedTransition = signal<WorkflowTransition | null>(null);
  transitionFields = signal<WorkflowTransitionField[]>([]);
  transitionFieldValues = signal<Record<string, string>>({});
  transitionComment = signal('');

  // Launch
  launchTemplateId = signal<number | null>(null);

  constructor(private workflowService: WorkflowService) {}

  ngOnInit(): void {
    this.loadInstances();
    this.loadTemplates();
  }

  loadInstances(): void {
    this.loading.set(true);
    this.workflowService.getDocumentWorkflows(this.documentId).subscribe({
      next: (instances) => {
        this.instances.set(instances);
        this.loading.set(false);
        if (instances.length > 0 && !this.selectedInstance()) {
          this.selectInstance(instances[0]);
        }
      },
      error: () => this.loading.set(false),
    });
  }

  loadTemplates(): void {
    this.workflowService.getTemplates().subscribe({
      next: (res) => this.templates.set(res.results),
    });
  }

  selectInstance(instance: WorkflowInstance): void {
    this.selectedInstance.set(instance);
    this.loadAvailableTransitions(instance);
    this.loadLog(instance);
  }

  loadAvailableTransitions(instance: WorkflowInstance): void {
    this.workflowService
      .getAvailableTransitions(this.documentId, instance.id)
      .subscribe({
        next: (transitions) => this.availableTransitions.set(transitions),
      });
  }

  loadLog(instance: WorkflowInstance): void {
    this.workflowService.getWorkflowLog(this.documentId, instance.id).subscribe({
      next: (entries) => this.logEntries.set(entries),
    });
  }

  launchWorkflow(): void {
    const templateId = this.launchTemplateId();
    if (!templateId) return;

    this.workflowService.launchWorkflow(this.documentId, templateId).subscribe({
      next: (instance) => {
        this.launchTemplateId.set(null);
        this.loadInstances();
        this.selectInstance(instance);
      },
    });
  }

  openTransitionDialog(transition: WorkflowTransition): void {
    this.selectedTransition.set(transition);
    this.transitionFieldValues.set({});
    this.transitionComment.set('');

    // Load fields for this transition
    const inst = this.selectedInstance();
    if (inst) {
      this.workflowService
        .getTransitionFields(inst.workflow, transition.id)
        .subscribe({
          next: (fields) => {
            this.transitionFields.set(fields);
            const defaults: Record<string, string> = {};
            fields.forEach((f) => {
              defaults[f.name] = f.default || '';
            });
            this.transitionFieldValues.set(defaults);
          },
        });
    }
    this.showTransitionDialog.set(true);
  }

  executeTransition(): void {
    const inst = this.selectedInstance();
    const trans = this.selectedTransition();
    if (!inst || !trans) return;

    this.workflowService
      .executeTransition(
        this.documentId,
        inst.id,
        trans.id,
        this.transitionFieldValues(),
        this.transitionComment(),
      )
      .subscribe({
        next: (updated) => {
          this.showTransitionDialog.set(false);
          this.selectedInstance.set(updated);
          this.loadInstances();
          this.loadAvailableTransitions(updated);
          this.loadLog(updated);
        },
      });
  }

  cancelTransitionDialog(): void {
    this.showTransitionDialog.set(false);
    this.selectedTransition.set(null);
  }

  setFieldValue(name: string, value: string): void {
    const current = this.transitionFieldValues();
    this.transitionFieldValues.set({ ...current, [name]: value });
  }
}
