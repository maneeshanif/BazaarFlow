/** Shared class names of the public site's buttons. Kept out of client modules so server components can use them. */
export const SITE_BUTTON =
  "inline-flex min-h-control-lg items-center justify-center rounded-md px-5 text-ui-md font-semibold focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-line-focus focus-visible:ring-offset-2 disabled:opacity-60";
export const SITE_PRIMARY = `${SITE_BUTTON} bg-ink text-fg-inverse hover:bg-ink-soft`;
export const SITE_SECONDARY = `${SITE_BUTTON} border border-ink text-ink hover:bg-ledger-rule/40`;
