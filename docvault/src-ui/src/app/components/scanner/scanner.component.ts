import { Component, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { SecurityService } from '../../services/security.service';
import { ScannerDevice } from '../../models/security.model';

@Component({
  selector: 'app-scanner',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="container-fluid py-4">
      <h4>Scanners</h4>

      @if (errorMessage()) {
        <div class="alert alert-danger alert-dismissible">
          {{ errorMessage() }}
          <button type="button" class="btn-close" (click)="errorMessage.set('')"></button>
        </div>
      }

      @if (successMessage()) {
        <div class="alert alert-success alert-dismissible">
          {{ successMessage() }}
          <button type="button" class="btn-close" (click)="successMessage.set('')"></button>
        </div>
      }

      <!-- Discover -->
      <div class="card mb-3">
        <div class="card-header d-flex justify-content-between align-items-center">
          <span>Available Scanners</span>
          <button class="btn btn-primary btn-sm" (click)="discoverScanners()" [disabled]="discovering()">
            @if (discovering()) {
              <span class="spinner-border spinner-border-sm me-1"></span>
            }
            <i class="bi bi-arrow-clockwise me-1"></i> Discover Scanners
          </button>
        </div>
        <div class="card-body">
          @if (scanners().length === 0) {
            <p class="text-muted mb-0">
              No scanners found. Click "Discover Scanners" to search for connected devices.
            </p>
          } @else {
            <div class="list-group">
              @for (scanner of scanners(); track scanner.id) {
                <button class="list-group-item list-group-item-action d-flex justify-content-between align-items-center"
                        [class.active]="selectedScanner()?.id === scanner.id"
                        (click)="selectScanner(scanner)">
                  <div>
                    <strong>{{ scanner.label || scanner.model }}</strong>
                    <br />
                    <small class="text-body-secondary">{{ scanner.vendor }} - {{ scanner.type }}</small>
                  </div>
                  @if (selectedScanner()?.id === scanner.id) {
                    <i class="bi bi-check-circle-fill"></i>
                  }
                </button>
              }
            </div>
          }
        </div>
      </div>

      <!-- Scan Settings -->
      @if (selectedScanner()) {
        <div class="card mb-3">
          <div class="card-header">Scan Settings</div>
          <div class="card-body">
            <div class="row g-3">
              <div class="col-md-4">
                <label class="form-label">DPI (Resolution)</label>
                <select class="form-select" [(ngModel)]="scanDpi">
                  <option [ngValue]="150">150 DPI (Draft)</option>
                  <option [ngValue]="200">200 DPI</option>
                  <option [ngValue]="300">300 DPI (Standard)</option>
                  <option [ngValue]="600">600 DPI (High Quality)</option>
                </select>
              </div>
              <div class="col-md-4">
                <label class="form-label">Color Mode</label>
                <select class="form-select" [(ngModel)]="scanColorMode">
                  <option value="color">Color</option>
                  <option value="grayscale">Grayscale</option>
                  <option value="lineart">Black &amp; White</option>
                </select>
              </div>
              <div class="col-md-4">
                <label class="form-label">Paper Size</label>
                <select class="form-select" [(ngModel)]="scanPaperSize">
                  <option value="a4">A4</option>
                  <option value="letter">Letter</option>
                  <option value="legal">Legal</option>
                  <option value="auto">Auto Detect</option>
                </select>
              </div>
            </div>
            <div class="mt-3">
              <button class="btn btn-success" (click)="startScan()" [disabled]="scanning()">
                @if (scanning()) {
                  <span class="spinner-border spinner-border-sm me-1"></span>
                }
                <i class="bi bi-printer me-1"></i> Scan Document
              </button>
            </div>
          </div>
        </div>
      }

      <!-- Scan Result -->
      @if (scanTaskId()) {
        <div class="card">
          <div class="card-header">Scan Result</div>
          <div class="card-body text-center">
            <div class="alert alert-info">
              <i class="bi bi-info-circle me-1"></i>
              Scan task submitted successfully (Task ID: {{ scanTaskId() }}).
              The document will appear in your inbox once processing is complete.
            </div>
          </div>
        </div>
      }
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
