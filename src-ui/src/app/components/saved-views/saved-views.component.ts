import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { SearchService } from '../../services/search.service';
import {
  SavedView,
  SavedViewListItem,
  FilterRule,
  FilterGroup,
  Filter,
  FILTER_RULE_TYPES,
} from '../../models/search.model';

@Component({
  selector: 'app-saved-views',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  templateUrl: './saved-views.component.html',
})
export class SavedViewsComponent implements OnInit {
  views = signal<SavedViewListItem[]>([]);
  creating = signal(false);
  editing = signal<SavedView | null>(null);

  editName = signal('');
  editDisplayMode = signal<'table' | 'small_cards' | 'large_cards'>('table');
  editSortField = signal('created');
  editSortReverse = signal(true);
  editPageSize = signal(25);
  editShowDashboard = signal(false);
  editShowSidebar = signal(false);
  editRules = signal<FilterRule[]>([]);

  newRuleType = signal('title_contains');
  newRuleValue = signal('');

  ruleTypes = FILTER_RULE_TYPES;

  // --- Filter Groups (B2.4) ---
  editFilterGroups = signal<FilterGroup[]>([]);
  newGroupRuleType = signal<Record<number, string>>({});
  newGroupRuleValue = signal<Record<number, string>>({});

  constructor(private searchService: SearchService) {}

  ngOnInit(): void {
    this.loadViews();
  }

  loadViews(): void {
    this.searchService.getSavedViews().subscribe({
      next: (res) => this.views.set(res.results),
    });
  }

  startCreate(): void {
    this.creating.set(true);
    this.editing.set(null);
    this.editName.set('');
    this.editDisplayMode.set('table');
    this.editSortField.set('created');
    this.editSortReverse.set(true);
    this.editPageSize.set(25);
    this.editShowDashboard.set(false);
    this.editShowSidebar.set(false);
    this.editRules.set([]);
    this.editFilterGroups.set([]);
    this.newGroupRuleType.set({});
    this.newGroupRuleValue.set({});
  }

  startEdit(viewItem: SavedViewListItem): void {
    this.searchService.getSavedView(viewItem.id).subscribe({
      next: (view) => {
        this.editing.set(view);
        this.creating.set(false);
        this.editName.set(view.name);
        this.editDisplayMode.set(view.display_mode);
        this.editSortField.set(view.sort_field);
        this.editSortReverse.set(view.sort_reverse);
        this.editPageSize.set(view.page_size);
        this.editShowDashboard.set(view.show_on_dashboard);
        this.editShowSidebar.set(view.show_in_sidebar);
        this.editRules.set([...view.filter_rules]);
        this.editFilterGroups.set([]);
        this.newGroupRuleType.set({});
        this.newGroupRuleValue.set({});
      },
    });
  }

  cancelEdit(): void {
    this.creating.set(false);
    this.editing.set(null);
  }

  addRule(): void {
    this.editRules.update((rules) => [
      ...rules,
      { rule_type: this.newRuleType(), value: this.newRuleValue() },
    ]);
    this.newRuleValue.set('');
  }

  removeRule(index: number): void {
    this.editRules.update((rules) => rules.filter((_, i) => i !== index));
  }

  // --- Filter Group methods (B2.4) ---

  addFilterGroup(): void {
    this.editFilterGroups.update((groups) => [...groups, { filters: [], operator: 'AND' }]);
  }

  removeFilterGroup(groupIndex: number): void {
    this.editFilterGroups.update((groups) => groups.filter((_, i) => i !== groupIndex));
  }

  toggleGroupOperator(groupIndex: number): void {
    this.editFilterGroups.update((groups) =>
      groups.map((g, i) =>
        i === groupIndex ? { ...g, operator: g.operator === 'AND' ? 'OR' : 'AND' } : g,
      ),
    );
  }

  addFilterToGroup(groupIndex: number): void {
    const ruleType = this.newGroupRuleType()[groupIndex] ?? 'title_contains';
    const value = this.newGroupRuleValue()[groupIndex] ?? '';
    if (!value.trim()) return;

    this.editFilterGroups.update((groups) =>
      groups.map((g, i) =>
        i === groupIndex ? { ...g, filters: [...g.filters, { rule_type: ruleType, value }] } : g,
      ),
    );

    // reset inputs for this group
    this.newGroupRuleValue.update((v) => ({ ...v, [groupIndex]: '' }));
  }

  removeFilterFromGroup(groupIndex: number, filterIndex: number): void {
    this.editFilterGroups.update((groups) =>
      groups.map((g, i) =>
        i === groupIndex
          ? { ...g, filters: g.filters.filter((_, fi) => fi !== filterIndex) }
          : g,
      ),
    );
  }

  getGroupRuleType(groupIndex: number): string {
    return this.newGroupRuleType()[groupIndex] ?? 'title_contains';
  }

  setGroupRuleType(groupIndex: number, value: string): void {
    this.newGroupRuleType.update((v) => ({ ...v, [groupIndex]: value }));
  }

  getGroupRuleValue(groupIndex: number): string {
    return this.newGroupRuleValue()[groupIndex] ?? '';
  }

  setGroupRuleValue(groupIndex: number, value: string): void {
    this.newGroupRuleValue.update((v) => ({ ...v, [groupIndex]: value }));
  }

  save(): void {
    const data: Partial<SavedView> = {
      name: this.editName(),
      display_mode: this.editDisplayMode(),
      sort_field: this.editSortField(),
      sort_reverse: this.editSortReverse(),
      page_size: this.editPageSize(),
      show_on_dashboard: this.editShowDashboard(),
      show_in_sidebar: this.editShowSidebar(),
      filter_rules: this.editRules().map((r) => ({
        rule_type: r.rule_type,
        value: r.value,
      })),
    };

    if (this.creating()) {
      this.searchService.createSavedView(data).subscribe({
        next: () => {
          this.cancelEdit();
          this.loadViews();
        },
      });
    } else if (this.editing()) {
      this.searchService.updateSavedView(this.editing()!.id, data).subscribe({
        next: () => {
          this.cancelEdit();
          this.loadViews();
        },
      });
    }
  }

  deleteView(view: SavedViewListItem): void {
    if (!confirm(`Delete saved view "${view.name}"?`)) return;
    this.searchService.deleteSavedView(view.id).subscribe({
      next: () => this.loadViews(),
    });
  }

  getRuleTypeLabel(ruleType: string): string {
    return this.ruleTypes.find((t) => t.value === ruleType)?.label || ruleType;
  }
}
