import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { OrganizationService } from '../../services/organization.service';
import { Tag } from '../../models/organization.model';

@Component({
  selector: 'app-tags',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './tags.component.html',
})
export class TagsComponent implements OnInit {
  tags = signal<Tag[]>([]);
  editing = signal<Tag | null>(null);
  creating = signal(false);

  formName = signal('');
  formColor = signal('#3b82f6');
  formParent = signal<number | null>(null);
  formIsInbox = signal(false);
  formMatch = signal('');
  formAlgorithm = signal(0);

  constructor(private orgService: OrganizationService) {}

  ngOnInit(): void {
    this.loadTags();
  }

  loadTags(): void {
    this.orgService.getTags().subscribe({
      next: (res) => this.tags.set(res.results),
    });
  }

  startCreate(): void {
    this.creating.set(true);
    this.editing.set(null);
    this.resetForm();
  }

  startEdit(tag: Tag): void {
    this.editing.set(tag);
    this.creating.set(false);
    this.formName.set(tag.name);
    this.formColor.set(tag.color);
    this.formParent.set(tag.parent);
    this.formIsInbox.set(tag.is_inbox_tag);
    this.formMatch.set(tag.match);
    this.formAlgorithm.set(tag.matching_algorithm);
  }

  cancel(): void {
    this.creating.set(false);
    this.editing.set(null);
    this.resetForm();
  }

  save(): void {
    const data = {
      name: this.formName(),
      color: this.formColor(),
      parent: this.formParent(),
      is_inbox_tag: this.formIsInbox(),
      match: this.formMatch(),
      matching_algorithm: this.formAlgorithm(),
    };

    if (this.editing()) {
      this.orgService.updateTag(this.editing()!.id, data).subscribe({
        next: () => { this.cancel(); this.loadTags(); },
      });
    } else {
      this.orgService.createTag(data).subscribe({
        next: () => { this.cancel(); this.loadTags(); },
      });
    }
  }

  deleteTag(tag: Tag): void {
    if (!confirm(`Delete tag "${tag.name}"?`)) return;
    this.orgService.deleteTag(tag.id).subscribe({
      next: () => this.loadTags(),
    });
  }

  private resetForm(): void {
    this.formName.set('');
    this.formColor.set('#3b82f6');
    this.formParent.set(null);
    this.formIsInbox.set(false);
    this.formMatch.set('');
    this.formAlgorithm.set(0);
  }
}
