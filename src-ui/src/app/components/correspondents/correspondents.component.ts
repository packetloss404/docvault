import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { OrganizationService } from '../../services/organization.service';
import { Correspondent } from '../../models/organization.model';

@Component({
  selector: 'app-correspondents',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './correspondents.component.html',
})
export class CorrespondentsComponent implements OnInit {
  correspondents = signal<Correspondent[]>([]);
  editing = signal<Correspondent | null>(null);
  creating = signal(false);

  formName = signal('');
  formMatch = signal('');
  formAlgorithm = signal(0);

  constructor(private orgService: OrganizationService) {}

  ngOnInit(): void {
    this.load();
  }

  load(): void {
    this.orgService.getCorrespondents().subscribe({
      next: (res) => this.correspondents.set(res.results),
    });
  }

  startCreate(): void {
    this.creating.set(true);
    this.editing.set(null);
    this.formName.set('');
    this.formMatch.set('');
    this.formAlgorithm.set(0);
  }

  startEdit(c: Correspondent): void {
    this.editing.set(c);
    this.creating.set(false);
    this.formName.set(c.name);
    this.formMatch.set(c.match);
    this.formAlgorithm.set(c.matching_algorithm);
  }

  cancel(): void {
    this.creating.set(false);
    this.editing.set(null);
  }

  save(): void {
    const data = {
      name: this.formName(),
      match: this.formMatch(),
      matching_algorithm: this.formAlgorithm(),
    };

    if (this.editing()) {
      this.orgService.updateCorrespondent(this.editing()!.id, data).subscribe({
        next: () => { this.cancel(); this.load(); },
      });
    } else {
      this.orgService.createCorrespondent(data).subscribe({
        next: () => { this.cancel(); this.load(); },
      });
    }
  }

  deleteCorrespondent(c: Correspondent): void {
    if (!confirm(`Delete correspondent "${c.name}"?`)) return;
    this.orgService.deleteCorrespondent(c.id).subscribe({
      next: () => this.load(),
    });
  }
}
