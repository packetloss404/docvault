import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { OrganizationService } from '../../services/organization.service';
import { Tag } from '../../models/organization.model';

const MAX_TAG_DEPTH = 5;

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

  depthError = signal<string | null>(null);

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
    this.depthError.set(null);
    this.resetForm();
  }

  startEdit(tag: Tag): void {
    this.editing.set(tag);
    this.creating.set(false);
    this.depthError.set(null);
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
    this.depthError.set(null);
    this.resetForm();
  }

  /**
   * Compute the depth of a tag by walking up its parent chain.
   * A root tag (no parent) has depth 1.
   */
  getDepth(tag: Pick<Tag, 'id' | 'parent'>): number {
    let depth = 1;
    let current: Pick<Tag, 'id' | 'parent'> | undefined = tag;
    const allTags = this.tags();
    const visited = new Set<number>();

    while (current?.parent != null) {
      if (visited.has(current.id)) break; // guard against cycles
      visited.add(current.id);
      current = allTags.find((t) => t.id === current!.parent);
      depth++;
    }
    return depth;
  }

  save(): void {
    const parentId = this.formParent();

    if (parentId != null) {
      const parentTag = this.tags().find((t) => t.id === parentId);
      if (parentTag) {
        const newDepth = this.getDepth(parentTag) + 1;
        if (newDepth > MAX_TAG_DEPTH) {
          this.depthError.set(
            `Cannot place tag here: maximum nesting depth of ${MAX_TAG_DEPTH} levels would be exceeded.`,
          );
          return;
        }
      }
    }

    this.depthError.set(null);

    const data = {
      name: this.formName(),
      color: this.formColor(),
      parent: parentId,
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
