"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Mic, MicOff, PhoneCall, PhoneOff } from "lucide-react";
import Vapi from "@vapi-ai/web";

import { Button } from "@/components/app/Button";
import { PageHeader } from "@/components/app/PageHeader";

interface ConversationEntry {
  role: "user" | "assistant" | "system";
  text: string;
  timestamp: string;
}

interface EventLogEntry {
  type: "system" | "user" | "assistant" | "error" | "network";
  label: string;
  details?: string;
  timestamp: string;
}

type CallStatus = "idle" | "connecting" | "active" | "ended";

const STATUS_LABEL: Record<CallStatus, string> = { idle: "Idle", connecting: "Connecting", active: "Live", ended: "Ended" };
const now = () => new Date().toLocaleTimeString();
const errorText = (err: unknown) => (err instanceof Error ? err.message : String(err));

/** Dot that pulses while its flag is on. */
function Dot({ on, tone }: { on: boolean; tone: "bg-success" | "bg-info" }) {
  return <span aria-hidden className={`h-3 w-3 rounded-pill ${on ? `${tone} animate-pulse` : "bg-neutral"}`} />;
}

/** Live voice test call with the support assistant (VAPI Web SDK), inside the workspace shell. */
export function SupportCall() {
  const vapiRef = useRef<Vapi | null>(null);
  const [isCalling, setIsCalling] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [status, setStatus] = useState<CallStatus>("idle");
  const [conversation, setConversation] = useState<ConversationEntry[]>([]);
  const [eventLog, setEventLog] = useState<EventLogEntry[]>([]);
  const [isListening, setIsListening] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [volumeLevel, setVolumeLevel] = useState(0);

  const publicKey = process.env.NEXT_PUBLIC_VAPI_PUBLIC_KEY ?? "";
  const assistantId = process.env.NEXT_PUBLIC_VAPI_SUPPORT_ASSISTANT_ID ?? "";

  const log = useCallback((type: EventLogEntry["type"], label: string, details?: string) => {
    setEventLog((prev) => [...prev, { type, label, details, timestamp: now() }]);
  }, []);
  const say = useCallback((role: ConversationEntry["role"], text: string) => {
    setConversation((prev) => [...prev, { role, text, timestamp: now() }]);
  }, []);

  useEffect(() => {
    if (!publicKey) return;
    let instance: Vapi;
    try {
      instance = new Vapi(publicKey);
    } catch (err) {
      console.error("Failed to initialise VAPI Web SDK", err);
      return;
    }

    instance.on("call-start", () => {
      setStatus("active");
      setIsCalling(true);
      say("system", "Call started.");
      log("system", "call:start", "Call started successfully");
    });
    instance.on("call-end", () => {
      setStatus("ended");
      setIsCalling(false);
      setIsMuted(false);
      say("system", "Call ended.");
      log("system", "call:end", "Call ended");
    });
    instance.on("speech-start", () => {
      setIsListening(true);
      log("system", "speech:start", "User started speaking");
    });
    instance.on("speech-end", () => {
      setIsListening(false);
      log("system", "speech:end", "User stopped speaking");
    });
    instance.on("volume-level", (volume: number) => setVolumeLevel(volume));
    instance.on("message", (message: { type?: string; transcript?: { text?: string }; role?: string }) => {
      if (message?.type !== "transcript") return;
      const text = message.transcript?.text ?? "";
      if (!text) return;
      const role = message.role === "user" ? "user" : "assistant";
      say(role, text);
      log(role, `${role}:transcript`, text);
      if (role === "assistant") {
        setIsSpeaking(true);
        // there is no assistant-speech-end event, so clear the speaking state after a short delay
        setTimeout(() => setIsSpeaking(false), 1500);
      }
    });
    instance.on("error", (error: unknown) => {
      console.error("VAPI error", error);
      say("system", "There was a problem with the call. Please try again.");
      log("error", "sdk:error", errorText(error));
    });

    vapiRef.current = instance;
    return () => {
      instance.removeAllListeners?.();
      vapiRef.current = null;
    };
  }, [publicKey, log, say]);

  async function handleToggleCall() {
    const vapi = vapiRef.current;
    if (!vapi) return;
    if (isCalling) {
      await vapi.stop();
      log("system", "call:stop_request", "User ended call");
      return;
    }
    if (!assistantId) {
      say("system", "Support assistant ID is not configured.");
      log("error", "call:start_blocked", "Missing NEXT_PUBLIC_VAPI_SUPPORT_ASSISTANT_ID");
      return;
    }
    setStatus("connecting");
    setConversation([]);
    log("system", "call:start_request", `Starting call with assistant ${assistantId}`);
    try {
      await vapi.start(assistantId);
      setIsCalling(true);
    } catch (err) {
      console.error("Error starting VAPI call", err);
      setStatus("idle");
      say("system", "Unable to start the support call.");
      log("error", "call:start_error", errorText(err));
    }
  }

  function handleToggleMute() {
    const vapi = vapiRef.current;
    if (!vapi || !isCalling) return;
    try {
      vapi.setMuted(!isMuted);
      setIsMuted(!isMuted);
    } catch (err) {
      console.error("Error toggling mute", err);
      log("error", "call:mute_error", errorText(err));
    }
  }

  return (
    <div>
      <PageHeader
        title="Support calls"
        description="Talk to the voice assistant about your shop, orders, stock and marketing."
        actions={
          <span className="rounded-pill border-2 border-line-strong bg-surface-raised px-4 py-1 text-ui-sm font-bold text-fg">
            {STATUS_LABEL[status]}
          </span>
        }
      />

      <div className="space-y-6 px-4 pb-8 md:px-8">
        <div className="rounded-card border-2 border-line-strong bg-surface-raised p-6 shadow-card">
          <div className="flex flex-wrap items-center gap-x-6 gap-y-2 text-ui-sm text-fg-muted">
            <span className="flex items-center gap-2">
              <Dot on={isListening} tone="bg-success" />
              {isListening ? "Listening" : "Not listening"}
            </span>
            <span className="flex items-center gap-2">
              <Dot on={isSpeaking} tone="bg-info" />
              {isSpeaking ? "Assistant speaking" : "Assistant quiet"}
            </span>
          </div>

          <div className="mt-5 flex items-center gap-3">
            <Button variant="primary" size="lg" className="flex-1" onClick={handleToggleCall} disabled={!publicKey}>
              {isCalling ? <PhoneOff aria-hidden className="h-5 w-5" /> : <PhoneCall aria-hidden className="h-5 w-5" />}
              {isCalling ? "End call" : "Start call"}
            </Button>
            <Button
              variant="secondary"
              size="lg"
              onClick={handleToggleMute}
              disabled={!isCalling}
              aria-label={isMuted ? "Unmute microphone" : "Mute microphone"}
            >
              {isMuted ? <MicOff aria-hidden className="h-5 w-5" /> : <Mic aria-hidden className="h-5 w-5" />}
            </Button>
          </div>

          <div className="mt-5 flex items-center gap-3 text-ui-sm text-fg-muted">
            <span className="w-20 shrink-0">Mic level</span>
            <div className="h-3 flex-1 overflow-hidden rounded-pill bg-surface-sunken">
              <div
                className="h-full rounded-pill bg-success transition-all"
                style={{ width: `${Math.min(100, Math.max(0, volumeLevel * 100))}%` }}
              />
            </div>
          </div>
        </div>

        <div className="grid gap-6 md:grid-cols-2">
          <section aria-label="Live transcript" className="h-80 overflow-y-auto rounded-card border-2 border-line-strong bg-surface-raised p-5 shadow-card">
            <h2 className="mb-3 text-ui-lg">Transcript</h2>
            {conversation.length === 0 ? (
              <p className="text-ui-sm text-fg-muted">Start a call to see the live transcript of your conversation here.</p>
            ) : (
              <ul className="space-y-3 text-ui-sm">
                {conversation.map((entry, idx) => (
                  <li key={idx}>
                    <span className="block text-ui-xs text-fg-subtle">
                      {entry.timestamp} · {entry.role}
                    </span>
                    <span className={entry.role === "user" ? "font-semibold text-info" : entry.role === "assistant" ? "text-fg" : "text-fg-muted"}>
                      {entry.text}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section aria-label="Event log" className="h-80 overflow-y-auto rounded-card border-2 border-line-strong bg-surface-raised p-5 shadow-card">
            <h2 className="mb-3 text-ui-lg">Event log</h2>
            {eventLog.length === 0 ? (
              <p className="text-ui-sm text-fg-muted">Call events, errors and transcripts will show here.</p>
            ) : (
              <ul className="space-y-2 text-ui-xs">
                {eventLog.map((entry, idx) => (
                  <li key={idx}>
                    <span className={`block ${entry.type === "error" ? "text-danger" : "text-fg-subtle"}`}>
                      {entry.timestamp} · {entry.type} · {entry.label}
                    </span>
                    {entry.details ? <span className="text-fg">{entry.details}</span> : null}
                  </li>
                ))}
              </ul>
            )}
          </section>
        </div>

        {!publicKey ? (
          <p role="status" className="rounded-card border-2 border-danger-border bg-danger-subtle p-4 text-ui-sm text-danger">
            Voice support is not switched on yet: the VAPI public key is missing. It will work once the owner adds the keys.
          </p>
        ) : null}
        {publicKey && !assistantId ? (
          <p role="status" className="rounded-card border-2 border-warning-border bg-warning-subtle p-4 text-ui-sm text-warning">
            The support assistant is not set up yet. Create a &quot;BazaarFlow Support&quot; assistant in VAPI and add its ID.
          </p>
        ) : null}
      </div>
    </div>
  );
}
