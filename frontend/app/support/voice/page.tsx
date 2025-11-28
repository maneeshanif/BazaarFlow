"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { PhoneCall, PhoneOff, Mic, MicOff } from "lucide-react";

import Vapi from "@vapi-ai/web";

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

export default function SupportVoicePage() {
  const [vapi, setVapi] = useState<Vapi | null>(null);
  const [isCalling, setIsCalling] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState<
    "idle" | "connecting" | "active" | "ended"
  >("idle");
  const [conversation, setConversation] = useState<ConversationEntry[]>([]);
  const [eventLog, setEventLog] = useState<EventLogEntry[]>([]);
  const [isListening, setIsListening] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [volumeLevel, setVolumeLevel] = useState(0);

  const publicKey = process.env.NEXT_PUBLIC_VAPI_PUBLIC_KEY ?? "";
  const assistantId = process.env.NEXT_PUBLIC_VAPI_SUPPORT_ASSISTANT_ID ?? "";

  useEffect(() => {
    let mounted = true;

    async function initVapi() {
      if (!publicKey) {
        console.warn("VAPI public key not configured");
        return;
      }

      try {
        if (!mounted) return;

        const instance = new Vapi(publicKey);

        setEventLog((prev) => [
          ...prev,
          {
            type: "system",
            label: "sdk:init",
            details: "Vapi Web SDK initialised",
            timestamp: new Date().toLocaleTimeString(),
          },
        ]);

        instance.on("call-start", () => {
          setConnectionStatus("active");
          setIsCalling(true);
          setConversation((prev) => [
            ...prev,
            {
              role: "system",
              text: "Call started.",
              timestamp: new Date().toLocaleTimeString(),
            },
          ]);
          setEventLog((prev) => [
            ...prev,
            {
              type: "system",
              label: "call:start",
              details: "Call started successfully",
              timestamp: new Date().toLocaleTimeString(),
            },
          ]);
        });

        instance.on("call-end", () => {
          setConnectionStatus("ended");
          setIsCalling(false);
          setIsMuted(false);
          setConversation((prev) => [
            ...prev,
            {
              role: "system",
              text: "Call ended.",
              timestamp: new Date().toLocaleTimeString(),
            },
          ]);
          setEventLog((prev) => [
            ...prev,
            {
              type: "system",
              label: "call:end",
              details: "Call ended",
              timestamp: new Date().toLocaleTimeString(),
            },
          ]);
        });

        // Speech and volume-level events for realtime indicators
        instance.on("speech-start", () => {
          setIsListening(true);
          setEventLog((prev) => [
            ...prev,
            {
              type: "system",
              label: "speech:start",
              details: "User started speaking",
              timestamp: new Date().toLocaleTimeString(),
            },
          ]);
        });

        instance.on("speech-end", () => {
          setIsListening(false);
          setEventLog((prev) => [
            ...prev,
            {
              type: "system",
              label: "speech:end",
              details: "User stopped speaking",
              timestamp: new Date().toLocaleTimeString(),
            },
          ]);
        });

        instance.on("volume-level", (volume: number) => {
          setVolumeLevel(volume);
        });

        instance.on(
          "message",
          (message: { type?: string; transcript?: { text?: string }; role?: string }) => {
            if (!message || !message.type) return;

            if (message.type === "transcript") {
              const text = message.transcript?.text ?? "";
              if (!text) return;

              const role = message.role === "user" ? "user" : "assistant";
              const timestamp = new Date().toLocaleTimeString();

              setConversation((prev) => [
                ...prev,
                {
                  role,
                  text,
                  timestamp,
                },
              ]);

              setEventLog((prev) => [
                ...prev,
                {
                  type: role,
                  label: role === "user" ? "user:transcript" : "assistant:transcript",
                  details: text,
                  timestamp,
                },
              ]);

              if (role === "assistant") {
                setIsSpeaking(true);
                // We don't have a direct assistant-speech-end event, so we can
                // optimistically clear speaking state after a short delay.
                setTimeout(() => setIsSpeaking(false), 1500);
              }
            }
          },
        );

        instance.on("error", (error: unknown) => {
          console.error("VAPI error", error);
          setConversation((prev) => [
            ...prev,
            {
              role: "system",
              text: "There was a problem with the call. Please try again.",
              timestamp: new Date().toLocaleTimeString(),
            },
          ]);
          setEventLog((prev) => [
            ...prev,
            {
              type: "error",
              label: "sdk:error",
              details: error instanceof Error ? error.message : String(error),
              timestamp: new Date().toLocaleTimeString(),
            },
          ]);
        });

        setVapi(instance);
      } catch (err) {
        console.error("Failed to initialise VAPI Web SDK", err);
        setEventLog((prev) => [
          ...prev,
          {
            type: "error",
            label: "sdk:init_error",
            details: err instanceof Error ? err.message : String(err),
            timestamp: new Date().toLocaleTimeString(),
          },
        ]);
      }
    }

    void initVapi();

    return () => {
      mounted = false;
    };
  }, [publicKey]);

  async function handleToggleCall() {
    if (!vapi) return;

    if (isCalling) {
      await vapi.stop();
      setEventLog((prev) => [
        ...prev,
        {
          type: "system",
          label: "call:stop_request",
          details: "User ended call",
          timestamp: new Date().toLocaleTimeString(),
        },
      ]);
      return;
    }

    if (!assistantId) {
      setConversation((prev) => [
        ...prev,
        {
          role: "system",
          text: "Support assistant ID is not configured.",
          timestamp: new Date().toLocaleTimeString(),
        },
      ]);
      setEventLog((prev) => [
        ...prev,
        {
          type: "error",
          label: "call:start_blocked",
          details: "Missing NEXT_PUBLIC_VAPI_SUPPORT_ASSISTANT_ID",
          timestamp: new Date().toLocaleTimeString(),
        },
      ]);
      return;
    }

    setConnectionStatus("connecting");
    setConversation([]);
    setEventLog((prev) => [
      ...prev,
      {
        type: "system",
        label: "call:start_request",
        details: `Starting call with assistant ${assistantId}`,
        timestamp: new Date().toLocaleTimeString(),
      },
    ]);

    try {
      await vapi.start(assistantId);
      setIsCalling(true);
    } catch (err) {
      console.error("Error starting VAPI call", err);
      setConnectionStatus("idle");
      setConversation((prev) => [
        ...prev,
        {
          role: "system",
          text: "Unable to start the support call.",
          timestamp: new Date().toLocaleTimeString(),
        },
      ]);
      setEventLog((prev) => [
        ...prev,
        {
          type: "error",
          label: "call:start_error",
          details: err instanceof Error ? err.message : String(err),
          timestamp: new Date().toLocaleTimeString(),
        },
      ]);
    }
  }

  async function handleToggleMute() {
    if (!vapi || !isCalling) return;

    try {
      if (isMuted) {
        vapi.setMuted(false);
        setIsMuted(false);
      } else {
        vapi.setMuted(true);
        setIsMuted(true);
      }
    } catch (err) {
      console.error("Error toggling mute", err);
      setEventLog((prev) => [
        ...prev,
        {
          type: "error",
          label: "call:mute_error",
          details: err instanceof Error ? err.message : String(err),
          timestamp: new Date().toLocaleTimeString(),
        },
      ]);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50 px-4 py-8">
      <Card className="w-full max-w-5xl shadow-lg">
        <CardContent className="p-6 space-y-6">
          <div className="flex items-center justify-between gap-4">
            <div>
              <h1 className="text-2xl font-semibold tracking-tight">
                BazaarFlow Voice Support
              </h1>
              <p className="text-sm text-muted-foreground mt-1">
                Talk to an AI assistant about your BazaarFlow setup, orders,
                inventory, and marketing.
              </p>
            </div>
            <div className="flex items-center gap-3">
              <Badge variant="outline">
                {connectionStatus === "active" && "Live"}
                {connectionStatus === "connecting" && "Connecting"}
                {connectionStatus === "idle" && "Idle"}
                {connectionStatus === "ended" && "Ended"}
              </Badge>
              <div className="flex items-center gap-2 text-xs text-slate-600">
                <span
                  className={
                    isListening
                      ? "h-2 w-2 rounded-full bg-emerald-500 animate-pulse"
                      : "h-2 w-2 rounded-full bg-slate-400"
                  }
                />
                <span>{isListening ? "Listening" : "Idle"}</span>
                <span className="mx-1 text-slate-400">•</span>
                <span
                  className={
                    isSpeaking
                      ? "h-2 w-2 rounded-full bg-sky-500 animate-pulse"
                      : "h-2 w-2 rounded-full bg-slate-400"
                  }
                />
                <span>{isSpeaking ? "Assistant speaking" : "Assistant idle"}</span>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-4">
            <Button
              size="lg"
              className="flex-1"
              onClick={handleToggleCall}
              disabled={!vapi}
            >
              {isCalling ? (
                <>
                  <PhoneOff className="w-4 h-4 mr-2" /> End Call
                </>
              ) : (
                <>
                  <PhoneCall className="w-4 h-4 mr-2" /> Start Call
                </>
              )}
            </Button>

            <Button
              variant="outline"
              size="icon"
              onClick={handleToggleMute}
              disabled={!isCalling}
            >
              {isMuted ? <MicOff className="w-4 h-4" /> : <Mic className="w-4 h-4" />}
            </Button>
          </div>

          {/* Simple volume meter */}
          <div className="flex items-center gap-2 text-xs text-slate-600">
            <span className="w-16">Mic level</span>
            <div className="h-2 flex-1 rounded-full bg-slate-200 overflow-hidden">
              <div
                className="h-full bg-emerald-500 transition-all"
                style={{ width: `${Math.min(100, Math.max(0, volumeLevel * 100))}%` }}
              />
            </div>
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <div className="border rounded-md bg-slate-950 text-slate-50 h-72 overflow-y-auto p-3 text-sm space-y-2">
              {conversation.length === 0 && (
                <p className="text-slate-400">
                  Start a call to see the live transcript of your conversation here.
                </p>
              )}
              {conversation.map((entry, idx) => (
                <div key={idx} className="flex flex-col">
                  <span className="text-[10px] text-slate-500">
                    {entry.timestamp} · {entry.role.toUpperCase()}
                  </span>
                  <span
                    className={
                      entry.role === "user"
                        ? "text-sky-300"
                        : entry.role === "assistant"
                        ? "text-emerald-300"
                        : "text-slate-300"
                    }
                  >
                    {entry.text}
                  </span>
                </div>
              ))}
            </div>

            <div className="border rounded-md bg-slate-900 text-slate-100 h-72 overflow-y-auto p-3 text-xs space-y-1">
              {eventLog.length === 0 && (
                <p className="text-slate-500">
                  Event log will show SDK events, call lifecycle, errors, and transcripts.
                </p>
              )}
              {eventLog.map((entry, idx) => (
                <div key={idx} className="flex flex-col">
                  <span className="text-[10px] text-slate-500">
                    {entry.timestamp} · {entry.type.toUpperCase()} · {entry.label}
                  </span>
                  {entry.details && <span className="text-slate-100">{entry.details}</span>}
                </div>
              ))}
            </div>
          </div>

          {!publicKey && (
            <p className="text-xs text-red-600">
              NEXT_PUBLIC_VAPI_PUBLIC_KEY is not set. Configure your VAPI keys to
              enable voice support.
            </p>
          )}

          {!assistantId && (
            <p className="text-xs text-amber-600">
              NEXT_PUBLIC_VAPI_SUPPORT_ASSISTANT_ID is not set. Create a
              &quot;BazaarFlow Support&quot; assistant in VAPI and add its ID to your env
              to route calls correctly.
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
