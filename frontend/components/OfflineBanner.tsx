"use client";

import { useEffect, useState } from "react";

export default function OfflineBanner() {
  const [online, setOnline] = useState<boolean>(true);
  useEffect(() => {
    // initialize from navigator (no sync setState on mount by using a timeout)
    const initial = navigator.onLine;
    setTimeout(() => setOnline(initial), 0);
    function onOnline() { setOnline(true); }
    function onOffline() { setOnline(false); }
    window.addEventListener('online', onOnline);
    window.addEventListener('offline', onOffline);
    return () => {
      window.removeEventListener('online', onOnline);
      window.removeEventListener('offline', onOffline);
    };
  }, []);

  if (online) return null;
  return (
    <div style={{ background: '#fffbeb', border: '1px solid #f6c6a8', padding: 12, borderRadius: 8, marginBottom: 12 }}>
      <strong>You are offline</strong> — some features are disabled. <button className="btn-primary" style={{ marginLeft: 8 }}>Retry</button>
    </div>
  );
}
