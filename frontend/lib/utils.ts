import { clsx, type ClassValue } from "clsx"
import { extendTailwindMerge } from "tailwind-merge"

/**
 * Our type scale (`text-ui-*`, `text-display-*`) are font sizes, not colours. Without telling tailwind-merge, it reads
 * `text-ui-base` as a text colour and silently drops an earlier `text-fg-inverse`, which left primary buttons with dark
 * text on blue (found by the axe contrast check, task 53).
 */
const twMerge = extendTailwindMerge({
  extend: {
    classGroups: {
      "font-size": [{ text: ["ui-2xs", "ui-xs", "ui-sm", "ui-base", "ui-md", "ui-lg", "ui-xl", "ui-2xl", "ui-3xl", "display-lg", "display-xl"] }],
    },
  },
})

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}
