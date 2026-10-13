"use client";

import { LOCALES, LOCALE_LABEL } from "@/lib/i18n/dictionary";
import { useLocale } from "@/lib/i18n/LocaleProvider";
import { cn } from "@/lib/utils";

/** English / اردو. The choice is remembered on this device and flips the whole layout to right to left for Urdu. */
export function LanguageSwitcher({ className }: { className?: string }) {
  const { locale, setLocale, t } = useLocale();
  return (
    <div role="group" aria-label={t("Language")} className={cn("inline-flex rounded-md border border-border bg-surface p-0.5", className)}>
      {LOCALES.map((code) => (
        <button
          key={code}
          type="button"
          lang={code}
          aria-pressed={locale === code}
          onClick={() => setLocale(code)}
          className={cn(
            "h-control-sm rounded-sm px-2 text-ui-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-line-focus",
            locale === code ? "bg-action-subtle font-medium text-action" : "text-fg-muted hover:bg-surface-hover",
          )}
        >
          {LOCALE_LABEL[code]}
        </button>
      ))}
    </div>
  );
}
