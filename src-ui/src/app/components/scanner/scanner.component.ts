import { Component, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { SecurityService } from '../../services/security.service';
import { ScannerDevice } from '../../models/security.model';
import { SubnavComponent } from '../subnav/subnav.component';

@Component({
  selector: 'app-scanner',
  standalone: true,
  imports: [FormsModule, SubnavComponent],
  styleUrl: './scanner.component.scss',
  template: `
    <div class="dv-screen dv-screen--tight">
      <div class="dv-inner dv-inner--wide">
        <dv-subnav />

        <div class="dv-pagehead pagehead">
          <h1 class="dv-h1 dv-h1--sm">Scanners</h1>
          <button
            type="button"
            class="dv-btn dv-btn--secondary dv-btn--sm dv-push"
            (click)="discoverScanners()"
            [disabled]="discovering()"
          >
            @if (discovering()) {
              <span class="dv-spinner"></span>
              Discovering…
            } @else {
              Discover scanners
            }
          </button>
        </div>

        @if (errorMessage()) {
          <div class="notice notice--bad" role="alert">
            <span>{{ errorMessage() }}</span>
            <button type="button" class="notice__close" (click)="errorMessage.set('')">✕</button>
          </div>
        }

        @if (successMessage()) {
          <div class="notice notice--ok" role="status">
            <span>{{ successMessage() }}</span>
            <button type="button" class="notice__close" (click)="successMessage.set('')">✕</button>
          </div>
        }

        <div class="dv-section">
          <span class="dv-eyebrow">available scanners</span>
        </div>

        @if (scanners().length === 0) {
          <div class="dv-dropzone">
            No scanners found yet — run “Discover scanners” to search for connected devices.
          </div>
        } @else {
          <div class="scanner-grid">
            @for (scanner of scanners(); track scanner.id) {
              <div
                class="dv-card dv-card--pad dv-card--hover"
                [class.dv-card--accent]="selectedScanner()?.id === scanner.id"
              >
                <div class="scanner-head">
                  <span class="scanner-name">{{ scanner.label || scanner.model }}</span>
                  <span
                    class="scanner-state dv-push"
                    [class.scanner-state--on]="selectedScanner()?.id === scanner.id"
                  >
                    {{ selectedScanner()?.id === scanner.id ? '● selected' : '○ idle' }}
                  </span>
                </div>
                <div class="scanner-meta">{{ scanner.vendor }} · {{ scanner.type }}</div>
                <div class="scanner-id dv-meta">{{ scanner.id }}</div>
                <div class="scanner-actions">
                  <button
                    type="button"
                    class="dv-btn dv-btn--primary dv-btn--md"
                    (click)="scanNow(scanner)"
                    [disabled]="scanning()"
                  >
                    @if (scanning() && selectedScanner()?.id === scanner.id) {
                      <span class="dv-spinner"></span>
                      Scanning…
                    } @else {
                      Scan now
                    }
                  </button>
                  <button
                    type="button"
                    class="dv-btn dv-btn--ghost dv-btn--md"
                    (click)="selectScanner(scanner)"
                  >
                    Settings
                  </button>
                </div>
              </div>
            }
          </div>
        }

        @if (selectedScanner()) {
          <div class="dv-section">
            <span class="dv-eyebrow">scan settings</span>
          </div>

          <div class="dv-card dv-card--pad form-card">
            <div class="form-grid">
              <div>
                <label class="dv-field__label" for="scan-dpi">dpi</label>
                <select id="scan-dpi" class="dv-select" [(ngModel)]="scanDpi">
                  <option [ngValue]="150">150 · draft</option>
                  <option [ngValue]="200">200</option>
                  <option [ngValue]="300">300 · standard</option>
                  <option [ngValue]="600">600 · high quality</option>
                </select>
              </div>

              <div>
                <label class="dv-field__label" for="scan-color">colour mode</label>
                <select id="scan-color" class="dv-select" [(ngModel)]="scanColorMode">
                  <option value="color">Colour</option>
                  <option value="grayscale">Greyscale</option>
                  <option value="lineart">Black &amp; white</option>
                </select>
              </div>

              <div>
                <label class="dv-field__label" for="scan-paper">paper size</label>
                <select id="scan-paper" class="dv-select" [(ngModel)]="scanPaperSize">
                  <option value="a4">A4</option>
                  <option value="letter">Letter</option>
                  <option value="legal">Legal</option>
                  <option value="auto">Auto detect</option>
                </select>
              </div>
            </div>

            <div class="form-actions">
              <button
                type="button"
                class="dv-btn dv-btn--primary dv-btn--sm"
                (click)="startScan()"
                [disabled]="scanning()"
              >
                @if (scanning()) {
                  <span class="dv-spinner"></span>
                  Scanning…
                } @else {
                  Scan document
                }
              </button>
            </div>
          </div>
        }

        @if (scanTaskId()) {
          <div class="dv-callout callout">
            <div class="dv-callout__label">scan queued</div>
            <div class="callout__body">
              Task <span class="dv-mono">{{ scanTaskId() }}</span> submitted. The document appears
              in your inbox once processing completes.
            </div>
          </div>
        }
      </div>
    </div>
  `,
})
export class ScannerComponent {
  scanners = signal<ScannerDevice[]>([]);
  selectedScanner = signal<ScannerDevice | null>(null);
  discovering = signal(false);
  scanning = signal(false);
  scanTaskId = signal('');
  errorMessage = signal('');
  successMessage = signal('');

  scanDpi = 300;
  scanColorMode = 'color';
  scanPaperSize = 'a4';

  constructor(private securityService: SecurityService) {}

  discoverScanners(): void {
    this.discovering.set(true);
    this.errorMessage.set('');
    this.securityService.listScanners().subscribe({
      next: (devices) => {
        this.scanners.set(devices);
        this.discovering.set(false);
        if (devices.length === 0) {
          this.errorMessage.set('No scanners were detected. Ensure your scanner is connected and powered on.');
        }
      },
      error: () => {
        this.errorMessage.set('Failed to discover scanners. Check server configuration.');
        this.discovering.set(false);
      },
    });
  }

  selectScanner(scanner: ScannerDevice): void {
    this.selectedScanner.set(scanner);
  }

  /** Card-level "Scan now": select the device, then scan with current settings. */
  scanNow(scanner: ScannerDevice): void {
    this.selectScanner(scanner);
    this.startScan();
  }

  startScan(): void {
    const device = this.selectedScanner();
    if (!device) return;

    this.scanning.set(true);
    this.errorMessage.set('');
    this.successMessage.set('');
    this.scanTaskId.set('');

    this.securityService.scan(device.id, {
      dpi: this.scanDpi,
      color_mode: this.scanColorMode,
      paper_size: this.scanPaperSize,
    }).subscribe({
      next: (result) => {
        this.scanTaskId.set(result.task_id);
        this.successMessage.set(result.message || 'Scan initiated successfully.');
        this.scanning.set(false);
      },
      error: () => {
        this.errorMessage.set('Scan failed. Please check the scanner and try again.');
        this.scanning.set(false);
      },
    });
  }
}
