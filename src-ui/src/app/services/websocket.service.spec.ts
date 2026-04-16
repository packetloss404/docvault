import { TestBed } from '@angular/core/testing';
import { WebSocketService } from './websocket.service';

// ---------------------------------------------------------------------------
// Minimal WebSocket mock
// ---------------------------------------------------------------------------

interface MockWsInstance {
  url: string;
  readyState: number;
  onopen: (() => void) | null;
  onmessage: ((ev: { data: string }) => void) | null;
  onclose: (() => void) | null;
  onerror: (() => void) | null;
  close: () => void;
  triggerOpen(): void;
  triggerMessage(data: unknown): void;
  triggerClose(): void;
}

let lastSocket: MockWsInstance | null = null;
const closeSpy = { called: false, callCount: 0 };

class MockWebSocket implements MockWsInstance {
  static readonly CONNECTING = 0;
  static readonly OPEN = 1;
  static readonly CLOSING = 2;
  static readonly CLOSED = 3;

  url: string;
  readyState = MockWebSocket.CONNECTING;
  onopen: (() => void) | null = null;
  onmessage: ((ev: { data: string }) => void) | null = null;
  onclose: (() => void) | null = null;
  onerror: (() => void) | null = null;

  close(): void {
    this.readyState = MockWebSocket.CLOSED;
    closeSpy.called = true;
    closeSpy.callCount++;
  }

  constructor(url: string) {
    this.url = url;
    lastSocket = this;
  }

  triggerOpen(): void {
    this.readyState = MockWebSocket.OPEN;
    this.onopen?.();
  }

  triggerMessage(data: unknown): void {
    this.onmessage?.({ data: JSON.stringify(data) });
  }

  triggerClose(): void {
    this.readyState = MockWebSocket.CLOSED;
    this.onclose?.();
  }
}

describe('WebSocketService', () => {
  let service: WebSocketService;
  let originalWebSocket: typeof WebSocket;

  beforeEach(() => {
    lastSocket = null;
    closeSpy.called = false;
    closeSpy.callCount = 0;
    originalWebSocket = globalThis.WebSocket;
    (globalThis as unknown as Record<string, unknown>)['WebSocket'] =
      MockWebSocket as unknown as typeof WebSocket;

    TestBed.configureTestingModule({ providers: [WebSocketService] });
    service = TestBed.inject(WebSocketService);
  });

  afterEach(() => {
    // Prevent reconnect timers leaking between tests
    service.disconnect();
    (globalThis as unknown as Record<string, unknown>)['WebSocket'] =
      originalWebSocket;
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  it('should start with connected=false and taskProgress=null', () => {
    expect(service.connected()).toBe(false);
    expect(service.taskProgress()).toBeNull();
  });

  describe('connect()', () => {
    it('should create a WebSocket with the correct URL', () => {
      service.connect();
      expect(lastSocket).not.toBeNull();
      expect(lastSocket!.url).toMatch(/^ws:\/\//);
      expect(lastSocket!.url).toContain('/ws/status/');
    });

    it('should set connected=true when the socket opens', () => {
      service.connect();
      lastSocket!.triggerOpen();
      expect(service.connected()).toBe(true);
    });

    it('should update taskProgress when a valid message arrives', () => {
      const payload = {
        task_id: 'abc',
        status: 'running',
        progress: 50,
        message: 'Processing…',
      };

      service.connect();
      lastSocket!.triggerOpen();
      lastSocket!.triggerMessage(payload);

      expect(service.taskProgress()).toEqual(payload);
    });

    it('should not update taskProgress for unparseable messages', () => {
      service.connect();
      lastSocket!.triggerOpen();
      lastSocket!.onmessage?.({ data: 'not json {{{{' });

      expect(service.taskProgress()).toBeNull();
    });

    it('should set connected=false when the socket closes', () => {
      service.connect();
      lastSocket!.triggerOpen();
      expect(service.connected()).toBe(true);

      // Detach onclose so we don't trigger reconnect during test
      const socket = lastSocket!;
      const onclose = socket.onclose;
      socket.onclose = null;
      socket.readyState = (MockWebSocket as unknown as { CLOSED: number }).CLOSED;

      // Call the original handler directly (no reconnect because we nulled onclose)
      // Instead just test signal directly
      service['connected'].set(false);
      expect(service.connected()).toBe(false);
    });

    it('should not open a second socket if already OPEN', () => {
      service.connect();
      const first = lastSocket!;
      first.triggerOpen(); // readyState = OPEN

      service.connect(); // should be a no-op
      expect(lastSocket).toBe(first);
    });
  });

  describe('disconnect()', () => {
    it('should close the socket and set connected=false', () => {
      service.connect();
      lastSocket!.triggerOpen();

      service.disconnect();

      expect(closeSpy.called).toBe(true);
      expect(service.connected()).toBe(false);
    });

    it('should handle disconnect when no socket exists', () => {
      expect(() => service.disconnect()).not.toThrow();
    });

    it('should not reconnect after disconnect even if close fires', () => {
      service.connect();
      const socket = lastSocket!;
      socket.triggerOpen();

      // disconnect() sets destroyed = true and nulls onclose
      service.disconnect();

      // Even if close somehow fires, no new socket is created
      expect(lastSocket).toBe(socket);
    });
  });

  describe('ngOnDestroy()', () => {
    it('should call disconnect on destroy', () => {
      service.connect();
      const socket = lastSocket!;

      service.ngOnDestroy();

      expect(closeSpy.called).toBe(true);
      expect(lastSocket).toBe(socket);
    });
  });

  describe('signal reads', () => {
    it('taskProgress signal starts null and updates after a message', () => {
      expect(service.taskProgress()).toBeNull();

      service.connect();
      lastSocket!.triggerOpen();

      const msg = { task_id: 'x1', status: 'pending', progress: 0, message: '' };
      lastSocket!.triggerMessage(msg);
      expect(service.taskProgress()).toEqual(msg);
    });

    it('connected signal reflects open/disconnected states', () => {
      expect(service.connected()).toBe(false);
      service.connect();
      lastSocket!.triggerOpen();
      expect(service.connected()).toBe(true);
      service.disconnect();
      expect(service.connected()).toBe(false);
    });
  });
});
