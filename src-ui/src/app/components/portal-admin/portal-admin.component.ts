import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { PortalService } from '../../services/portal.service';
import { PortalConfig } from '../../models/portal.model';
import { SubnavComponent } from '../subnav/subnav.component';

@Component({
  selector: 'app-portal-admin',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule, SubnavComponent],
  styleUrl: './portal-admin.component.scss',
  template: `
    <div class="dv-screen dv-screen--tight">
      <div class="dv-inner dv-inner--wide">
        <dv-subnav />

        <div class="dv-section pa-section">
          <span class="dv-eyebrow">contributor portals</span>
          <button
            type="button"
            class="dv-btn dv-btn--accent dv-btn--md dv-push"
            (click)="showForm.set(!showForm())"
          >
            {{ showForm() ? 'Cancel' : '+ New portal' }}
          </button>
        </div>

        <!-- Create / edit form -->
        @if (showForm()) {
          <div class="dv-card dv-card--pad pa-form">
            <div class="dv-card__title pa-form__title">
              {{ editingPortal() ? 'Edit portal' : 'New portal' }}
            </div>

            <div class="pa-grid">
              <label class="pa-field">
                <span class="dv-field__label">name</span>
                <input
                  type="text"
                  class="dv-input dv-input--r7"
                  [ngModel]="formName()"
                  (ngModelChange)="formName.set($event)"
                />
              </label>

              <label class="pa-field">
                <span class="dv-field__label">slug</span>
                <input
                  type="text"
                  class="dv-input dv-input--r7 dv-mono"
                  placeholder="auto-generated if blank"
                  [ngModel]="formSlug()"
                  (ngModelChange)="formSlug.set($event)"
                />
              </label>

              <label class="pa-field pa-field--full">
                <span class="dv-field__label">welcome text</span>
                <textarea
                  class="dv-input dv-input--r7"
                  rows="3"
                  [ngModel]="formWelcomeText()"
                  (ngModelChange)="formWelcomeText.set($event)"
                ></textarea>
              </label>

              <label class="pa-field">
                <span class="dv-field__label">brand colour</span>
                <input
                  type="color"
                  class="pa-color"
                  [ngModel]="formPrimaryColor()"
                  (ngModelChange)="formPrimaryColor.set($event)"
                />
              </label>

              <label class="pa-field">
                <span class="dv-field__label">max file size (mb)</span>
                <input
                  type="number"
                  class="dv-input dv-input--r7 dv-mono"
                  [ngModel]="formMaxFileSize()"
                  (ngModelChange)="formMaxFileSize.set($event)"
                />
              </label>

              <label class="pa-field">
                <span class="dv-field__label">default document type id</span>
                <input
                  type="number"
                  class="dv-input dv-input--r7 dv-mono"
                  placeholder="optional"
                  [ngModel]="formDefaultDocType()"
                  (ngModelChange)="formDefaultDocType.set($event)"
                />
              </label>

              <div class="pa-field pa-field--full pa-switches">
                <label class="dv-checkbox-label">
                  <input
                    type="checkbox"
                    class="dv-checkbox"
                    [ngModel]="formRequireEmail()"
                    (ngModelChange)="formRequireEmail.set($event)"
                  />
                  <span>require email</span>
                </label>
                <label class="dv-checkbox-label">
                  <input
                    type="checkbox"
                    class="dv-checkbox"
                    [ngModel]="formRequireName()"
                    (ngModelChange)="formRequireName.set($event)"
                  />
                  <span>require name</span>
                </label>
                <label class="dv-checkbox-label">
                  <input
                    type="checkbox"
                    class="dv-checkbox"
                    [ngModel]="formIsActive()"
                    (ngModelChange)="formIsActive.set($event)"
                  />
                  <span>live</span>
                </label>
              </div>
            </div>

            @if (formError()) {
              <div class="dv-banner dv-banner--error pa-banner" role="alert">{{ formError() }}</div>
            }

            <div class="pa-form__actions">
              <button
                type="button"
                class="dv-btn dv-btn--primary dv-btn--md"
                (click)="savePortal()"
                [disabled]="!formName()"
              >
                {{ editingPortal() ? 'Update' : 'Create' }}
              </button>
              <button type="button" class="dv-btn dv-btn--ghost dv-btn--md" (click)="cancelForm()">
                Cancel
              </button>
            </div>
          </div>
        }

        <!-- Portal cards -->
        @if (loading()) {
          <div class="dv-empty"><span class="dv-spinner"></span> Loading…</div>
        } @else if (portals().length === 0) {
          <div class="dv-empty">No contributor portals configured yet.</div>
        } @else {
          <div class="pa-cards">
            @for (portal of portals(); track portal.id) {
              <div class="dv-card dv-card--pad pa-card">
                <div class="pa-card__head">
                  <span
                    class="pa-swatch"
                    [style.background]="portal.primary_color"
                    aria-hidden="true"
                  ></span>
                  <span class="pa-card__name dv-clip">{{ portal.name }}</span>
                  <span
                    class="dv-meta dv-push"
                    [class.dv-ok]="portal.is_active"
                    [class.dv-faint]="!portal.is_active"
                    >{{ portal.is_active ? '● live' : '○ paused' }}</span
                  >
                </div>

                <a
                  class="pa-card__slug dv-mono"
                  [href]="'/portal/' + portal.slug"
                  target="_blank"
                  rel="noopener"
                  title="Open public portal"
                  >/portal/{{ portal.slug }} ⧉</a
                >

                <div class="pa-card__stats">
                  <span>max {{ portal.max_file_size_mb }} MB</span>
                  <span>{{ portal.require_email ? 'email required' : 'no email required' }}</span>
                  @if (portal.require_name) {
                    <span>name required</span>
                  }
                </div>

                <div class="pa-card__foot">
                  <span class="dv-meta">created {{ portal.created_at | date: 'short' }}</span>
                  <button
                    type="button"
                    class="dv-btn dv-btn--ghost dv-btn--sm dv-push"
                    (click)="editPortal(portal)"
                  >
                    Edit
                  </button>
                  <button
                    type="button"
                    class="dv-btn dv-btn--danger dv-btn--sm"
                    (click)="deletePortal(portal)"
                  >
                    Delete
                  </button>
                </div>
              </div>
            }
          </div>
        }
      </div>
    </div>
  `,
})
export class PortalAdminComponent implements OnInit {
  portals = signal<PortalConfig[]>([]);
  loading = signal(true);
  showForm = signal(false);
  editingPortal = signal<PortalConfig | null>(null);
  formError = signal('');

