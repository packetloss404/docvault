import { Injectable, OnDestroy, signal } from '@angular/core';
import { environment } from '../../environments/environment';
import { TaskProgress } from '../models/websocket.model';

@Injectable({ providedIn: 'root' })
export class WebSocketService implements OnDestroy {
  private socket: WebSocket | null = null;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private reconnectDelay = 1000;
  private readonly maxReconnectDelay = 30000;
  private destroyed = false;

  readonly taskProgress = signal<TaskProgress | null>(null);
  readonly connected = signal(false);

  private get wsUrl(): string {
    // Derive WebSocket base URL from the HTTP API URL.
    // e.g. http://localhost:5000/api/v1 → ws://localhost:5000
    const base = environment.apiUrl
      .replace(/\/api\/v1\/?$/, '')
      .replace(/^http/, 'ws');
    return `${base}/ws/status/`;
  }

  connect(): void {
    if (this.destroyed || this.socket?.readyState === WebSocket.OPEN) {
      return;
    }

    this.cancelReconnect();

    const socket = new WebSocket(this.wsUrl);
    this.socket = socket;

    socket.onopen = () => {
      this.reconnectDelay = 1000;
      this.connected.set(true);
    };

    socket.onmessage = (event: MessageEvent) => {
      try {
        const data = JSON.parse(event.data as string) as TaskProgress;
        this.taskProgress.set(data);
      } catch {
        // Ignore unparseable frames.
      }
    };

    socket.onclose = () => {
      this.connected.set(false);
      if (!this.destroyed) {
        this.scheduleReconnect();
      }
    };

    socket.onerror = () => {
      // onclose fires immediately after onerror, which handles reconnection.
    };
  }

  disconnect(): void {
    this.destroyed = true;
    this.cancelReconnect();
    if (this.socket) {
      this.socket.onclose = null;
      this.socket.close();
      this.socket = null;
    }
    this.connected.set(false);
  }

  ngOnDestroy(): void {
    this.disconnect();
  }

  private scheduleReconnect(): void {
    this.reconnectTimer = setTimeout(() => {
      if (!this.destroyed) {
        this.connect();
      }
    }, this.reconnectDelay);

    // Exponential backoff capped at maxReconnectDelay.
    this.reconnectDelay = Math.min(
      this.reconnectDelay * 2,
      this.maxReconnectDelay,
    );
  }

  private cancelReconnect(): void {
    if (this.reconnectTimer !== null) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
  }
}
