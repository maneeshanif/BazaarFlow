/**
 * Status -> tone mapping (context/ui-tokens.md). A status must mean the same on every screen, so components never
 * pick a colour for a status themselves: they ask this module.
 */

export type Tone = "success" | "warning" | "danger" | "info" | "neutral" | "accent";

const TONES: Record<string, Tone> = {
  // success
  posted: "success", paid: "success", connected: "success", executed: "success", approved: "success",
  accepted: "success", reconciled: "success", active: "success", completed: "success", published: "success",
  delivered: "success", in_stock: "success", settled: "success",
  // warning
  pending: "warning", needs_human: "warning", low_stock: "warning", partial: "warning", awaiting_approval: "warning",
  near_expiry: "warning", pending_approval: "warning", owes: "warning", step_limit: "warning", spend_limit: "warning",
  // info
  scheduled: "info", submitted: "info", in_progress: "info", queued: "info", generating: "info", running: "info",
  // danger
  reversed: "danger", rejected: "danger", error: "danger", failed: "danger", expired: "danger", cancelled: "danger",
  void: "danger", inactive: "danger", out_of_stock: "danger", send_failed: "danger",
  // accent
  ai_handling: "accent",
  // neutral
  draft: "neutral", resolved: "neutral", open: "neutral", disabled: "neutral", paused: "neutral", archived: "neutral",
};

const normalise = (status: string): string => status.trim().toLowerCase().replace(/[\s-]+/g, "_");

export function toneFor(status: string): Tone {
  return TONES[normalise(status)] ?? "neutral";
}

/** Human label for a status, e.g. needs_human -> "needs human". */
export function labelFor(status: string): string {
  return normalise(status).replace(/_/g, " ");
}
