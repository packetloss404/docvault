import { Injectable, OnDestroy, signal } from '@angular/core';
import { environment } from '../../environments/environment';
import { Notification } from '../models/notification.model';
import { TaskProgress } from '../models/websocket.model';
import { AuthService } from './auth.service';

function socketUrl(path: string, token: string | null): string {
  const base = environment.apiUrl.replace(/\/api\/v1\/?$/, '');
  const url = new URL(`${base}/ws/${path}/`, window.location.origin);
  url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
  if (token) url.searchParams.set('token', token);
  return url.toString();
}

class SocketConnection<T> {
  private socket: WebSocket | null = null;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private delay = 1000;
  private active = false;
  private destroyed = false;

  constructor(
    private readonly url: () => string,
    private readonly receive: (message: T) => void,
    private readonly status: (connected: boolean) => void,
  ) {}

  connect(): void {
    if (this.destroyed || this.socket?.readyState === WebSocket.OPEN || this.socket?.readyState === WebSocket.CONNECTING) return;
    this.active = true;
    this.cancelReconnect();
    const socket = new WebSocket(this.url());
    this.socket = socket;
    socket.onopen = () => { this.delay = 1000; this.status(true); };
    socket.onmessage = (event: MessageEvent) => {
      try { this.receive(JSON.parse(event.data as string) as T); } catch { /* Ignore malformed frames. */ }
    };
    socket.onclose = () => {
      this.socket = null;
      this.status(false);
      if (this.active) {
        this.reconnectTimer = setTimeout(() => this.connect(), this.delay);
        this.delay = Math.min(this.delay * 2, 30_000);
      }
    };
    socket.onerror = () => {};
  }

  disconnect(): void {
    this.active = false;
    this.cancelReconnect();
    if (this.socket) {
      this.socket.onopen = this.socket.onmessage = this.socket.onclose = this.socket.onerror = null;
      this.socket.close();
      this.socket = null;
    }
    this.status(false);
  }

  destroy(): void { this.destroyed = true; this.disconnect(); }

  private cancelReconnect(): void {
    if (this.reconnectTimer !== null) clearTimeout(this.reconnectTimer);
    this.reconnectTimer = null;
  }
}

@Injectable({ providedIn: 'root' })
export class WebSocketService implements OnDestroy {
  readonly taskProgress = signal<TaskProgress | null>(null);
  readonly connected = signal(false);
  private readonly connection: SocketConnection<TaskProgress>;

  constructor(auth: AuthService) {
    this.connection = new SocketConnection(
      () => socketUrl('status', auth.token()),
      (message) => this.taskProgress.set(message),
      (connected) => this.connected.set(connected),
    );
  }

  connect(): void { this.connection.connect(); }
  disconnect(): void { this.connection.disconnect(); this.taskProgress.set(null); }
  ngOnDestroy(): void { this.connection.destroy(); }
}

@Injectable({ providedIn: 'root' })
export class NotificationWebSocketService implements OnDestroy {
  readonly notification = signal<Notification | null>(null);
  readonly connected = signal(false);
  private readonly connection: SocketConnection<Notification>;

  constructor(auth: AuthService) {
    this.connection = new SocketConnection(
      () => socketUrl('notifications', auth.token()),
      (message) => this.notification.set(message),
      (connected) => this.connected.set(connected),
    );
  }

  connect(): void { this.connection.connect(); }
  disconnect(): void { this.connection.disconnect(); this.notification.set(null); }
  ngOnDestroy(): void { this.connection.destroy(); }
}
