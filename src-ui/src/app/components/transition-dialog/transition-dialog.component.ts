import { Component, EventEmitter, Input, Output, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import {
  WorkflowTransition,
  WorkflowTransitionField,
} from '../../models/workflow.model';

@Component({
  selector: 'app-transition-dialog',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './transition-dialog.component.html',
})
export class TransitionDialogComponent {
  @Input() transition!: WorkflowTransition;
  @Input() fields: WorkflowTransitionField[] = [];
  @Output() execute = new EventEmitter<{
    fieldValues: Record<string, string>;
    comment: string;
  }>();
  @Output() cancel = new EventEmitter<void>();

  fieldValues = signal<Record<string, string>>({});
  comment = signal('');

  setFieldValue(name: string, value: string): void {
    const current = this.fieldValues();
    this.fieldValues.set({ ...current, [name]: value });
  }

  onExecute(): void {
    this.execute.emit({
      fieldValues: this.fieldValues(),
      comment: this.comment(),
    });
  }

  onCancel(): void {
    this.cancel.emit();
  }
}
