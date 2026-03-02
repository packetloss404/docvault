import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { WorkflowService } from '../../services/workflow.service';
import {
  WorkflowState,
  WorkflowTemplate,
  WorkflowTransition,
} from '../../models/workflow.model';

@Component({
  selector: 'app-workflow-detail',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  templateUrl: './workflow-detail.component.html',
})
export class WorkflowDetailComponent implements OnInit {
  template = signal<WorkflowTemplate | null>(null);
  states = signal<WorkflowState[]>([]);
  transitions = signal<WorkflowTransition[]>([]);
  loading = signal(true);
  activeTab = signal<'states' | 'transitions'>('states');

  // Add state form
  newStateLabel = signal('');
  newStateInitial = signal(false);
  newStateFinal = signal(false);
  newStateCompletion = signal(0);

  // Add transition form
  newTransLabel = signal('');
  newTransOrigin = signal<number | null>(null);
  newTransDest = signal<number | null>(null);
  newTransCondition = signal('');

  // Edit mode
  editingLabel = signal(false);
  editLabel = signal('');
  editAutoLaunch = signal(false);

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private workflowService: WorkflowService,
  ) {}

  ngOnInit(): void {
    const id = Number(this.route.snapshot.paramMap.get('id'));
    if (id) {
      this.loadTemplate(id);
      this.loadStates(id);
      this.loadTransitions(id);
    }
  }

  get templateId(): number {
    return this.template()?.id ?? 0;
  }

  loadTemplate(id: number): void {
    this.workflowService.getTemplate(id).subscribe({
      next: (t) => {
        this.template.set(t);
        this.loading.set(false);
      },
      error: () => {
        this.loading.set(false);
        this.router.navigate(['/workflows']);
      },
    });
  }

  loadStates(id: number): void {
    this.workflowService.getStates(id).subscribe({
      next: (states) => this.states.set(states),
    });
  }

  loadTransitions(id: number): void {
    this.workflowService.getTransitions(id).subscribe({
      next: (transitions) => this.transitions.set(transitions),
    });
  }

  startEditLabel(): void {
    const t = this.template();
    if (!t) return;
    this.editLabel.set(t.label);
    this.editAutoLaunch.set(t.auto_launch);
    this.editingLabel.set(true);
  }

  saveLabel(): void {
    const t = this.template();
    if (!t) return;
    this.workflowService
      .updateTemplate(t.id, {
        label: this.editLabel(),
        auto_launch: this.editAutoLaunch(),
      })
      .subscribe({
        next: (updated) => {
          this.template.set(updated);
          this.editingLabel.set(false);
        },
      });
  }

  addState(): void {
    const label = this.newStateLabel().trim();
    if (!label) return;
    this.workflowService
      .createState(this.templateId, {
        label,
        initial: this.newStateInitial(),
        final: this.newStateFinal(),
        completion: this.newStateCompletion(),
      })
      .subscribe({
        next: () => {
          this.newStateLabel.set('');
          this.newStateInitial.set(false);
          this.newStateFinal.set(false);
          this.newStateCompletion.set(0);
          this.loadStates(this.templateId);
        },
      });
  }

  deleteState(stateId: number): void {
    this.workflowService.deleteState(this.templateId, stateId).subscribe({
      next: () => this.loadStates(this.templateId),
    });
  }

  addTransition(): void {
    const label = this.newTransLabel().trim();
    const origin = this.newTransOrigin();
    const dest = this.newTransDest();
    if (!label || !origin || !dest) return;

    this.workflowService
      .createTransition(this.templateId, {
        label,
        origin_state: origin,
        destination_state: dest,
        condition: this.newTransCondition(),
      })
      .subscribe({
        next: () => {
          this.newTransLabel.set('');
          this.newTransOrigin.set(null);
          this.newTransDest.set(null);
          this.newTransCondition.set('');
          this.loadTransitions(this.templateId);
        },
      });
  }

  deleteTransition(transitionId: number): void {
    this.workflowService.deleteTransition(this.templateId, transitionId).subscribe({
      next: () => this.loadTransitions(this.templateId),
    });
  }

  setTab(tab: 'states' | 'transitions'): void {
    this.activeTab.set(tab);
  }
}
