import { WebSocketMessage } from './types';

type MessageHandler<T> = (data: T) => void;
type StatusHandler = (status: 'connecting' | 'open' | 'closed' | 'error') => void;

export class SensorWebSocketClient<T = WebSocketMessage> {
  private ws: WebSocket | null = null;
  private url: string;
  private reconnectIntervalMs: number;
  private shouldReconnect: boolean = true;
  private messageListeners: Set<MessageHandler<T>> = new Set();
  private statusListeners: Set<StatusHandler> = new Set();
  private reconnectTimer: NodeJS.Timeout | null = null;

  constructor(url?: string, reconnectIntervalMs: number = 3000) {
    const defaultWsUrl = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8001/ws/feed';
    this.url = url || defaultWsUrl;
    this.reconnectIntervalMs = reconnectIntervalMs;
  }

  public connect(): void {
    if (typeof window === 'undefined') return;
    if (this.ws && (this.ws.readyState === WebSocket.CONNECTING || this.ws.readyState === WebSocket.OPEN)) {
      return;
    }

    this.shouldReconnect = true;
    this.notifyStatus('connecting');

    try {
      this.ws = new WebSocket(this.url);

      this.ws.onopen = () => {
        this.notifyStatus('open');
        if (this.reconnectTimer) {
          clearTimeout(this.reconnectTimer);
          this.reconnectTimer = null;
        }
      };

      this.ws.onmessage = (event: MessageEvent) => {
        try {
          const parsed = JSON.parse(event.data) as T;
          this.messageListeners.forEach((listener) => listener(parsed));
        } catch {
          // If raw string payload
          this.messageListeners.forEach((listener) => listener(event.data as unknown as T));
        }
      };

      this.ws.onerror = () => {
        this.notifyStatus('error');
      };

      this.ws.onclose = () => {
        this.notifyStatus('closed');
        if (this.shouldReconnect) {
          this.scheduleReconnect();
        }
      };
    } catch {
      this.notifyStatus('error');
      this.scheduleReconnect();
    }
  }

  public disconnect(): void {
    this.shouldReconnect = false;
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.notifyStatus('closed');
  }

  public send(data: unknown): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      const payload = typeof data === 'string' ? data : JSON.stringify(data);
      this.ws.send(payload);
    }
  }

  public onMessage(handler: MessageHandler<T>): () => void {
    this.messageListeners.add(handler);
    return () => {
      this.messageListeners.delete(handler);
    };
  }

  public onStatusChange(handler: StatusHandler): () => void {
    this.statusListeners.add(handler);
    return () => {
      this.statusListeners.delete(handler);
    };
  }

  private scheduleReconnect(): void {
    if (!this.shouldReconnect || this.reconnectTimer) return;
    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;
      this.connect();
    }, this.reconnectIntervalMs);
  }

  private notifyStatus(status: 'connecting' | 'open' | 'closed' | 'error'): void {
    this.statusListeners.forEach((listener) => listener(status));
  }
}