  formName = signal('');
  formSlug = signal('');
  formWelcomeText = signal('');
  formPrimaryColor = signal('#0d6efd');
  formMaxFileSize = signal(25);
  formDefaultDocType = signal<number | null>(null);
  formRequireEmail = signal(true);
  formRequireName = signal(false);
  formIsActive = signal(true);

  constructor(private portalService: PortalService) {}

  ngOnInit(): void {
    this.loadPortals();
  }

  loadPortals(): void {
    this.loading.set(true);
    this.portalService.getPortals().subscribe({
      next: (resp) => {
        this.portals.set(resp.results);
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
  }

  editPortal(portal: PortalConfig): void {
    this.editingPortal.set(portal);
    this.formName.set(portal.name);
    this.formSlug.set(portal.slug);
    this.formWelcomeText.set(portal.welcome_text);
    this.formPrimaryColor.set(portal.primary_color);
    this.formMaxFileSize.set(portal.max_file_size_mb);
    this.formDefaultDocType.set(portal.default_document_type);
    this.formRequireEmail.set(portal.require_email);
    this.formRequireName.set(portal.require_name);
    this.formIsActive.set(portal.is_active);
    this.showForm.set(true);
    this.formError.set('');
  }

  cancelForm(): void {
    this.showForm.set(false);
    this.editingPortal.set(null);
    this.resetForm();
  }

  private resetForm(): void {
    this.formName.set('');
    this.formSlug.set('');
    this.formWelcomeText.set('');
    this.formPrimaryColor.set('#0d6efd');
    this.formMaxFileSize.set(25);
    this.formDefaultDocType.set(null);
    this.formRequireEmail.set(true);
    this.formRequireName.set(false);
    this.formIsActive.set(true);
    this.formError.set('');
  }

  savePortal(): void {
    this.formError.set('');
    const data: Partial<PortalConfig> = {
      name: this.formName(),
      slug: this.formSlug() || undefined,
      welcome_text: this.formWelcomeText(),
      primary_color: this.formPrimaryColor(),
      max_file_size_mb: this.formMaxFileSize(),
      default_document_type: this.formDefaultDocType(),
      require_email: this.formRequireEmail(),
      require_name: this.formRequireName(),
      is_active: this.formIsActive(),
    };

    const editing = this.editingPortal();
    const obs = editing
      ? this.portalService.updatePortal(editing.id, data)
      : this.portalService.createPortal(data);

    obs.subscribe({
      next: () => {
        this.cancelForm();
        this.loadPortals();
      },
      error: (err) => {
        this.formError.set(
          err.error?.detail || JSON.stringify(err.error) || 'Save failed.',
        );
      },
    });
  }

  deletePortal(portal: PortalConfig): void {
    if (!confirm(`Delete portal "${portal.name}"? This cannot be undone.`)) return;
    this.portalService.deletePortal(portal.id).subscribe({
      next: () => this.loadPortals(),
    });
  }
}
