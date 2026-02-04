/**
 * WebSocket Client
 * Real-time updates for transactions and alerts
 * Inspired by Deriv's real-time monitoring systems
 */

type WebSocketMessage = 
  | { type: 'connected'; timestamp: string; message: string }
  | { type: 'transaction'; data: any; timestamp: string }
  | { type: 'alert'; data: any; timestamp: string }
  | { type: 'dashboard_stats'; data: any; timestamp: string }
  | { type: 'subscription_updated'; subscriptions: Record<string, boolean> }
  | { type: 'pong'; timestamp: string }
  | { type: 'error'; message: string }

type MessageHandler = (message: WebSocketMessage) => void

class WebSocketClient {
  private ws: WebSocket | null = null
  private url: string
  private reconnectAttempts = 0
  private maxReconnectAttempts = 5
  private reconnectDelay = 1000
  private handlers: Set<MessageHandler> = new Set()
  private subscriptions: Record<string, boolean> = {
    transactions: true,
    alerts: true,
    dashboard: true,
  }

  constructor(url: string = 'ws://localhost:8000/ws') {
    this.url = url
  }

  connect(): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      return
    }

    try {
      this.ws = new WebSocket(this.url)

      this.ws.onopen = () => {
        console.log('WebSocket connected')
        this.reconnectAttempts = 0
        this.subscribe(this.subscriptions)
      }

      this.ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data) as WebSocketMessage
          this.handlers.forEach(handler => handler(message))
        } catch (error) {
          console.error('Error parsing WebSocket message:', error)
        }
      }

      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error)
      }

      this.ws.onclose = () => {
        console.log('WebSocket disconnected')
        this.ws = null
        this.attemptReconnect()
      }
    } catch (error) {
      console.error('Error creating WebSocket:', error)
      this.attemptReconnect()
    }
  }

  private attemptReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('Max reconnection attempts reached')
      return
    }

    this.reconnectAttempts++
    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1)
    
    setTimeout(() => {
      console.log(`Reconnecting... (attempt ${this.reconnectAttempts})`)
      this.connect()
    }, delay)
  }

  disconnect(): void {
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
  }

  subscribe(channels: Record<string, boolean>): void {
    this.subscriptions = { ...this.subscriptions, ...channels }
    
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({
        type: 'subscribe',
        channels: this.subscriptions,
      }))
    }
  }

  onMessage(handler: MessageHandler): () => void {
    this.handlers.add(handler)
    
    // Return unsubscribe function
    return () => {
      this.handlers.delete(handler)
    }
  }

  ping(): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type: 'ping' }))
    }
  }

  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN
  }
}

// Singleton instance
let wsClient: WebSocketClient | null = null

export function getWebSocketClient(): WebSocketClient {
  if (!wsClient) {
    const wsUrl = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000/ws'
    wsClient = new WebSocketClient(wsUrl)
  }
  return wsClient
}

// React hook for WebSocket
export function useWebSocket() {
  if (typeof window === 'undefined') {
    // SSR: return mock functions
    return {
      connect: () => {},
      disconnect: () => {},
      subscribe: () => {},
      onMessage: () => () => {},
      isConnected: () => false,
    }
  }

  const client = getWebSocketClient()

  return {
    connect: () => client.connect(),
    disconnect: () => client.disconnect(),
    subscribe: (channels: Record<string, boolean>) => client.subscribe(channels),
    onMessage: (handler: MessageHandler) => client.onMessage(handler),
    isConnected: () => client.isConnected(),
  }
}
