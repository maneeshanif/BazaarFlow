"use client";

import { useEffect, useState } from "react";

export function useLocalStorage<T>(key: string, defaultValue: T): [T, (value: T) => void] {
  const [value, setValue] = useState<T>(() => {
    if (typeof window === "undefined") {
      return defaultValue;
    }
    try {
      const stored = window.localStorage.getItem(key);
      return stored ? (JSON.parse(stored) as T) : defaultValue;
    } catch {
      return defaultValue;
    }
  });

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }
    try {
      window.localStorage.setItem(key, JSON.stringify(value));
    } catch {
      /* ignore quota errors */
    }
  }, [key, value]);

  return [value, setValue];
}
