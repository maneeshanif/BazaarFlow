/** Shared class names of the public site's buttons. Kept out of client modules so server components can use them. */
export const SITE_BUTTON =
  "roll inline-flex min-h-control-lg items-center justify-center rounded-pill px-8 font-display text-ui-lg uppercase tracking-wide transition-transform duration-200 hover:-translate-y-0.5 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-line-focus focus-visible:ring-offset-2 disabled:opacity-60";
export const SITE_PRIMARY = `${SITE_BUTTON} bg-forest text-lime shadow-card hover:bg-forest-deep`;
export const SITE_SECONDARY = `${SITE_BUTTON} border-2 border-forest-ink text-forest-ink hover:bg-forest hover:text-lime`;
/** for use on forest-green sections */
export const SITE_ON_FOREST = `${SITE_BUTTON} bg-lime text-forest-ink hover:bg-lime-deep`;
export const SITE_ON_FOREST_SECONDARY = `${SITE_BUTTON} border-2 border-lime text-lime hover:bg-lime hover:text-forest-ink`;
