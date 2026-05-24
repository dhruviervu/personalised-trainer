import { useCallback, useEffect, useRef, useState } from 'react';

const RECONNECT_DELAY_MS = 2000;

/**
 * WebSocket hook for exercise config + JPEG frame streaming.
 *
 * @param {string|null} url - WebSocket URL; pass null to stay disconnected
 * @param {{ enabled?: boolean, autoReconnect?: boolean }} options
 */
export function useWebSocket(url, options = {}) {
  const { enabled = true, autoReconnect = true } = options;

  const [lastMessage, setLastMessage] = useState(null);
  const [connectionStatus, setConnectionStatus] = useState('disconnected');
  const [configReady, setConfigReady] = useState(false);

  const wsRef = useRef(null);
  const reconnectTimerRef = useRef(null);
  const shouldReconnectRef = useRef(autoReconnect);
  const enabledRef = useRef(enabled);
  const configReadyRef = useRef(false);

  useEffect(() => {
    enabledRef.current = enabled;
    shouldReconnectRef.current = autoReconnect;
  }, [enabled, autoReconnect]);

  const clearReconnectTimer = useCallback(() => {
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
  }, []);

  const connect = useCallback(() => {
    if (!url || !enabledRef.current) {
      return;
    }

    clearReconnectTimer();
    setConnectionStatus('connecting');
    setConfigReady(false);
    configReadyRef.current = false;

    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnectionStatus('connected');
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        setLastMessage(data);
      } catch (err) {
        console.error('Failed to parse WebSocket message:', err);
      }
    };

    ws.onerror = () => {
      setConnectionStatus('disconnected');
    };

    ws.onclose = () => {
      setConnectionStatus('disconnected');
      setConfigReady(false);
      configReadyRef.current = false;
      wsRef.current = null;

      if (shouldReconnectRef.current && enabledRef.current) {
        reconnectTimerRef.current = window.setTimeout(() => {
          connect();
        }, RECONNECT_DELAY_MS);
      }
    };
  }, [url, clearReconnectTimer]);

  useEffect(() => {
    if (!enabled || !url) {
      clearReconnectTimer();
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
      setConnectionStatus('disconnected');
      setConfigReady(false);
      configReadyRef.current = false;
      return undefined;
    }

    shouldReconnectRef.current = autoReconnect;
    connect();

    return () => {
      clearReconnectTimer();
      shouldReconnectRef.current = false;
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [enabled, url, autoReconnect, connect, clearReconnectTimer]);

  const sendConfig = useCallback((exerciseConfig) => {
    const ws = wsRef.current;
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(exerciseConfig));
      configReadyRef.current = true;
      setConfigReady(true);
    }
  }, []);

  const sendFrame = useCallback((base64jpeg) => {
    const ws = wsRef.current;
    if (
      ws &&
      ws.readyState === WebSocket.OPEN &&
      base64jpeg &&
      configReadyRef.current
    ) {
      ws.send(base64jpeg);
    }
  }, []);

  const sendResetSet = useCallback(() => {
    const ws = wsRef.current;
    if (ws && ws.readyState === WebSocket.OPEN && configReadyRef.current) {
      ws.send('RESET_SET');
    }
  }, []);

  const disconnect = useCallback(() => {
    shouldReconnectRef.current = false;
    clearReconnectTimer();
    setConfigReady(false);
    configReadyRef.current = false;
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setConnectionStatus('disconnected');
  }, [clearReconnectTimer]);

  const resetForNewSession = useCallback(() => {
    setLastMessage(null);
    setConfigReady(false);
    configReadyRef.current = false;
  }, []);

  return {
    sendFrame,
    sendConfig,
    sendResetSet,
    lastMessage,
    connectionStatus,
    configReady,
    disconnect,
    resetForNewSession,
  };
}
