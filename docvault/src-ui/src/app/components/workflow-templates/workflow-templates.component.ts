import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { WorkflowService } from '../../services/workflow.service';
import { WorkflowTemplate } from '../../models/workflow.model';

@Component({
  selector: 'app-workflow-templates',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  templateUrl: './workflow-templates.component.html',
})
export class WorkflowTemplatesComponent implements OnInit {
  templates = signal<WorkflowTemplate[]>([]);
  loading = signal(true);

  // Create form
  showCreate = signal(false);
  newLabel = signal('');
  newAutoLaunch = signal(false);

  constructor(private workflowService: WorkflowService) {}

  ngOnInit(): void {
    this.loadTemplates();
  }

  loadTemplates(): void {
    this.loading.set(true);
    this.workflowService.getTemplates().subscribe({
      next: (res) => {
        this.templates.set(res.results);
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
  }

  createTemplate(): void {
    const label = this.newLabel().trim();
    if (!label) return;

    this.workflowService
      .createTemplate({ label, auto_launch: this.newAutoLaunch() })
      .subscribe({
        next: () => {
          this.newLabel.set('');
          this.newAutoLaunch.set(false);
          this.showCreate.set(false);
          this.loadTemplates();
        },
      });
  }

  deleteTemplate(id: number, label: string): void {
    if (!confirm(`Delete workflow template "${label}"?`)) return;
    this.workflowService.deleteTemplate(id).subscribe({
      next: () => this.loadTemplates(),
    });
  }
}
