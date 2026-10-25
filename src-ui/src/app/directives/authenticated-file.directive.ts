import {
  Directive,
  ElementRef,
  HostListener,
  Input,
  OnDestroy,
  Renderer2,
  inject,
} from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Subscription } from 'rxjs';

@Directive({ selector: 'img[authenticatedSrc], iframe[authenticatedSrc]', standalone: true })
export class AuthenticatedSrcDirective implements OnDestroy {
  private readonly http = inject(HttpClient);
  private readonly element = inject(ElementRef<HTMLImageElement | HTMLIFrameElement>);
  private readonly renderer = inject(Renderer2);
  private request?: Subscription;
  private source = '';
  private fragment = '';
  private objectUrl = '';

  @Input() set authenticatedSrc(value: string) {
    const hash = value.indexOf('#');
    const source = hash < 0 ? value : value.slice(0, hash);
    this.fragment = hash < 0 ? '' : value.slice(hash);
    if (source === this.source) {
      this.render();
      return;
    }
    this.source = source;
    this.request?.unsubscribe();
    this.release();
    if (!source) return;
    this.request = this.http.get(source, { responseType: 'blob' }).subscribe({
      next: (blob) => {
        if (this.element.nativeElement.tagName === 'IFRAME' && blob.type !== 'application/pdf') {
          this.element.nativeElement.dispatchEvent(new Event('error'));
          return;
        }
        this.objectUrl = URL.createObjectURL(blob);
        this.render();
      },
      error: () => this.element.nativeElement.dispatchEvent(new Event('error')),
    });
  }

  ngOnDestroy(): void {
    this.request?.unsubscribe();
    this.release();
  }

  private render(): void {
    if (this.objectUrl) {
      this.renderer.setAttribute(this.element.nativeElement, 'src', this.objectUrl + this.fragment);
    }
  }

  private release(): void {
    this.renderer.removeAttribute(this.element.nativeElement, 'src');
    if (this.objectUrl) URL.revokeObjectURL(this.objectUrl);
    this.objectUrl = '';
  }
}

@Directive({ selector: 'a[authenticatedDownload]', standalone: true })
export class AuthenticatedDownloadDirective implements OnDestroy {
  @Input() authenticatedDownload = '';
  @Input() downloadFilename = 'document';
  private readonly http = inject(HttpClient);
  private readonly element = inject(ElementRef<HTMLAnchorElement>);
  private request?: Subscription;
  private readonly downloads = new Map<string, ReturnType<typeof setTimeout>>();
  private loading = false;

  @HostListener('click', ['$event'])
  download(event: MouseEvent): void {
    event.preventDefault();
    if (this.loading || !this.authenticatedDownload) return;
    this.loading = true;
    this.request = this.http
      .get(this.authenticatedDownload, {
        responseType: 'blob',
        observe: 'response',
      })
      .subscribe({
        next: (response) => {
          this.loading = false;
          if (!response.body) return;
          const url = URL.createObjectURL(response.body);
          const link = document.createElement('a');
          link.href = url;
          link.download = this.filename(response.headers.get('Content-Disposition'));
          document.body.appendChild(link);
          link.click();
          link.remove();
          // Allow the browser to begin reading the blob before releasing it.
          this.downloads.set(
            url,
            setTimeout(() => {
              URL.revokeObjectURL(url);
              this.downloads.delete(url);
            }, 1000),
          );
        },
        error: () => {
          this.loading = false;
          this.element.nativeElement.dispatchEvent(new Event('error'));
        },
      });
  }

  ngOnDestroy(): void {
    this.request?.unsubscribe();
    for (const [url, timer] of this.downloads) {
      clearTimeout(timer);
      URL.revokeObjectURL(url);
    }
  }

  private filename(disposition: string | null): string {
    const encoded = disposition?.match(/filename\*=UTF-8''([^;]+)/i)?.[1];
    if (encoded) {
      try {
        return decodeURIComponent(encoded);
      } catch {
        /* Use the plain filename instead. */
      }
    }
    return disposition?.match(/filename="([^"]+)"/i)?.[1] ?? this.downloadFilename;
  }
}
