import { Component, OnInit, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { OrganizationService } from '../../services/organization.service';
import { Correspondent } from '../../models/organization.model';
import { SubnavComponent } from '../subnav/subnav.component';

@Component({
  selector: 'app-correspondents',
  standalone: true,
  imports: [FormsModule, SubnavComponent],
  templateUrl: './correspondents.component.html',
  styleUrl: './correspondents.component.scss',
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

  /** Up to two initials for the row avatar ("Acme Utilities" -> "AU"). */
  initials(name: string): string {
    const parts = (name || '').trim().split(/\s+/).filter((p) => p.length > 0);
    if (parts.length === 0) return '??';
    if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
    return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
  }

  deleteCorrespondent(c: Correspondent): void {
    if (!confirm(`Delete correspondent "${c.name}"?`)) return;
    this.orgService.deleteCorrespondent(c.id).subscribe({
      next: () => this.load(),
    });
  }
}
