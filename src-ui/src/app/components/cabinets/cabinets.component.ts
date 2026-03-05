import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { OrganizationService } from '../../services/organization.service';
import { Cabinet, CabinetTreeNode } from '../../models/organization.model';

@Component({
  selector: 'app-cabinets',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './cabinets.component.html',
})
export class CabinetsComponent implements OnInit {
  cabinets = signal<Cabinet[]>([]);
  tree = signal<CabinetTreeNode[]>([]);
  editing = signal<Cabinet | null>(null);
  creating = signal(false);

  formName = signal('');
  formParent = signal<number | null>(null);

  constructor(private orgService: OrganizationService) {}

  ngOnInit(): void {
    this.load();
  }

  load(): void {
    this.orgService.getCabinets().subscribe({
      next: (res) => this.cabinets.set(res.results),
    });
    this.orgService.getCabinetTree().subscribe({
      next: (tree) => this.tree.set(tree),
    });
  }

  startCreate(): void {
    this.creating.set(true);
    this.editing.set(null);
    this.formName.set('');
    this.formParent.set(null);
  }

  startEdit(c: Cabinet): void {
    this.editing.set(c);
    this.creating.set(false);
    this.formName.set(c.name);
    this.formParent.set(c.parent);
  }

  cancel(): void {
    this.creating.set(false);
    this.editing.set(null);
  }

  save(): void {
    const data = {
      name: this.formName(),
      parent: this.formParent(),
    };

    if (this.editing()) {
      this.orgService.updateCabinet(this.editing()!.id, data).subscribe({
        next: () => { this.cancel(); this.load(); },
      });
    } else {
      this.orgService.createCabinet(data).subscribe({
        next: () => { this.cancel(); this.load(); },
      });
    }
  }

  deleteCabinet(c: Cabinet): void {
    if (!confirm(`Delete cabinet "${c.name}"?`)) return;
    this.orgService.deleteCabinet(c.id).subscribe({
      next: () => this.load(),
    });
  }
}
