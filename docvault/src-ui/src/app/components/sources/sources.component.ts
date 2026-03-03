import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { SourceService } from '../../services/source.service';
import { Source, MailAccount } from '../../models/source.model';

@Component({
  selector: 'app-sources',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  templateUrl: './sources.component.html',
})
export class SourcesComponent implements OnInit {
  sources = signal<Source[]>([]);
  mailAccounts = signal<MailAccount[]>([]);
  activeTab = signal<'sources' | 'mail'>('sources');

  // Source form
  showSourceForm = signal(false);
  editingSource = signal<Source | null>(null);
  sourceForm = signal<Partial<Source>>({
    label: '',
    source_type: 'watch_folder',
    enabled: true,
  });

  // Mail account form
  showMailForm = signal(false);
  editingMailAccount = signal<MailAccount | null>(null);
  mailForm = signal<Partial<MailAccount>>({
    name: '',
    imap_server: '',
    port: 993,
    security: 'ssl',
    account_type: 'imap',
    username: '',
    password: '',
    enabled: true,
  });

  testResult = signal<{ success: boolean; message: string } | null>(null);

  constructor(private sourceService: SourceService) {}

  ngOnInit(): void {
    this.loadSources();
    this.loadMailAccounts();
  }

  loadSources(): void {
    this.sourceService.getSources().subscribe({
      next: (resp) => this.sources.set(resp.results),
    });
  }

  loadMailAccounts(): void {
    this.sourceService.getMailAccounts().subscribe({
      next: (resp) => this.mailAccounts.set(resp.results),
    });
  }

  openSourceForm(source?: Source): void {
    if (source) {
      this.editingSource.set(source);
      this.sourceForm.set({
        label: source.label,
        source_type: source.source_type,
        enabled: source.enabled,
      });
    } else {
      this.editingSource.set(null);
      this.sourceForm.set({ label: '', source_type: 'watch_folder', enabled: true });
    }
    this.showSourceForm.set(true);
  }

  saveSource(): void {
    const data = this.sourceForm();
    const existing = this.editingSource();
    if (existing) {
      this.sourceService.updateSource(existing.id, data).subscribe({
        next: () => { this.showSourceForm.set(false); this.loadSources(); },
      });
    } else {
      this.sourceService.createSource(data).subscribe({
        next: () => { this.showSourceForm.set(false); this.loadSources(); },
      });
    }
  }

  deleteSource(id: number): void {
    if (confirm('Delete this source?')) {
      this.sourceService.deleteSource(id).subscribe({
        next: () => this.loadSources(),
      });
    }
  }

  openMailForm(account?: MailAccount): void {
    if (account) {
      this.editingMailAccount.set(account);
      this.mailForm.set({
        name: account.name,
        imap_server: account.imap_server,
        port: account.port,
        security: account.security,
        account_type: account.account_type,
        username: account.username,
        password: '',
        enabled: account.enabled,
      });
    } else {
      this.editingMailAccount.set(null);
      this.mailForm.set({
        name: '', imap_server: '', port: 993, security: 'ssl',
        account_type: 'imap', username: '', password: '', enabled: true,
      });
    }
    this.showMailForm.set(true);
  }

  saveMailAccount(): void {
    const data = this.mailForm();
    const existing = this.editingMailAccount();
    if (existing) {
      this.sourceService.updateMailAccount(existing.id, data).subscribe({
        next: () => { this.showMailForm.set(false); this.loadMailAccounts(); },
      });
    } else {
      this.sourceService.createMailAccount(data).subscribe({
        next: () => { this.showMailForm.set(false); this.loadMailAccounts(); },
      });
    }
  }

  deleteMailAccount(id: number): void {
    if (confirm('Delete this mail account?')) {
      this.sourceService.deleteMailAccount(id).subscribe({
        next: () => this.loadMailAccounts(),
      });
    }
  }

  testConnection(accountId: number): void {
    this.testResult.set(null);
    this.sourceService.testMailConnection(accountId).subscribe({
      next: (result) => this.testResult.set(result),
    });
  }
}
