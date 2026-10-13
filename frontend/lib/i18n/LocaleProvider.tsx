"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useSyncExternalStore, type ReactNode } from "react";
import { dirFor, isLocale, translate, type Locale } from "@/lib/i18n/dictionary";

const STORAGE_KEY = "bf_locale";
const CHANGED = "bf-locale-changed";

type Value = {
  locale: Locale;
  dir: "ltr" | "rtl";
  setLocale: (next: Locale) => void;
  t: (text: string) => string;
};

const FALLBACK: Value = { locale: "en", dir: "ltr", setLocale: () => undefined, t: (text) => text };

const LocaleContext = createContext<Value>(FALLBACK);

// the choice made in this page visit, so the switch works even when storage is blocked
let chosen: Locale | null = null;

/** Storage can be blocked or throw (private windows, blocked site data): the app still renders, in English. */
function readStored(): Locale {
  if (chosen) return chosen;
  try {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    return isLocale(stored) ? stored : "en";
  } catch {
    return "en";
  }
}

function subscribe(onChange: () => void): () => void {
  window.addEventListener(CHANGED, onChange);
  window.addEventListener("storage", onChange); // another tab changed the language
  return () => {
    window.removeEventListener(CHANGED, onChange);
    window.removeEventListener("storage", onChange);
  };
}

/**
 * The shop language (PRD §16). The server and the first client render are English, so hydration always matches; a
 * stored Urdu choice is read from the device right after, and sets `lang` and `dir` on the document, which is what
 * flips the layout to right to left. The choice is kept in localStorage: a per-device convenience, not shop data.
 */
export function LocaleProvider({ children }: { children: ReactNode }) {
  const locale = useSyncExternalStore<Locale>(subscribe, readStored, () => "en");

  useEffect(() => {
    document.documentElement.lang = locale;
    document.documentElement.dir = dirFor(locale);
  }, [locale]);

  const setLocale = useCallback((next: Locale) => {
    chosen = next;
    try {
      window.localStorage.setItem(STORAGE_KEY, next);
    } catch {
      // the choice cannot be kept on this device, so it applies only until the page is reloaded
    }
    window.dispatchEvent(new Event(CHANGED));
  }, []);

  const value = useMemo<Value>(
    () => ({ locale, dir: dirFor(locale), setLocale, t: (text: string) => translate(locale, text) }),
    [locale, setLocale],
  );
  return <LocaleContext.Provider value={value}>{children}</LocaleContext.Provider>;
}

export function useLocale(): Value {
  return useContext(LocaleContext);
}

/** `const t = useT(); t("Orders")` -> the text in the shop's language, or the English original. */
export function useT(): (text: string) => string {
  return useContext(LocaleContext).t;
}
