type Subscriber = (msg: unknown) => void;

const subscribers: Set<Subscriber> = new Set();
let socket: WebSocket | null = null;

export function connectWS(url = (typeof window !== 'undefined' && window.location.origin.replace(/^http/, 'ws')) + '/ws/clients') {
  if (socket && socket.readyState === WebSocket.OPEN) return socket;
  try {
    socket = new WebSocket(url);
    socket.onmessage = (ev) => {
      let data: unknown = null;
      try { data = JSON.parse(ev.data as string); } catch { data = ev.data; }
      subscribers.forEach((s) => s(data));
    };
    socket.onclose = () => { socket = null; };
  } catch (err) {
    console.warn('ws connect failed', err);
  }
  return socket;
}

export function subscribe(cb: Subscriber) {
  subscribers.add(cb);
  return () => { subscribers.delete(cb); };
}

export function sendWS(msg: unknown) {
  if (!socket || socket.readyState !== WebSocket.OPEN) return false;
  socket.send(JSON.stringify(msg));
  return true;
}
